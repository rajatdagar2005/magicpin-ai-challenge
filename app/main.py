import time
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from typing import Any

from app.models import ContextPushRequest, ContextPushResponse, TickRequest, TickResponse, ReplyRequest, ReplyResponse, Action
from app.stores.context_store import context_store
from app.stores.conversation_store import conversation_store
from app.core.state_machine import handle_reply
from app.core.suppression import suppression_store
from app.composer.deterministic import compose

app = FastAPI()
START = time.time()

@app.get("/v1/healthz")
async def healthz():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START),
        "contexts_loaded": context_store.get_counts()
    }

@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": "Antigravity",
        "team_members": ["Agent"],
        "model": "Deterministic (Fallback)",
        "approach": "Deterministic Composer with robust state machine",
        "contact_email": "agent@example.com",
        "version": "1.0.0",
        "submitted_at": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/v1/context")
async def push_context(body: ContextPushRequest):
    accepted, reason, cur_ver = context_store.push(
        body.scope, body.context_id, body.version, body.payload
    )
    
    if not accepted:
        # stale version
        return {
            "accepted": False,
            "reason": "stale_version",
            "current_version": cur_ver
        }
        
    if reason == "same":
        # idempotent 200 OK
        return {
            "accepted": True,
            "ack_id": f"ack_{body.context_id}_v{body.version}",
            "stored_at": datetime.utcnow().isoformat() + "Z"
        }
        
    # replaced (higher version)
    return {
        "accepted": True,
        "ack_id": f"ack_{body.context_id}_v{body.version}",
        "stored_at": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/v1/tick")
async def tick(body: TickRequest):
    actions = []
    
    for trg_id in body.available_triggers:
        if len(actions) >= 20:
            break
            
        trg_payload = context_store.get_payload("trigger", trg_id)
        if not trg_payload:
            continue
            
        merchant_id = trg_payload.get("merchant_id")
        merchant = context_store.get_payload("merchant", merchant_id)
        if not merchant:
            continue
            
        category_slug = merchant.get("category_slug")
        category = context_store.get_payload("category", category_slug)
        if not category:
            continue
            
        customer_id = trg_payload.get("customer_id")
        customer = context_store.get_payload("customer", customer_id) if customer_id else None
        
        # Check expiry
        expires_at_str = trg_payload.get("expires_at")
        if expires_at_str:
            try:
                # "2026-05-03T00:00:00Z"
                expires_dt = datetime.strptime(expires_at_str.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
                now_dt = datetime.strptime(body.now.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
                if now_dt >= expires_dt:
                    continue
            except Exception:
                pass
        
        # Check suppression
        sup_key = trg_payload.get("suppression_key", "")
        if sup_key and suppression_store.is_suppressed(sup_key):
            continue
            
        # Compose message deterministically
        composed = compose(category, merchant, trg_payload, customer)
        if composed:
            # Mark suppressed
            suppression_store.suppress(sup_key)
            
            # Action required
            conv_id = f"conv_{merchant_id}_{trg_id}"
            actions.append(Action(
                conversation_id=conv_id,
                merchant_id=merchant_id,
                customer_id=customer_id,
                send_as=composed["send_as"],
                trigger_id=trg_id,
                template_name="deterministic_v1",
                template_params=[],
                body=composed["body"],
                cta=composed["cta"],
                suppression_key=sup_key,
                rationale=composed["rationale"]
            ))
            
    return TickResponse(actions=actions)

@app.post("/v1/reply")
async def reply(body: ReplyRequest):
    # Store history
    conversation_store.append_message(
        body.conversation_id, body.from_role, body.message, body.turn_number
    )
    
    auto_reply_count = 0
    if body.from_role == "merchant" and body.merchant_id:
        auto_reply_count = conversation_store.track_merchant_message(body.merchant_id, body.message)
    
    conv = conversation_store.get_conversation(body.conversation_id)
    merchant = context_store.get_payload("merchant", body.merchant_id) if body.merchant_id else {}
    
    action, next_body, cta, rationale = handle_reply(body.message, auto_reply_count, body.merchant_id)
    
    if action == "end":
        conversation_store.update_state(body.conversation_id, "ENDED")
        return ReplyResponse(action=action, rationale=rationale)
        
    elif action == "wait":
        conversation_store.update_state(body.conversation_id, "WAITING")
        return ReplyResponse(action=action, wait_seconds=1800, rationale=rationale)
        
    else:
        conversation_store.update_state(body.conversation_id, "ENGAGED")
        return ReplyResponse(action=action, body=next_body, cta=cta, rationale=rationale)
