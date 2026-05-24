"""
Fyers execution adapter
"""

from quant_ecosystem.execution.adapters.base_adapter import BaseExecutionAdapter


ORDER_TYPE_MAP = {
    "MARKET": 2,
    "LIMIT": 1,
}

SIDE_MAP = {
    "BUY": 1,
    "SELL": -1,
}


class FyersExecutionAdapter(BaseExecutionAdapter):

    def translate_order(self, request):
        return {
            "symbol": request.symbol,
            "qty": request.qty,
            "type": ORDER_TYPE_MAP[request.order_type],
            "side": SIDE_MAP[request.side],
            "productType": request.product,
        }

    def translate_modify(self, request):
        return {
            "id": request.order_id,
            "qty": request.qty,
            "limitPrice": request.price,
        }

    def translate_cancel(self, request):
        return {
            "id": request.order_id,
        }