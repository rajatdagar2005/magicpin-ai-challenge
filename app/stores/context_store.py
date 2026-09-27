import threading
from typing import Any, Dict, Optional, Tuple, List

class ContextStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._store: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def push(self, scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
        """
        Returns (accepted, reason, current_version)
        accepted=True, reason="replaced", current_version=None (higher version)
        accepted=True, reason="same", current_version=version (same version -> no-op)
        accepted=False, reason="stale", current_version=current (lower version)
        """
        key = (scope, context_id)
        with self._lock:
            if key in self._store:
                cur = self._store[key]
                if version < cur["version"]:
                    return False, "stale", cur["version"]
                elif version == cur["version"]:
                    return True, "same", cur["version"]
            
            self._store[key] = {
                "version": version,
                "payload": payload
            }
            return True, "replaced", None

    def get(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._store.get((scope, context_id))

    def get_payload(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            ctx = self._store.get((scope, context_id))
            if ctx:
                return ctx["payload"]
            return None

    def get_counts(self) -> Dict[str, int]:
        counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
        with self._lock:
            for (scope, _) in self._store.keys():
                if scope in counts:
                    counts[scope] += 1
                else:
                    counts[scope] = 1
        return counts

    def get_all_by_scope(self, scope: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [ctx for (s, _), ctx in self._store.items() if s == scope]

context_store = ContextStore()
