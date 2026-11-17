import threading
import unittest

from src.fencing import FencedOrderStore, FencingTokenIssuer


def make():
    logs = []
    return FencedOrderStore(log=logs.append), FencingTokenIssuer(), logs


class FencingTests(unittest.TestCase):
    def test_stale_worker_rejected_after_newer_token(self):
        store, issuer, logs = make()
        token_a = issuer.next_token()   # Worker A: 1
        token_b = issuer.next_token()   # Worker B: 2
        self.assertTrue(store.update("A", "shipped", token_b, "worker-B"))
        self.assertFalse(store.update("A", "cancelled", token_a, "worker-A"))
        rec = store.get("A")
        self.assertEqual((rec.status, rec.highest_token, rec.last_worker), ("shipped", 2, "worker-B"))
        self.assertTrue(any("REJECTED" in l for l in logs))

    def test_older_then_newer_both_accepted_in_order(self):
        store, issuer, _ = make()
        t1, t2 = issuer.next_token(), issuer.next_token()
        self.assertTrue(store.update("A", "paid", t1, "worker-A"))
        self.assertTrue(store.update("A", "shipped", t2, "worker-B"))
        self.assertEqual(store.get("A").status, "shipped")

    def test_same_token_retry_accepted(self):
        store, issuer, _ = make()
        t = issuer.next_token()
        self.assertTrue(store.update("A", "paid", t, "worker-A"))
        self.assertTrue(store.update("A", "paid", t, "worker-A"))

    def test_tokens_tracked_per_order(self):
        store, issuer, _ = make()
        t1, t2 = issuer.next_token(), issuer.next_token()
        store.update("A", "x", t2, "worker-B")
        self.assertTrue(store.update("B", "y", t1, "worker-A"))

    def test_issuer_strictly_increasing_under_threads(self):
        issuer = FencingTokenIssuer()
        out, lock = [], threading.Lock()

        def grab():
            for _ in range(200):
                t = issuer.next_token()
                with lock:
                    out.append(t)

        threads = [threading.Thread(target=grab) for _ in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertEqual(sorted(out), list(range(1, 1601)))


if __name__ == "__main__":
    unittest.main()
