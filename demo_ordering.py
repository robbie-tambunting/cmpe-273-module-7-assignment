from src.ordering import Event, OrderProcessor


def show(p, order_id):
    s = p.snapshot(order_id)
    print(f"    STATE: version={s['version']} status={s['status']} "
          f"pending={s['pending']} missing={s['missing']} applied_order={s['applied_history']}")


def scenario_1():
    print("=" * 70)
    print("SCENARIO 1: delivery order  version 2 -> version 1 -> version 2 again")
    print("=" * 70)
    p = OrderProcessor()
    for ev in [Event("order-1", 2, "shipped"),
               Event("order-1", 1, "paid"),
               Event("order-1", 2, "shipped")]:
        print(f"\n>> received order_id={ev.order_id} version={ev.version} status={ev.status}")
        p.apply_event(ev)
        show(p, ev.order_id)


def scenario_2():
    print()
    print("=" * 70)
    print("SCENARIO 2: missing event - only version 3 arrives (v1, v2 missing)")
    print("=" * 70)
    p = OrderProcessor()
    ev = Event("order-2", 3, "delivered")
    print(f"\n>> received order_id={ev.order_id} version={ev.version} status={ev.status}")
    p.apply_event(ev)
    show(p, "order-2")
    print("\n    Order did NOT jump ahead: status is still None, v3 is held as pending.")

    print("\n-- later, the missing events arrive (v1 then v2) --")
    for ev in [Event("order-2", 1, "paid"), Event("order-2", 2, "shipped")]:
        print(f"\n>> received order_id={ev.order_id} version={ev.version} status={ev.status}")
        p.apply_event(ev)
        show(p, ev.order_id)


if __name__ == "__main__":
    scenario_1()
    scenario_2()
