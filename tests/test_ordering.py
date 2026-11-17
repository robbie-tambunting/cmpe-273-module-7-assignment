import unittest

from src.ordering import Event, OrderProcessor


def make():
    logs = []
    return OrderProcessor(log=logs.append), logs


class OrderingTests(unittest.TestCase):
    def test_delivery_2_1_2(self):
        p, _ = make()
        self.assertEqual(p.apply_event(Event("A", 2, "shipped")), "buffered")
        self.assertEqual(p.snapshot("A")["version"], 0)
        self.assertIsNone(p.snapshot("A")["status"])
        self.assertEqual(p.apply_event(Event("A", 1, "paid")), "applied")
        snap = p.snapshot("A")
        self.assertEqual((snap["version"], snap["status"]), (2, "shipped"))
        self.assertEqual(snap["applied_history"], [1, 2])
        self.assertEqual(p.apply_event(Event("A", 2, "shipped")), "duplicate")
        snap = p.snapshot("A")
        self.assertEqual((snap["version"], snap["status"]), (2, "shipped"))
        self.assertEqual(snap["applied_history"], [1, 2])

    def test_duplicate_of_applied_version_ignored(self):
        p, _ = make()
        p.apply_event(Event("A", 1, "paid"))
        self.assertEqual(p.apply_event(Event("A", 1, "CHANGED")), "duplicate")
        self.assertEqual(p.snapshot("A")["status"], "paid")

    def test_duplicate_of_pending_version_ignored(self):
        p, _ = make()
        p.apply_event(Event("A", 3, "delivered"))
        self.assertEqual(p.apply_event(Event("A", 3, "delivered")), "duplicate")
        self.assertEqual(p.snapshot("A")["pending"], [3])

    def test_multiple_orders_independent(self):
        p, _ = make()
        p.apply_event(Event("A", 2, "shipped"))
        p.apply_event(Event("B", 1, "paid"))
        self.assertEqual(p.snapshot("A")["version"], 0)
        self.assertEqual(p.snapshot("B")["version"], 1)

    # --- missing event ---
    def test_only_later_version_does_not_jump_ahead(self):
        p, logs = make()
        p.apply_event(Event("A", 3, "delivered"))
        snap = p.snapshot("A")
        self.assertEqual(snap["version"], 0)
        self.assertIsNone(snap["status"])
        self.assertEqual(snap["pending"], [3])
        self.assertEqual(snap["missing"], [1, 2])
        self.assertTrue(p.has_gap("A"))
        self.assertTrue(any("MISSING version(s) [1, 2]" in l for l in logs))

    def test_gap_after_partial_progress(self):
        p, _ = make()
        p.apply_event(Event("A", 1, "paid"))
        p.apply_event(Event("A", 3, "delivered"))
        snap = p.snapshot("A")
        self.assertEqual((snap["version"], snap["status"]), (1, "paid"))
        self.assertEqual(snap["missing"], [2])

    def test_gap_filled_applies_in_order(self):
        p, _ = make()
        p.apply_event(Event("A", 3, "delivered"))
        p.apply_event(Event("A", 1, "paid"))
        self.assertEqual(p.snapshot("A")["missing"], [2])
        p.apply_event(Event("A", 2, "shipped"))
        snap = p.snapshot("A")
        self.assertEqual((snap["version"], snap["status"]), (3, "delivered"))
        self.assertEqual(snap["applied_history"], [1, 2, 3])
        self.assertFalse(p.has_gap("A"))


if __name__ == "__main__":
    unittest.main()
