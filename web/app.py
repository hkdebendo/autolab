"""Serve the AutoLab web interface and relay its API calls to the AutoLab service on Modal.

Render only serves the page and relays /api/* to AUTOLAB_API_URL (the browser never sees that address). No key lives
here, no research data is stored here (it is in the database, behind the service), no heavy computation happens here.
"""

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
TIMEOUT_S = 120.0  # a new request waits for the scope check; a follow-up for its answer
METHODS = ["GET", "POST", "PATCH", "DELETE"]

app = FastAPI(title="AutoLab")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


@app.get("/")
@app.get("/c/{cid}")
def page(cid: str | None = None) -> FileResponse:
    """The single page (a conversation's address opens it directly)."""
    return FileResponse(HERE / "static" / "index.html")


@app.api_route("/api/{path:path}", methods=METHODS)
async def relay(path: str, request: Request) -> Response:
    """Forward one call to the AutoLab service, passing the status code and the body through."""
    base = os.environ.get("AUTOLAB_API_URL")
    if not base:
        return JSONResponse({"detail": "the AutoLab service is not configured"}, status_code=503)
    body = await request.body()
    headers = {"Content-Type": "application/json"} if body else None
    try:
        async with httpx.AsyncClient(base_url=base.rstrip("/"), timeout=TIMEOUT_S) as client:
            upstream = await client.request(request.method, f"/api/{path}", content=body or None,
                                            params=dict(request.query_params), headers=headers)
    except httpx.HTTPError:
        return JSONResponse({"detail": "the AutoLab service cannot be reached"}, status_code=503)
    return Response(content=upstream.content, status_code=upstream.status_code,
                    media_type=upstream.headers.get("content-type", "application/json"))
