"""
Groww execution adapter
"""

from quant_ecosystem.execution.adapters.base_adapter import BaseExecutionAdapter


class GrowwExecutionAdapter(BaseExecutionAdapter):

    def translate_order(self, request):
        return {
            "instrument": request.symbol,
            "quantity": request.qty,
            "side": request.side,
            "order_type": request.order_type,
            "product": request.product,
            "price": request.price,
        }

    def translate_modify(self, request):
        return {
            "order_id": request.order_id,
            "quantity": request.qty,
            "price": request.price,
        }

    def translate_cancel(self, request):
        return {
            "order_id": request.order_id,
        }