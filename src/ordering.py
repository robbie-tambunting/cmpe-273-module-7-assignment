"""Versioned order-event processing.

Each order has a monotonically increasing ``version``. Events may arrive out of
order or more than once; the processor applies them strictly in version order,
buffers events that arrive early, and ignores duplicates.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass(frozen=True)
class Event:
    order_id: str
    version: int
    status: str


@dataclass
class OrderState:
    applied_version: int = 0          # 0 = nothing applied yet; next expected is 1
    status: Optional[str] = None
    pending: Dict[int, str] = field(default_factory=dict)   # version -> status
    applied_history: List[int] = field(default_factory=list)


class OrderProcessor:
    def __init__(self, log: Callable[[str], None] = print):
        self._orders: Dict[str, OrderState] = {}
        self._log = log

    def _state(self, order_id: str) -> OrderState:
        return self._orders.setdefault(order_id, OrderState())

    def apply_event(self, event: Event) -> str:
        """Process one event. Returns 'applied', 'buffered' or 'duplicate'."""
        st = self._state(event.order_id)
        tag = f"[{event.order_id}] v{event.version} ({event.status})"

        if event.version <= st.applied_version:
            self._log(f"{tag}: IGNORED duplicate (already applied; current v{st.applied_version})")
            return "duplicate"

        if event.version in st.pending:
            self._log(f"{tag}: IGNORED duplicate (already buffered as pending)")
            return "duplicate"

        if event.version > st.applied_version + 1:
            st.pending[event.version] = event.status
            self._log(f"{tag}: BUFFERED, waiting for v{st.applied_version + 1}")
            missing = self.missing_versions(event.order_id)
            self._log(f"[{event.order_id}] MISSING version(s) {missing}; pending {sorted(st.pending)}")
            return "buffered"

        # event.version == applied_version + 1: apply, then drain the buffer
        self._apply(event.order_id, st, event.version, event.status, "APPLIED")
        while st.applied_version + 1 in st.pending:
            nxt = st.applied_version + 1
            self._apply(event.order_id, st, nxt, st.pending.pop(nxt), "APPLIED (from buffer)")
        return "applied"

    def _apply(self, order_id, st, version, status, label):
        st.applied_version = version
        st.status = status
        st.applied_history.append(version)
        self._log(f"[{order_id}] v{version} ({status}): {label} -> order now v{version}/{status}")

    def missing_versions(self, order_id: str) -> List[int]:
        """Versions between the last applied one and the highest pending one that haven't arrived."""
        st = self._state(order_id)
        if not st.pending:
            return []
        return [v for v in range(st.applied_version + 1, max(st.pending))
                if v not in st.pending]

    def has_gap(self, order_id: str) -> bool:
        return bool(self.missing_versions(order_id))

    def snapshot(self, order_id: str) -> dict:
        st = self._state(order_id)
        return {
            "order_id": order_id,
            "version": st.applied_version,
            "status": st.status,
            "pending": sorted(st.pending),
            "missing": self.missing_versions(order_id),
            "applied_history": list(st.applied_history),
        }
