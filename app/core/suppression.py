import threading
from datetime import datetime, timezone
from typing import Dict

class SuppressionStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._keys: Dict[str, datetime] = {}

    def is_suppressed(self, key: str) -> bool:
        if not key:
            return False
        with self._lock:
            return key in self._keys

    def suppress(self, key: str):
        if not key:
            return
        with self._lock:
            self._keys[key] = datetime.now(timezone.utc)

suppression_store = SuppressionStore()
