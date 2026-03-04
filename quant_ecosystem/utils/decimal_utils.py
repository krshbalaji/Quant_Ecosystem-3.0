from decimal import Decimal, ROUND_HALF_UP


def quantize(value, places=4):
    scale = "1." + ("0" * places)
    return float(Decimal(str(value)).quantize(Decimal(scale), rounding=ROUND_HALF_UP))

