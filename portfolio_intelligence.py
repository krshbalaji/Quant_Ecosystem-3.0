# portfolio_intelligence.py

from universe import SYMBOL_UNIVERSE

MAX_PER_SECTOR = 1
MAX_SELECTION = 2


def rank_candidates(candidates):
    """
    candidates: list of dicts {symbol, score}
    """
    return sorted(candidates, key=lambda x: x["score"], reverse=True)


def get_sector(symbol):
    for sector, symbols in SYMBOL_UNIVERSE.items():
        if symbol in symbols:
            return sector
    return "OTHER"


def diversify(candidates):

    selected = []
    sector_count = {}

    for c in candidates:

        sector = get_sector(c["symbol"])

        if sector_count.get(sector, 0) >= MAX_PER_SECTOR:
            continue

        selected.append(c)
        sector_count[sector] = sector_count.get(sector, 0) + 1

        if len(selected) >= MAX_SELECTION:
            break

    return selected