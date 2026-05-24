"""
CoinSwitch execution adapter
"""

from quant_ecosystem.execution.adapters.base_adapter import BaseExecutionAdapter


class CoinSwitchExecutionAdapter(BaseExecutionAdapter):

    def _normalize_symbol(self, symbol):
        return str(symbol).replace("/", "-")

    def translate_order(self, request):
        return {
            "symbol": self._normalize_symbol(request.symbol),
            "quantity": request.qty,
            "side": request.side,
            "order_type": request.order_type,
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