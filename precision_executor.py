# precision_executor.py

def execute_signal(symbol, side, qty, price, order_type="LIMIT"):
    """
    Clean execution (paper mode, no broker dependency)
    """

    print(f"[ORDER] {order_type} {side} {qty} {symbol} @ {price}")

    # Simulated execution
    print(f"[BROKER PAPER] {side} {qty} {symbol} @ {price}")

    return True