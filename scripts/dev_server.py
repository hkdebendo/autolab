"""Local preview of the interface with the recorded researches, without the database and without any paid call.

    python scripts/dev_server.py          then open http://127.0.0.1:8100

The same service as in production (agent/service.py) over a memory store, filled with the recorded researches
(agent/importer.py); new requests are answered by a stand-in (no model is called) and never start a research.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from autolab.agent.importer import RECORDED, import_run
from autolab.agent.service import Service
from autolab.llm.client import Reply
from autolab.store.conversations import MemoryStore

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "static"


class Offline:
    """Stand-in for the models in the preview: explains that this is a preview, starts nothing."""

    provider = "preview"

    def complete_json(self, messages, schema, **kw):
        return {"intent": "other", "status": "unsupported", "domain": "", "title": "Preview request",
                "constraints": [], "reply": "This is a local preview: new researches and follow-up answers run on "
                                            "the AutoLab service, not here."}, []

    def chat(self, messages, **kw):
        return Reply("preview", "none", "This is a local preview: follow-up answers run on the AutoLab service.",
                     "", 0, 0, None, 0.0, 0.0)


svc = Service(MemoryStore(), lambda: [Offline()], lambda cid: None)
for folder, cid, title, request in RECORDED:
    if (ROOT / folder / "result.json").exists():
        import_run(svc, ROOT / folder, cid, title, request)

app = FastAPI()
app.mount("/static", StaticFiles(directory=WEB), name="static")


class Text(BaseModel):
    message: str


class Title(BaseModel):
    title: str


def found(x):
    if x is None:
        raise HTTPException(404, "conversation not found")
    return x


@app.get("/")
@app.get("/c/{cid}")
def page(cid: str | None = None):
    return FileResponse(WEB / "index.html")


@app.get("/api/conversations")
def conversations():
    return [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in c.items()} for c in svc.history()]


@app.post("/api/conversations")
def start(req: Text):
    return svc.start(req.message)


@app.get("/api/conversations/{cid}")
def view(cid: str):
    return found(svc.view(cid))


@app.get("/api/conversations/{cid}/progress")
def progress(cid: str, after: int = 0):
    return found(svc.progress(cid, after))


@app.post("/api/conversations/{cid}/messages")
def post(cid: str, req: Text):
    return found(svc.post(cid, req.message))


@app.post("/api/conversations/{cid}/cancel")
def cancel(cid: str):
    return found(svc.cancel(cid))


@app.patch("/api/conversations/{cid}")
def rename(cid: str, req: Title):
    return found(svc.rename(cid, req.title))


@app.delete("/api/conversations/{cid}")
def delete(cid: str):
    if not svc.delete(cid):
        raise HTTPException(409, "cannot delete")
    return {"deleted": cid}


@app.get("/api/conversations/{cid}/files/{name:path}")
def files(cid: str, name: str):
    art = next((a for a in svc.store.artifacts(cid) if a["name"] == name), None)
    if art is None:
        raise HTTPException(404, "file not available")
    return json.loads(Path(art["path"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)
