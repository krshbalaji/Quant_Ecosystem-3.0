from datetime import date

from quant_ecosystem.market.futures import (
    expiry_calendar,
    continuous_contract_mapper,
    rollover_engine,
)


def test_monthly_expiry():
    exp = expiry_calendar.next_monthly_expiry(
        date(2025, 6, 10)
    )

    assert exp.month == 6


def test_contract_code():
    code = expiry_calendar.contract_code(
        date(2025, 6, 26)
    )

    assert code == "25JUN"


def test_front_month():
    sym = continuous_contract_mapper.front_month_contract(
        "NIFTY",
        date(2025, 6, 10),
    )

    assert "NIFTY" in sym
    assert "FUT" in sym


def test_next_contract():
    sym = continuous_contract_mapper.next_contract(
        "BANKNIFTY",
        date(2025, 6, 10),
    )

    assert "BANKNIFTY" in sym


def test_roll_signal():
    should = rollover_engine.should_roll(
        date(2025, 6, 24),
        roll_days_before=3,
    )

    assert should is True


def test_roll_target():
    tgt = rollover_engine.roll_target(
        "NIFTY",
        date(2025, 6, 24),
    )

    assert "NIFTY" in tgt