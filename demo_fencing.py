from src.fencing import FencedOrderStore, FencingTokenIssuer


def main():
    print("=" * 70)
    print("STALE WORKER TEST: two workers, increasing fencing tokens")
    print("=" * 70)
    issuer = FencingTokenIssuer()
    store = FencedOrderStore()

    token_a = issuer.next_token()
    print(f"\nworker-A acquires lock, fencing token = {token_a}")
    print("worker-A then stalls (e.g. long GC pause) and its lock lease expires...")

    token_b = issuer.next_token()
    print(f"\nworker-B acquires lock, fencing token = {token_b}")
    print(">> worker-B updates order-1 (newer token)")
    store.update("order-1", "shipped", token_b, "worker-B")

    print("\nworker-A wakes up, still believes it holds the lock")
    print(">> worker-A updates order-1 (older token)")
    store.update("order-1", "cancelled", token_a, "worker-A")

    rec = store.get("order-1")
    print(f"\nFINAL STATE: order-1 status={rec.status} highest_token={rec.highest_token} "
          f"last_writer={rec.last_worker}")


if __name__ == "__main__":
    main()
