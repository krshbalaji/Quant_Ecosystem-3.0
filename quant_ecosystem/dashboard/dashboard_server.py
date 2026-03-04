"""FastAPI dashboard server for live system map."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Optional

from quant_ecosystem.dashboard.system_state_api import SystemStateAPI
from quant_ecosystem.dashboard.websocket_stream import WebSocketStreamHub

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
except Exception as exc:  # pragma: no cover
    FastAPI = None
    _FASTAPI_IMPORT_ERROR = exc
else:
    _FASTAPI_IMPORT_ERROR = None


def create_dashboard_app(
    router_provider: Optional[Callable[[], object]] = None,
    update_interval_sec: float = 0.25,
):
    """Create the live dashboard app.

    Requires `fastapi` and an ASGI server such as `uvicorn`.
    """
    if FastAPI is None:  # pragma: no cover
        raise ImportError(
            "FastAPI is required for dashboard server. "
            "Install with: pip install fastapi uvicorn"
        ) from _FASTAPI_IMPORT_ERROR

    app = FastAPI(title="Quant Ecosystem Live Dashboard", version="1.0.0")
    state_api = SystemStateAPI(router_provider=router_provider)
    stream_hub = WebSocketStreamHub()
    app.state.system_state_api = state_api
    app.state.stream_hub = stream_hub

    ui_dir = Path(__file__).parent / "dashboard_ui"
    app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="dashboard_ui")

    @app.get("/")
    async def index():
        return FileResponse(str(ui_dir / "index.html"))

    @app.get("/system/state")
    async def system_state():
        return JSONResponse(state_api.get_system_state())

    @app.get("/strategies")
    async def strategies():
        return JSONResponse(state_api.get_strategies())

    @app.get("/events")
    async def events(limit: int = 200):
        return JSONResponse({"events": state_api.get_events(limit=limit)})

    @app.get("/portfolio")
    async def portfolio():
        return JSONResponse(state_api.get_portfolio())

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        await stream_hub.connect(websocket)
        try:
            while True:
                _ = await websocket.receive_text()
        except WebSocketDisconnect:
            await stream_hub.disconnect(websocket)
        except Exception:
            await stream_hub.disconnect(websocket)

    @app.on_event("startup")
    async def startup_event():
        app.state._heartbeat_task = asyncio.create_task(
            stream_hub.heartbeat_loop(state_api=state_api, interval_sec=update_interval_sec)
        )
        state_api.emit_event("DASHBOARD_START", {"interval_sec": update_interval_sec})

    @app.on_event("shutdown")
    async def shutdown_event():
        task = getattr(app.state, "_heartbeat_task", None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        state_api.emit_event("DASHBOARD_STOP", {})

    return app


async def run_dashboard_server_forever(
    router_provider: Optional[Callable[[], object]],
    host: str = "127.0.0.1",
    port: int = 8090,
    update_interval_sec: float = 0.25,
):
    """Run dashboard as a background ASGI service until cancelled."""
    app = create_dashboard_app(
        router_provider=router_provider,
        update_interval_sec=update_interval_sec,
    )
    try:
        import uvicorn
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required for dashboard background service.") from exc

    config = uvicorn.Config(app=app, host=host, port=int(port), log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()
