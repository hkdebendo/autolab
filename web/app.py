"""Serve the AutoLab web interface and relay its API calls to the AutoLab service on Modal.

It serves the page, relays /api/* to AUTOLAB_API_URL (the browser never sees that address) and pushes the events of
a research over a WebSocket (/ws/conversations/{id}) as soon as the service has them. No key lives here, no research
data is stored here (it is in the database, behind the service), no heavy computation happens here.
"""

import asyncio
import contextlib
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent


def _env_file_value(name: str) -> str | None:
    """A setting from the project's .env (local runs: no Render dashboard), without any extra package."""
    env = HERE.parent / ".env"
    if not env.exists():
        return None
    for line in env.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == name:
            return value.split("#")[0].strip() or None
    return None

def _service_url() -> str | None:
    return os.environ.get("AUTOLAB_API_URL") or _env_file_value("AUTOLAB_API_URL")


TIMEOUT_S = 120.0  # a new request waits for the scope check; a follow-up for its answer
LIVE_POLL_S = 0.8  # how often the WebSocket asks the service for new events while a research runs
ACTIVE = {"queued", "running", "stopping"}
RUN_STATE = {"queued": "running", "stopping": "running", "running": "running", "done": "done",
             "interrupted": "interrupted", "error": "error"}
METHODS = ["GET", "POST", "PATCH", "DELETE"]

app = FastAPI(title="AutoLab")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@app.get("/")
@app.get("/c/{cid}")
def page(cid: str | None = None) -> FileResponse:
    """The single page (a conversation's address opens it directly)."""
    return FileResponse(HERE / "static" / "index.html")


_CLIENTS: dict[tuple, httpx.AsyncClient] = {}


def _client(base: str) -> httpx.AsyncClient:
    """One client per service address (and event loop): its connections are kept, so each call does not open a new
    secure connection to the service (that cost about half a second per call)."""
    key = (base, id(asyncio.get_running_loop()))
    if key not in _CLIENTS:
        _CLIENTS[key] = httpx.AsyncClient(base_url=base.rstrip("/"), timeout=TIMEOUT_S)
    return _CLIENTS[key]


@app.api_route("/api/{path:path}", methods=METHODS)
async def relay(path: str, request: Request) -> Response:
    """Forward one call to the AutoLab service, passing the status code and the body through."""
    base = _service_url()
    if not base:
        return JSONResponse({"detail": "the AutoLab service is not configured"}, status_code=503)
    body = await request.body()
    headers = {"Content-Type": "application/json"} if body else None
    try:
        upstream = await _client(base).request(request.method, f"/api/{path}", content=body or None,
                                               params=dict(request.query_params), headers=headers)
    except httpx.HTTPError:
        return JSONResponse({"detail": "the AutoLab service cannot be reached"}, status_code=503)
    return Response(content=upstream.content, status_code=upstream.status_code,
                    media_type=upstream.headers.get("content-type", "application/json"))


def _steps(events: list[dict], upto: int, status: str) -> list[dict] | None:
    """Steps of the research after its first `upto` events (the page shows the steps as it plays the events)."""
    try:
        from autolab.agent.progress import DOMAIN_STEPS, domain_of, steps_from_events
    except ImportError:  # the page then keeps the steps the service sent
        return None
    state = "running" if upto < len(events) else RUN_STATE.get(status, "done")
    return steps_from_events(events[:upto], state, DOMAIN_STEPS.get(domain_of(events)))  # domain from the whole run


@app.websocket("/ws/conversations/{cid}")
async def live(ws: WebSocket, cid: str) -> None:
    """Push the events of a conversation: everything at once, then the new ones while the research runs. The page may
    ask {"steps": n} for the steps after its n first events."""
    await ws.accept()
    base = _service_url()
    if not base:
        await ws.close(code=1011, reason="the AutoLab service is not configured")
        return
    events: list[dict] = []
    state = {"status": None}

    async def pull(client: httpx.AsyncClient) -> dict:
        r = await client.get(f"/api/conversations/{cid}/progress", params={"after": len(events)})
        r.raise_for_status()
        p = r.json()
        events.extend(p["events"])
        return p

    async def answer_steps() -> None:
        while True:
            msg = await ws.receive_json()
            if isinstance(msg, dict) and isinstance(msg.get("steps"), int):
                n = max(0, min(msg["steps"], len(events)))
                await ws.send_json({"type": "steps", "upto": n, "steps": _steps(events, n, state["status"])})

    async with httpx.AsyncClient(base_url=base.rstrip("/"), timeout=30.0) as client:
        reader = asyncio.create_task(answer_steps())
        try:
            while True:
                try:
                    p = await pull(client)
                except (httpx.HTTPError, ValueError):
                    await asyncio.sleep(LIVE_POLL_S * 3)  # the service is busy or unreachable: try again soon
                    continue
                changed = p["events"] or p["status"] != state["status"]
                state["status"] = p["status"]
                if changed:
                    await ws.send_json({"type": "events", "events": p["events"], "status": p["status"],
                                        "next": p["next"], "steps": p["steps"]})
                if reader.done():
                    break
                if p["status"] not in ACTIVE:
                    await reader  # finished: answer the page's step questions until it leaves
                    break
                await asyncio.sleep(LIVE_POLL_S)
        except WebSocketDisconnect:
            pass
        finally:
            reader.cancel()
            with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
                await reader
