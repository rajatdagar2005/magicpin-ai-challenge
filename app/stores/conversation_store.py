import threading
from typing import Any, Dict, List, Optional

class ConversationStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._conversations: Dict[str, Dict[str, Any]] = {}
        self._suppressed: Dict[str, bool] = {}
        self._merchant_states: Dict[str, Dict[str, Any]] = {}

    def append_message(self, conversation_id: str, from_role: str, message: str, turn_number: int):
        with self._lock:
            if conversation_id not in self._conversations:
                self._conversations[conversation_id] = {
                    "history": [],
                    "state": "NEW"
                }
            
            conv = self._conversations[conversation_id]
            conv["history"].append({
                "from": from_role,
                "msg": message,
                "turn": turn_number
            })

    def track_merchant_message(self, merchant_id: str, message: str) -> int:
        with self._lock:
            if merchant_id not in self._merchant_states:
                self._merchant_states[merchant_id] = {"last_msg": None, "auto_reply_count": 0}
            
            state = self._merchant_states[merchant_id]
            if state["last_msg"] == message:
                state["auto_reply_count"] += 1
            else:
                state["auto_reply_count"] = 0
            state["last_msg"] = message
            return state["auto_reply_count"]

    def update_state(self, conversation_id: str, state: str):
        with self._lock:
            if conversation_id in self._conversations:
                self._conversations[conversation_id]["state"] = state

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._conversations.get(conversation_id)

    def suppress(self, suppression_key: str):
        with self._lock:
            self._suppressed[suppression_key] = True

    def is_suppressed(self, suppression_key: str) -> bool:
        with self._lock:
            return self._suppressed.get(suppression_key, False)

conversation_store = ConversationStore()
