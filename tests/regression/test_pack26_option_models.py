from quant_ecosystem.market.options import (
    CanonicalOptionContract,
    CanonicalOptionChain,
    OptionChainNormalizer,
)


def test_option_contract_mid():
    c = CanonicalOptionContract(
        symbol="NIFTYCE",
        underlying="NIFTY",
        strike=24500,
        expiry="2025-06-26",
        option_type="CE",
        bid=100,
        ask=110,
    )

    assert c.mid_price == 105.0


def test_option_chain_map():
    ce = CanonicalOptionContract(
        symbol="CE1",
        underlying="NIFTY",
        strike=24500,
        expiry="2025-06-26",
        option_type="CE",
    )

    pe = CanonicalOptionContract(
        symbol="PE1",
        underlying="NIFTY",
        strike=24500,
        expiry="2025-06-26",
        option_type="PE",
    )

    chain = CanonicalOptionChain(
        underlying="NIFTY",
        expiry="2025-06-26",
        calls=[ce],
        puts=[pe],
    )

    sm = chain.strike_map()

    assert 24500 in sm
    assert "CE" in sm[24500]
    assert "PE" in sm[24500]


def test_fyers_normalizer():
    norm = OptionChainNormalizer()

    raw = [
        {
            "symbol": "NIFTY24500CE",
            "strike": 24500,
            "option_type": "CE",
            "bid": 100,
            "ask": 110,
            "ltp": 105,
            "volume": 1000,
            "open_interest": 5000,
            "iv": 18.5,
        }
    ]

    chain = norm.normalize_fyers(
        underlying="NIFTY",
        expiry="2025-06-26",
        raw_chain=raw,
        spot_price=24480,
    )

    assert len(chain.calls) == 1
    assert chain.calls[0].implied_volatility == 18.5