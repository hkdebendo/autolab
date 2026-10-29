"""AutoLab service on Modal (production): the conversations API used by the web page, and the researches.

Deploy:   modal deploy modal_app/agent_app.py      (after modal_app/uma_app.py)

- api: the web API of the interface (conversations, messages, progress, stop, rename, delete, 3D files), over the
  Supabase PostgreSQL database (DATABASE_URL); scope checks and follow-up answers by the language models.
- run_research: one research on CPU (orchestration, Materials Project, ALIGNN, pymatgen); UMA relaxations and MD go
  to the GPU functions of autolab-uma. It reads and writes the caches of the autolab-data volume (the whole .cache of
  the development PC), so nothing already computed is computed again; its events go to the database as they happen.

Keys live only in the Modal secret config.MODAL_KEYS_SECRET, created by the owner (MODEL_API_KEY, BASETEN_API_KEY,
MP_API_KEY, FIREWORKS_API_KEY, GLIMMER_DEPLOYMENT, DATABASE_URL). No access code (owner, 2026-10-29): one research at
a time and config.LIVE_MAX_RUNS new researches in all protect the budget. No warm container, short limits.
"""

import modal

from autolab import config

DATA = "/data"
REFERENCE = "/app/reference"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.13.0", extra_index_url="https://download.pytorch.org/whl/cpu")
    .pip_install("pymatgen==2026.10.24", "mp-api==0.47.0", "ase==3.29.0", "openai==3.40.0", "python-dotenv==1.2.4",
                 "alignn==2026.8.11", "jarvis-tools==2026.6.12", "fastapi[standard]", "psycopg[binary]==3.2.12")
    .env({"AUTOLAB_CACHE_DIR": f"{DATA}/cache", "SIM_BACKEND": "modal"})
    .add_local_python_source("autolab")
    .add_local_dir("db", "/root/db")
    .add_local_dir("results/2026-10-29_reference_run", REFERENCE, ignore=["replay/**", "console*.log"])
)
data = modal.Volume.from_name(config.MODAL_DATA_VOLUME, create_if_missing=True)
keys = modal.Secret.from_name(config.MODAL_KEYS_SECRET)

app = modal.App(config.MODAL_AGENT_APP, image=image)


def _service():
    from autolab.agent.runs import client
    from autolab.agent.service import Service
    from autolab.store.conversations import PostgresStore

    def models():
        return [client(config.LLM_PROVIDER, config.LLM_COST_CAPS_USD[config.LLM_PROVIDER]),
                client(config.LLM_FALLBACK_PROVIDER, config.LLM_COST_CAPS_USD[config.LLM_FALLBACK_PROVIDER])]

    return Service(PostgresStore(), models, lambda cid: run_research.spawn(cid))


def _alignn_models() -> None:
    """ALIGNN looks for its models in ~/.alignn2_models; they come from the cache (zips fetched once via Colab)."""
    import glob
    import os
    import zipfile

    root = os.path.expanduser("~/.alignn2_models")
    for z in glob.glob(f"{DATA}/cache/alignn/*.zip"):
        name = os.path.splitext(os.path.basename(z))[0]
        if not os.path.isdir(f"{root}/{name}"):
            os.makedirs(f"{root}/{name}", exist_ok=True)
            zipfile.ZipFile(z).extractall(f"{root}/{name}")


@app.function(cpu=2.0, memory=6144, volumes={DATA: data}, secrets=[keys], timeout=config.LIVE_RUN_TIMEOUT_S,
              max_containers=1)
