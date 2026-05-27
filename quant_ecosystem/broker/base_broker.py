from abc import ABC, abstractmethod
from typing import Any, Dict, List

from quant_ecosystem.broker.broker_capabilities import BrokerCapabilities


class BaseBroker(ABC):
    """
    QE3 canonical broker adapter contract.

    All production brokers must inherit this.

    Execution router relies on this interface instead of broker-specific hacks.
    """

    capabilities: BrokerCapabilities = BrokerCapabilities()

    @property
    def broker_name(self) -> str:
        return self.capabilities.broker_name

    def validate_route(self, market: str, asset: str) -> None:
        self.capabilities.validate_route(market, asset)

    def supports_reconciliation(self) -> bool:
        return self.capabilities.supports_reconciliation

    def supports_cancel_order(self) -> bool:
        return self.capabilities.supports_cancel_order

    def supports_modify_order(self) -> bool:
        return self.capabilities.supports_modify_order

    def supports_positions_sync(self) -> bool:
        return self.capabilities.supports_positions_sync

    def supports_balance_sync(self) -> bool:
        return self.capabilities.supports_balance_sync

    def supports_order_history(self) -> bool:
        return self.capabilities.supports_order_history

    def supports_market_data_snapshot(self) -> bool:
        return self.capabilities.supports_market_data_snapshot

    def supports_live_streaming(self) -> bool:
        return self.capabilities.supports_live_streaming

    def health_check(self) -> Dict[str, Any]:
        """
        Default health check.
        Override in production brokers.
        """
        return {
            "broker": self.broker_name,
            "healthy": True,
            "details": "default health check",
        }
    def connect(self) -> None:
        """
        Establish broker connectivity/session.
        Override in live brokers.
        """
        return None

    def is_authenticated(self) -> bool:
        """
        Canonical broker auth state.
        """
        return True

    def authenticate(self) -> None:
        """
        Force authentication.
        """
        self.connect()

    def refresh_session(self) -> None:
        """
        Refresh broker auth/session.
        Override in token-based brokers.
        """
        self.authenticate()

    def invalidate_session(self) -> None:
        """
        Mark session invalid.
        """
        return None

    def session_health(self) -> Dict[str, Any]:
        """
        Canonical session health contract.
        """
        return {
            "broker": self.broker_name,
            "authenticated": self.is_authenticated(),
            "details": "default session state",
        }

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        price: float,
        fee: float = 0.0,
        meta: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Place order using broker-native API.
        """
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        if not self.supports_cancel_order():
            raise RuntimeError(
                f"{self.broker_name} does not support cancel_order"
            )
        raise NotImplementedError

    def modify_order(
        self,
        order_id: str,
        qty: int | None = None,
        price: float | None = None,
    ) -> Dict[str, Any]:
        if not self.supports_modify_order():
            raise RuntimeError(
                f"{self.broker_name} does not support modify_order"
            )
        raise NotImplementedError

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        if not self.supports_reconciliation():
            raise RuntimeError(
                f"{self.broker_name} does not support reconciliation"
            )
        raise NotImplementedError

    def get_order_history(self) -> List[Dict[str, Any]]:
        if not self.supports_order_history():
            raise RuntimeError(
                f"{self.broker_name} does not support order history"
            )
        raise NotImplementedError

    def get_positions(self) -> List[Dict[str, Any]]:
        if not self.supports_positions_sync():
            raise RuntimeError(
                f"{self.broker_name} does not support positions sync"
            )
        raise NotImplementedError

    def get_balance(self) -> Dict[str, Any]:
        if not self.supports_balance_sync():
            raise RuntimeError(
                f"{self.broker_name} does not support balance sync"
            )
        raise NotImplementedError

    def get_holdings(self) -> List[Dict[str, Any]]:
        if not self.capabilities.supports_holdings_sync:
            raise RuntimeError(
                f"{self.broker_name} does not support holdings sync"
            )
        raise NotImplementedError

    def get_ltp(self, symbol: str) -> Dict[str, Any]:
        if not self.capabilities.supports_ltp:
            raise RuntimeError(
                f"{self.broker_name} does not support LTP"
            )
        raise NotImplementedError

    def get_orderbook(self) -> List[Dict[str, Any]]:
        if not self.capabilities.supports_orderbook:
            raise RuntimeError(
                f"{self.broker_name} does not support orderbook"
            )
        raise NotImplementedError