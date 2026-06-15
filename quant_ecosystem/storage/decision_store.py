from typing import Any, Dict
from uuid import uuid4

from quant_ecosystem.contracts.portfolio_decision import PortfolioDecision
from quant_ecosystem.storage.organism_db import dumps_json, get_connection, init_db, utc_now


def record_decision(portfolio_decision: PortfolioDecision | Dict[str, Any]) -> str:
    init_db()
    if isinstance(portfolio_decision, PortfolioDecision):
        data = portfolio_decision.to_dict()
    else:
        data = PortfolioDecision.from_mapping(portfolio_decision).to_dict()
    row_id = str(uuid4())
    now = utc_now()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO portfolio_decisions (
                id, created_at, updated_at, action, symbol, confidence,
                reason, profile, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                now,
                now,
                data["action"],
                data["symbol"],
                data["confidence"],
                data["reason"],
                data["profile"],
                dumps_json(data["metadata"]),
            ),
        )
    return row_id