def run_research(cid: str) -> dict | None:
    from autolab.agent.events import EventLog
    from autolab.agent.loop import Agent
    from autolab.agent.runs import analyst_client, client, load_prior, summarizer
    from autolab.analysis.replay_export import export_run
    from autolab.sim.backend import RelaxBudget

    _alignn_models()
    svc = _service()

    def make_agent(events: EventLog, should_stop) -> Agent:
        brain = client(config.LLM_PROVIDER, config.LLM_COST_CAPS_USD[config.LLM_PROVIDER])
        fallback = client(config.LLM_FALLBACK_PROVIDER, config.LLM_COST_CAPS_USD[config.LLM_FALLBACK_PROVIDER])
        return Agent(brain or fallback, fallback if brain else None, events=events,
                     budget=RelaxBudget(config.LIVE_MAX_RELAXATIONS),
                     analyst=analyst_client(config.CANDIDATE_ANALYSIS_PROVIDER),
                     novelty_client=client(config.NOVELTY_PROVIDER, config.NOVELTY_COST_CAP_USD),
                     summarizer=summarizer(events), should_stop=should_stop)

    def export(cid_: str, result: dict) -> None:
        index = export_run(result, f"{DATA}/runs/{cid_}")
        svc.store.add_artifact(cid_, "index.json", "index", f"runs/{cid_}/index.json")
        for kind in ("structures", "md"):
            for e in index[kind]:
                svc.store.add_artifact(cid_, e["file"], kind.rstrip("s"), f"runs/{cid_}/{e['file']}", e)

    try:
        result = svc.run(cid, make_agent, prior=load_prior(f"{REFERENCE}/result.json", "ref"), export=export)
        return {"conversation": cid, "final_ranking": (result or {}).get("final_ranking")}
    finally:
        data.commit()  # new cache entries and the 3D files stay for the next researches


@app.function(secrets=[keys], volumes={DATA: data}, timeout=180, max_containers=2, scaledown_window=120)
@modal.asgi_app()
def api():
    import json

    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    svc = _service()
    web = FastAPI(title="AutoLab")
    web.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "PATCH", "DELETE"],
                       allow_headers=["*"])

    class Text(BaseModel):
        message: str

    class Title(BaseModel):
        title: str

    def found(x):
        if x is None:
            raise HTTPException(status_code=404, detail="conversation not found")
        return x

    @web.get("/api/health")
    def health():
        active = svc.store.active_research()
        return {"ok": True, "busy": bool(active), "researches_used": svc.store.live_runs_used(),
                "researches_allowed": config.LIVE_MAX_RUNS}

    @web.get("/api/conversations")
    def conversations():
        return [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in c.items()} for c in svc.history()]

    @web.post("/api/conversations")
    def start(req: Text):
        try:
            return svc.start(req.message)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @web.get("/api/conversations/{cid}")
    def view(cid: str):
        return found(svc.view(cid))

    @web.get("/api/conversations/{cid}/progress")
    def progress(cid: str, after: int = 0):
        return found(svc.progress(cid, after))

    @web.post("/api/conversations/{cid}/messages")
    def post(cid: str, req: Text):
        try:
            return found(svc.post(cid, req.message))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @web.post("/api/conversations/{cid}/cancel")
    def cancel(cid: str):
        return found(svc.cancel(cid))

    @web.patch("/api/conversations/{cid}")
    def rename(cid: str, req: Title):
        return found(svc.rename(cid, req.title))

    @web.delete("/api/conversations/{cid}")
    def delete(cid: str):
        if not svc.delete(cid):
            raise HTTPException(status_code=409, detail="stop the research before deleting it, or it does not exist")
        return {"deleted": cid}

    @web.get("/api/conversations/{cid}/result")
    def result(cid: str):
        found(svc.store.get(cid))
        return found(svc.store.result(cid))

    @web.get("/api/conversations/{cid}/files/{name:path}")
    def files(cid: str, name: str):
        """A 3D file of the conversation (structure, MD animation, index), from the volume."""
        art = next((a for a in svc.store.artifacts(cid) if a["name"] == name), None)
        if art is None:
            raise HTTPException(status_code=404, detail="file not available")
        data.reload()
        with open(f"{DATA}/{art['path']}", encoding="utf-8") as f:
            return json.load(f)

    return web
