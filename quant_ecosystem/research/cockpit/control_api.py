"""Cockpit REST API routes."""

from __future__ import annotations

from datetime import datetime

try:
    from fastapi import Header, HTTPException
    from fastapi.responses import JSONResponse
except Exception:  # pragma: no cover
    Header = None
    HTTPException = Exception
    JSONResponse = None


def register_control_routes(app, command_router, state_api, auth_token: str):
    """Register control-plane endpoints on FastAPI app."""

    def _check_auth(x_operator_token: str):
        if not auth_token:
            return
        if str(x_operator_token or "") != str(auth_token):
            raise HTTPException(status_code=401, detail="unauthorized")

    @app.get("/system/status")
    async def system_status():
        return JSONResponse(state_api.get_system_state())

    @app.get("/strategies")
    async def strategies():
        return JSONResponse(state_api.get_strategies())

    @app.get("/portfolio")
    async def portfolio():
        return JSONResponse(state_api.get_portfolio())

    @app.post("/command")
    async def command(body: dict, x_operator_token: str = Header(default="")):
        _check_auth(x_operator_token)
        cmd = str((body or {}).get("command", "")).strip()
        payload = dict((body or {}).get("payload", {}) or {})
        result = command_router.execute(cmd, payload)
        event = state_api.emit_event(
            event_type="COCKPIT_COMMAND",
            payload={
                "command": cmd,
                "ok": bool(result.get("ok")),
                "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        return JSONResponse({"result": result, "event": event})

