# CMPE 273 Module 7: Versioned Event Ordering & Fencing Tokens

A small Python (3.9+, standard library only) program that demonstrates:

1. **Versioned event ordering**: out-of-order delivery is buffered and applied in version order, and duplicates are ignored.
2. **Missing-event handling**: a later version never jumps ahead of a missing earlier one; the gap is recorded as pending.
3. **Fencing tokens**: a stale worker holding an older token is rejected by the store.

Each order update carries `order_id`, `version`, and `status`.

## Project layout

| File | Purpose |
|---|---|
| `src/ordering.py` | `OrderProcessor`: buffering, in-order apply, dedup, gap detection |
| `src/fencing.py` | `FencingTokenIssuer` and `FencedOrderStore` (store rejects stale tokens) |
| `demo_ordering.py` | Scenario 1 (2 → 1 → 2) and Scenario 2 (only v3) |
| `demo_fencing.py` | Two workers, stale token rejected |
| `tests/` | `unittest` suite (12 tests) |
| `run_all.sh` | Runs both demos and tests, saves output to `evidence/*.txt` |

## How to run

```bash
python3 demo_ordering.py                       # event ordering, duplicates, missing event
python3 demo_fencing.py                        # stale worker rejection
python3 -m unittest discover -s tests -t . -v  # all tests
./run_all.sh                                   # everything, logs saved to evidence/
```

No dependencies to install.

## How it works

**Ordering.** For each order the processor tracks `applied_version` (0 = nothing yet), the current `status`, and a `pending` buffer.

- `version <= applied_version` → duplicate, ignored.
- `version == applied_version + 1` → applied, then any consecutive buffered versions are applied too.
- `version > applied_version + 1` → buffered; the missing versions are recorded and the status is **not** changed.

**Fencing.** A token issuer hands out strictly increasing integers (simulating a lock service). The store remembers the highest token it has seen per order and rejects any write with a lower one. The *resource* enforces this, so a worker that paused and wrongly believes it still holds the lock can't overwrite newer data.

## Example of correct event ordering (delivery: v2, v1, v2)

| Arrival | Action | Order state after |
|---|---|---|
| v2 `shipped` | Buffered, waiting for v1 | version 0, status `None`, pending `[2]`, missing `[1]` |
| v1 `paid` | Applied, then v2 drained from buffer | version 2, status `shipped`, applied order `[1, 2]` |
| v2 `shipped` (again) | Ignored as duplicate | version 2, status `shipped`, applied order `[1, 2]` |

Actual output (`python3 demo_ordering.py`, full log in [evidence/demo_ordering.txt](evidence/demo_ordering.txt)):

```
>> received order_id=order-1 version=2 status=shipped
[order-1] v2 (shipped): BUFFERED, waiting for v1
[order-1] MISSING version(s) [1]; pending [2]
    STATE: version=0 status=None pending=[2] missing=[1] applied_order=[]

>> received order_id=order-1 version=1 status=paid
[order-1] v1 (paid): APPLIED -> order now v1/paid
[order-1] v2 (shipped): APPLIED (from buffer) -> order now v2/shipped
    STATE: version=2 status=shipped pending=[] missing=[] applied_order=[1, 2]
```

## Evidence: duplicate handling

The second delivery of v2 is ignored. State and applied order are unchanged.

```
>> received order_id=order-1 version=2 status=shipped
[order-1] v2 (shipped): IGNORED duplicate (already applied; current v2)
    STATE: version=2 status=shipped pending=[] missing=[] applied_order=[1, 2]
```

Also covered by `test_delivery_2_1_2`, `test_duplicate_of_applied_version_ignored`, and `test_duplicate_of_pending_version_ignored`.

## Evidence: missing-event case

Only v3 arrives while v1 and v2 are missing. The order does not jump ahead (status stays `None`), and v3 is held as pending with `[1, 2]` recorded as missing. When v1 and v2 arrive later, everything applies in order.

```
>> received order_id=order-2 version=3 status=delivered
[order-2] v3 (delivered): BUFFERED, waiting for v1
[order-2] MISSING version(s) [1, 2]; pending [3]
    STATE: version=0 status=None pending=[3] missing=[1, 2] applied_order=[]

>> received order_id=order-2 version=1 status=paid
[order-2] v1 (paid): APPLIED -> order now v1/paid
    STATE: version=1 status=paid pending=[3] missing=[2] applied_order=[1]

>> received order_id=order-2 version=2 status=shipped
[order-2] v2 (shipped): APPLIED -> order now v2/shipped
[order-2] v3 (delivered): APPLIED (from buffer) -> order now v3/delivered
    STATE: version=3 status=delivered pending=[] missing=[] applied_order=[1, 2, 3]
```

Covered by `test_only_later_version_does_not_jump_ahead`, `test_gap_after_partial_progress`, and `test_gap_filled_applies_in_order`.

## Evidence: stale-worker rejection

Worker A gets token 1 and stalls. Worker B gets token 2 and updates the order. When A wakes up and writes with token 1, the store rejects it.

```
worker-A acquires lock, fencing token = 1
worker-A then stalls (e.g. long GC pause) and its lock lease expires...

worker-B acquires lock, fencing token = 2
>> worker-B updates order-1 (newer token)
[order-1] worker-B token=2 status=shipped: ACCEPTED

worker-A wakes up, still believes it holds the lock
>> worker-A updates order-1 (older token)
[order-1] worker-A token=1 status=cancelled: REJECTED (stale token; store has seen token 2)

FINAL STATE: order-1 status=shipped highest_token=2 last_writer=worker-B
```

Covered by `test_stale_worker_rejected_after_newer_token`. Full log: [evidence/demo_fencing.txt](evidence/demo_fencing.txt).

## Test results

```
Ran 12 tests in 0.002s

OK
```

Full log: [evidence/tests.txt](evidence/tests.txt).

## Screenshots

<!-- Screenshots are added in the final evidence phase. -->

## Reflection

