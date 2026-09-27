from typing import Dict, Any, Tuple

def handle_reply(message: str, auto_reply_count: int, merchant_id: str) -> Tuple[str, str, str, str]:
    """
    Returns (action, body, cta, rationale)
    action can be "send", "wait", "end"
    """
    msg_lower = message.lower()
    
    # 1. Check auto-reply
    # Production Vera tries once after detecting auto-reply, then stops.
    # The requirement says "same message verbatim 3+ times = auto-reply".
    # Since the simulator starts at turn 1 and counts, if auto_reply_count >= 2, we end it.
    if auto_reply_count >= 2:
        return "end", "", "", "Detected auto-reply loop. Gracefully exiting."

    # 2. Check hostile / opt-out
    hostile_words = ["stop", "spam", "useless", "bothering", "don't send", "not interested", "fuck", "shut up"]
    if any(w in msg_lower for w in hostile_words) and "stop" in msg_lower or "spam" in msg_lower or "useless" in msg_lower:
        return "end", "Understood. I will not send these messages anymore. Have a great day!", "none", "Merchant requested to stop. Honoring opt-out."

    # 3. Check intent transition (execution handoff)
    intent_words = ["let's do it", "lets do it", "go ahead", "yes", "sure", "update", "do it", "start", "proceed", "what's next", "whats next"]
    # If the bot was qualifying, and now they say yes
    if any(w in msg_lower for w in intent_words):
        # Move to execution
        body = "Done! I've started the process. I'll share a preview of the update with you shortly."
        if "draft" in msg_lower or "send" in msg_lower or "patient" in msg_lower:
             body = "Sending now — also drafted a 90-sec patient-ed WhatsApp for you to review."
        return "send", body, "open_ended", "Merchant showed clear intent. Switched to action mode immediately."
        
    # 4. Check off-topic
    if "gst" in msg_lower or "tax" in msg_lower:
        return "send", "I specialize in your Google Business Profile and local marketing, so I can't help with GST/taxes. Would you like to get back to the profile updates?", "yes/no", "Redirected off-topic query politely."

    # 5. Ask to wait
    wait_words = ["wait", "busy", "later", "give me time"]
    if any(w in msg_lower for w in wait_words):
        return "wait", "", "", "Merchant is busy, waiting."

    # Default fallback
    return "send", "Got it. Let's move forward with this. Would you like me to finalize the draft?", "yes/no", "Acknowledged reply and proposed next step."
