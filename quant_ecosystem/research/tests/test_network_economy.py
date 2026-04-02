import pytest

from quant_ecosystem.operating.network.network_manager import NetworkManager


def test_network_capital_market_and_performance_reputation():
    mgr = NetworkManager(network_name="test_net")

    provider = mgr.create_node("provider", node_type="portfolio")
    borrower = mgr.create_node("borrower", node_type="strategy")

    mgr.connect_nodes("provider", "borrower")

    # provider gets some positive performance history to qualify
    provider.record_performance(cycle_id=1, pnl=5000)

    result = mgr.route_capital_request("borrower", {
        "amount": 10000,
        "strategy": "mean_reversion",
        "expected_return": 0.2,
        "source_reputation": borrower.reputation_score,
        "source": "borrower",
    })

    assert result["status"] == "approved"
    assert result["amount"] > 0
    assert borrower.equity >= 100000

    # confirm trade is logged
    assert any(r["from"] == "provider" for r in borrower.trades_funded)

    # profit sharing settle
    record = borrower.trades_funded[-1]
    borrower.settle_funding_outcome(record, realized_return=0.1)

    assert borrower.equity > 100000
    assert provider.equity > 100000


def test_strategy_market_offer_and_adoption():
    mgr = NetworkManager(network_name="test_net2")
    merchant = mgr.create_node("merchant", node_type="research")
    buyer = mgr.create_node("buyer", node_type="general")

    mgr.connect_nodes("merchant", "buyer")

    offer = merchant.publish_strategy_offer("breakout", 0.9, 5000)
    purchase = buyer.evaluate_strategy_offer(offer)

    assert purchase is not None
    assert purchase["strategy"] == "breakout"
    assert buyer.cash < buyer.initial_capital
    assert merchant.reputation_score >= 100 or merchant.reputation_score <= 100


def test_economic_competition_loop_allocation_and_weak_reduction():
    mgr = NetworkManager(network_name="test_net3")
    strong = mgr.create_node("strong", node_type="portfolio")
    weak = mgr.create_node("weak", node_type="strategy")

    strong.record_performance(cycle_id=1, pnl=10000)
    weak.record_performance(cycle_id=1, pnl=-5000)

    state = mgr.run_economic_competition_cycle(cycle_id=1)
    assert state["status"] == "competition_cycle_executed"
    assert "strong" in state["top_nodes"]
    assert "weak" in state["weak_nodes"]

    assert strong.equity > weak.equity
