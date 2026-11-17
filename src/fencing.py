"""Fencing tokens: the resource (store) rejects writes from stale workers."""

import threading
from dataclasses import dataclass
from typing import Callable, Dict, Optional


class FencingTokenIssuer:
    """Simulates a lock service handing out strictly increasing tokens."""

    def __init__(self):
        self._counter = 0
        self._lock = threading.Lock()

    def next_token(self) -> int:
        with self._lock:
            self._counter += 1
            return self._counter


@dataclass
class OrderRecord:
    status: Optional[str] = None
    highest_token: int = 0
    last_worker: Optional[str] = None


class FencedOrderStore:
    def __init__(self, log: Callable[[str], None] = print):
        self._orders: Dict[str, OrderRecord] = {}
        self._log = log
        self._lock = threading.Lock()

    def update(self, order_id: str, status: str, token: int, worker: str) -> bool:
        """Apply the update if ``token`` is not older than the newest seen. Returns accepted?"""
        with self._lock:
            rec = self._orders.setdefault(order_id, OrderRecord())
            if token < rec.highest_token:
                self._log(f"[{order_id}] {worker} token={token} status={status}: REJECTED "
                          f"(stale token; store has seen token {rec.highest_token})")
                return False
            rec.highest_token = token
            rec.status = status
            rec.last_worker = worker
            self._log(f"[{order_id}] {worker} token={token} status={status}: ACCEPTED")
            return True

    def get(self, order_id: str) -> OrderRecord:
        return self._orders.setdefault(order_id, OrderRecord())
