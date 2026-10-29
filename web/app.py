"""Serve the AutoLab jury page.

Replay mode reads the recorded reference run from disk (path in web/config.json,
key ``reference_run``). Live mode relays ``/api/live/*`` to the Modal agent API
(``AUTOLAB_API_URL``); the browser never sees that URL. No key lives here and no
heavy computation happens here; Render only serves the page.
"""

import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
REF_DIR = (HERE.parent / json.loads((HERE / "config.json").read_text(encoding="utf-8"))["reference_run"]).resolve()

LIVE_TIMEOUT_S = 70.0
LIVE_DISABLED = "live mode disabled"

app = FastAPI(title="AutoLab jury page")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    """Serve the page (plain HTML + CSS + JavaScript, no build step)."""
    return FileResponse(HERE / "static" / "index.html")


def _replay_path(name: str) -> Path | None:
    """Resolve a replay file name inside the reference run, or None if off-list."""
    ok = (
        name in ("events.jsonl", "result.json", "report.md", "replay/index.json")
        or (name.startswith("replay/structures/") and name.endswith(".json") and name.count("/") == 2)
        or (name.startswith("replay/md/") and name.endswith(".json") and name.count("/") == 2)
    )
    if not ok or ".." in name or "\\" in name:
        return None
    path = (REF_DIR / name).resolve()
    if REF_DIR not in path.parents:
        return None
    return path if path.is_file() else None


@app.get("/api/replay/{name:path}")
def replay(name: str) -> Response:
    """Serve one file of the reference run (events as a JSON array, in file order)."""
    if name == "report.html":
        import markdown

        html = markdown.markdown((REF_DIR / "report.md").read_text(encoding="utf-8"),
                                 extensions=["tables", "fenced_code", "md_in_html"])
        return Response(html, media_type="text/html; charset=utf-8")

    if name == "report.page":  # the whole report as a page of its own (opened in a new tab)
        import markdown

        body = markdown.markdown((REF_DIR / "report.md").read_text(encoding="utf-8"),
                                 extensions=["tables", "fenced_code", "md_in_html"])
        page = ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' "
                "content='width=device-width, initial-scale=1'><title>AutoLab report</title>"
                "<link rel='stylesheet' href='/static/styles.css'></head><body class='report-page'>"
                f"{body}</body></html>")
        return Response(page, media_type="text/html; charset=utf-8")
    path = _replay_path(name)
    if path is None:
        return JSONResponse({"detail": "unknown replay file"}, status_code=404)
    if name == "events.jsonl":
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return JSONResponse(events)
    if path.suffix == ".json":
        return JSONResponse(json.loads(path.read_text(encoding="utf-8")))
    return Response(path.read_text(encoding="utf-8"), media_type="text/markdown; charset=utf-8")


def _live_base() -> str | None:
    """Modal API base URL, or None when live mode is off (default)."""
    if os.environ.get("AUTOLAB_LIVE") != "1":
        return None
    return os.environ.get("AUTOLAB_API_URL") or None


async def _relay(method: str, path: str, body: bytes | None = None, params: dict | None = None) -> Response:
    """Forward one call to the Modal agent API, passing status and body through."""
    base = _live_base()
    if base is None:
        return JSONResponse({"detail": LIVE_DISABLED}, status_code=403)
    headers = {"Content-Type": "application/json"} if body is not None else None
    try:
        async with httpx.AsyncClient(base_url=base.rstrip("/"), timeout=LIVE_TIMEOUT_S) as client:
            upstream = await client.request(method, path, content=body, params=params, headers=headers)
    except httpx.HTTPError:
        return JSONResponse({"detail": "live backend unreachable"}, status_code=503)
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


@app.get("/api/live/health")
async def live_health() -> Response:
    """Relay the Modal queue state (busy, runs used/allowed)."""
    return await _relay("GET", "/api/health")


@app.post("/api/live/runs")
async def live_start(request: Request) -> Response:
    """Relay a live run request (goal + jury access code, checked on Modal)."""
    return await _relay("POST", "/api/runs", body=await request.body())


@app.get("/api/live/runs/{run_id}/events")
async def live_events(run_id: str, after: int = 0) -> Response:
    """Relay one poll of the live events (``after`` = last seen index)."""
    return await _relay("GET", f"/api/runs/{run_id}/events", params={"after": after})


@app.get("/api/live/runs/{run_id}/result")
async def live_result(run_id: str) -> Response:
    """Relay the live result (404 until the run is done)."""
    return await _relay("GET", f"/api/runs/{run_id}/result")
