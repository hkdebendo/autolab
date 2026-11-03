"""Local demo of AutoLab: the interface with the recorded researches, no GPU and no database.

    python scripts/dev_server.py          then open http://127.0.0.1:8100

The same service as in production (agent/service.py) over a memory store, filled with the recorded researches
(agent/importer.py), the three home page examples first, under their service ids.

With the keys of .env (MODEL_API_KEY at least), the Meta models work live: Muse Spark checks each request and answers
the follow-up questions, Muse Voice Transcribe takes dictation, and a known request (a home page example, or the
request of a recorded research) is replayed in hybrid mode (agent/hybrid.py): the proposals and every computation come
from the recorded research, while Muse Spark analyses each round, Muse Spark Open reviews the candidates, the summaries
are written again and Muse Wonder reviews the campaign. A new research is not started (it needs GPUs).
Without any key (or with AUTOLAB_DEMO_OFFLINE=1), a known request replays its recorded research as it was, and other
requests get a short notice: no model is called.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from autolab import config
from autolab.agent import hybrid
from autolab.agent.importer import HOME, RECORDED, import_run
from autolab.agent.progress import DOMAIN_STEPS, domain_of, steps_from_events
from autolab.agent.service import Service
from autolab.llm.client import Reply
from autolab.store.conversations import MemoryStore

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "static"
ACTIVE = {"queued", "running", "stopping"}
NEW_RESEARCH = ("This demo replays the three recorded researches of the home page, whose computations are stored in the "
                "repository. A new research computes new crystals with UMA on GPUs: see the README to run it.")
LIVE = None if os.getenv("AUTOLAB_DEMO_OFFLINE") else hybrid.models()  # None: no key, the recorded answers only


class Offline:
    """Stand-in for the models without any key: explains that the models need keys, starts nothing."""

    provider = "preview"

    def complete_json(self, messages, schema, **kw):
        return {"intent": "other", "status": "unsupported", "domain": "", "title": "Preview request",
                "constraints": [], "reply": "No model key is set: add MODEL_API_KEY to .env (see .env.example) so that "
                                            "Muse Spark reads new requests and answers questions."}, []

    def chat(self, messages, **kw):
        return Reply("preview", "none", "No model key is set: add MODEL_API_KEY to .env (see .env.example) so that "
                     "Muse Spark answers questions.", "", 0, 0, None, 0.0, 0.0)


class Demo(Service):
    """A known request replays its recorded research: in hybrid mode with keys, as it was without."""

    def start(self, text: str) -> dict:
        if LIVE is not None:
            return super().start(text)  # Muse Spark reads the request; a known one goes to reuse() below
        src = self.reusable(text)
        if src is None:
            return super().start(text)
        cid = uuid.uuid4().hex[:12]
        scope = src.get("scope") or {}
        self.store.create({"id": cid, "title": src["title"], "goal": text, "domain": src.get("domain"),
                           "status": "answered", "scope": scope})
        self.store.add_message(cid, "user", "request", text)
        reply = next((m["content"] for m in self.store.messages(src["id"]) if m["kind"] == "scope"), "")
        self.store.add_message(cid, "assistant", "scope", reply, data=scope)
        super().reuse(cid, src, scope)
        return self.view(cid)

    def reuse(self, cid: str, src: dict, scope: dict) -> None:
        if LIVE is None:
            return super().reuse(cid, src, scope)
        for a in self.store.artifacts(src["id"]):  # the 3D files of the recorded research
            self.store.add_artifact(cid, a["name"], a["kind"], a["path"], a.get("meta"))
        self.store.update(cid, status="running")
        threading.Thread(target=hybrid.replay, args=(self.store, cid, src["id"], LIVE, self.finish), daemon=True).start()


def new_research(cid: str) -> None:
    """A request that would need new computations: said, nothing started."""
    svc.store.update(cid, status="answered")
    svc.store.add_message(cid, "assistant", "notice", NEW_RESEARCH)


svc = Demo(MemoryStore(), lambda: [LIVE["brain"]] if LIVE else [Offline()], new_research)
home = {folder for folder, _, _ in HOME}
for folder, cid, title in HOME:
    run = ROOT / folder
    if (run / "result.json").exists():
        import_run(svc, run, cid, title, json.loads((run / "result.json").read_text(encoding="utf-8"))["goal"])
for folder, cid, title, request in RECORDED:
    if folder not in home and (ROOT / folder / "result.json").exists():
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
@app.get("/results")
@app.get("/results/{domain}")
@app.get("/settings")
@app.get("/benchmarks")
@app.get("/benchmarks/{domain}")
@app.get("/settings/{domain}")
@app.get("/settings/{domain}/edit")
def page(cid: str | None = None):
    return FileResponse(WEB / "index.html")


@app.get("/api/champions")
def champions():
    return svc.champions()


@app.get("/api/benchmarks")
def tests():
    from autolab.agent.benchmarks_view import benchmarks

    return benchmarks()


@app.get("/api/settings")
def rules():
    from autolab.agent.settings_view import settings

    return settings()


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


@app.websocket("/ws/conversations/{cid}")
async def live(ws: WebSocket, cid: str):
    """As the web server's WebSocket: every event at once, then the new ones while the research plays; the page may
    ask {"steps": n} for the steps after its n first events."""
    await ws.accept()
    p = svc.progress(cid, 0)
    if p is None:
        await ws.close(code=1008)
        return
    events = list(p["events"])
    state = {"status": p["status"]}
    await ws.send_json({"type": "events", "events": p["events"], "status": p["status"], "next": p["next"], "steps": p["steps"]})

    async def answer_steps() -> None:
        while True:
            msg = await ws.receive_json()
            if isinstance(msg, dict) and isinstance(msg.get("steps"), int):
                n = max(0, min(msg["steps"], len(events)))
                done = n >= len(events) and state["status"] not in ACTIVE
                await ws.send_json({"type": "steps", "upto": n,
                                    "steps": steps_from_events(events[:n], "done" if done else "running",
                                                               DOMAIN_STEPS.get(domain_of(events)))})

    reader = asyncio.create_task(answer_steps())
    try:
        while state["status"] in ACTIVE and not reader.done():
            await asyncio.sleep(0.8)
            p = svc.progress(cid, len(events))
            if p is None:
                break
            if p["events"] or p["status"] != state["status"]:
                events.extend(p["events"])
                state["status"] = p["status"]
                await ws.send_json({"type": "events", "events": p["events"], "status": p["status"], "next": p["next"],
                                    "steps": p["steps"]})
        await reader
    except WebSocketDisconnect:
        pass
    finally:
        reader.cancel()
        with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError):
            await reader


@app.websocket("/ws/voice")
async def voice(ws: WebSocket) -> None:
    """Dictation, as in web/app.py: 16 kHz PCM16 frames relayed to Meta Muse Voice Transcribe (the key stays here),
    partial and final transcripts sent back. One recording, at most config.VOICE_MAX_SECONDS of audio."""
    import websockets

    from autolab.llm import voice as asr

    await ws.accept()
    key = os.environ.get("MODEL_API_KEY")
    if not key or os.getenv("AUTOLAB_DEMO_OFFLINE"):
        await ws.send_json({"type": "error", "message": "voice input needs MODEL_API_KEY in .env"})
        await ws.close()
        return
    sent, ended = 0, False
    try:
        async with websockets.connect(config.VOICE_URL, open_timeout=15, max_size=2**20) as up:
            await up.send(asr.handshake(key))

            async def from_meta() -> None:
                async for message in up:
                    event = asr.parse(message)
                    if event:
                        await ws.send_json(event)

            reader = asyncio.create_task(from_meta())
            while not ended:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes"):
                    chunk = msg["bytes"][: max(0, asr.max_bytes() - sent)]
                    if chunk:
                        sent += len(chunk)
                        await up.send(chunk)
                    if sent >= asr.max_bytes():
                        ended = True
                elif msg.get("text") and json.loads(msg["text"]).get("type") == "stop":
                    ended = True
            if ended:
                await up.send(asr.END_STREAM)
                with contextlib.suppress(asyncio.TimeoutError, websockets.ConnectionClosed):
                    await asyncio.wait_for(reader, timeout=15)
            reader.cancel()
    except (OSError, websockets.WebSocketException, asyncio.TimeoutError):
        with contextlib.suppress(Exception):
            await ws.send_json({"type": "error", "message": "the transcription service cannot be reached"})
    except WebSocketDisconnect:
        return
    with contextlib.suppress(Exception):
        await ws.send_json({"type": "done"})
        await ws.close()


if __name__ == "__main__":
    import uvicorn

    print("Models:", "live (" + ", ".join(f"{k}: {v.provider}" for k, v in LIVE.items() if v) + ")" if LIVE
          else "none (no key in .env): recorded answers only")
    uvicorn.run(app, host="127.0.0.1", port=8100)
