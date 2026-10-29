"""AutoLab agent on Modal (production): the whole loop runs here, Render only shows it.

Deploy:   modal deploy modal_app/agent_app.py      (after modal_app/uma_app.py)

- run_agent: one live run on CPU (orchestration, Materials Project, ALIGNN, pymatgen); UMA relaxations and MD go to
  the GPU functions of autolab-uma. Reads and writes the caches of the autolab-data volume (the whole .cache of the
  development PC), so nothing already computed is computed again; model replies are cached by their exact question,
  so a request already answered replays for free.
- api: a small web API for the page on Render: start a run (jury access code), read its events as they happen,
  read its result, and the recorded reference run for the replay mode.

Keys live only in the Modal secret config.MODAL_KEYS_SECRET, created by the owner (MODEL_API_KEY, BASETEN_API_KEY,
MP_API_KEY, JURY_ACCESS_CODE). No warm container, short limits, one live run at a time, config.LIVE_MAX_RUNS in all.
"""

import modal

from autolab import config

DATA = "/data"
REFERENCE = "/app/reference"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.13.0", extra_index_url="https://download.pytorch.org/whl/cpu")
    .pip_install("pymatgen==2026.10.24", "mp-api==0.47.0", "ase==3.29.0", "openai==3.40.0", "python-dotenv==1.2.4",
                 "alignn==2026.8.11", "jarvis-tools==2026.6.12", "fastapi[standard]")
    .env({"AUTOLAB_CACHE_DIR": f"{DATA}/cache", "SIM_BACKEND": "modal"})
    .add_local_python_source("autolab")
    .add_local_dir("results/2026-10-29_reference_run", REFERENCE, ignore=["replay/**", "console*.log"])
)
data = modal.Volume.from_name(config.MODAL_DATA_VOLUME, create_if_missing=True)
keys = modal.Secret.from_name(config.MODAL_KEYS_SECRET)
store = modal.Dict.from_name(config.MODAL_LIVE_STORE, create_if_missing=True)

app = modal.App(config.MODAL_AGENT_APP, image=image)


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
def run_agent(run_id: str, goal: str) -> dict:
    import json
    import os

    from autolab.agent.events import EventLog
    from autolab.agent.live import StoreSink, run_live
    from autolab.agent.loop import Agent
    from autolab.agent.runs import analyst_client, client, load_prior
    from autolab.sim.backend import RelaxBudget

    _alignn_models()
    prior = load_prior(f"{REFERENCE}/result.json", "ref")
    folder = f"{DATA}/runs/{run_id}"
    os.makedirs(folder, exist_ok=True)

    def make_agent(events: EventLog) -> Agent:
        sink = events.sink
        events = EventLog(f"{folder}/events.jsonl", sink=sink)  # also kept in the volume
        brain = client(config.LLM_PROVIDER, config.LLM_COST_CAPS_USD[config.LLM_PROVIDER])
        fallback = client(config.LLM_FALLBACK_PROVIDER, config.LLM_COST_CAPS_USD[config.LLM_FALLBACK_PROVIDER])
        return Agent(brain or fallback, fallback if brain else None, events=events,
                     budget=RelaxBudget(config.LIVE_MAX_RELAXATIONS),
                     analyst=analyst_client(config.CANDIDATE_ANALYSIS_PROVIDER),
                     novelty_client=client(config.NOVELTY_PROVIDER, config.NOVELTY_COST_CAP_USD))

    try:
        result = run_live(run_id, goal, store, make_agent, prior)
        with open(f"{folder}/result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, default=str)
        return {"run_id": run_id, "final_ranking": result.get("final_ranking"), "usage": result.get("usage")}
    finally:
        data.commit()  # new cache entries and the run files stay for the next runs


@app.function(secrets=[keys], volumes={DATA: data}, timeout=60, max_containers=2, scaledown_window=60)
@modal.asgi_app()
def api():
    import json
    import os
    import uuid

    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    from autolab.agent.live import LiveRefused, check_request, events_after, reserve

    web = FastAPI(title="AutoLab agent")
    web.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])

    class Request(BaseModel):
        goal: str
        access_code: str

    @web.get("/api/health")
    def health():
        lock = store.get("lock")
        return {"ok": True, "busy": bool(lock), "live_runs_used": store.get("live_runs", 0),
                "live_runs_allowed": config.LIVE_MAX_RUNS}

    @web.post("/api/runs")
    def start(req: Request):
        try:
            check_request(req.goal, req.access_code, os.environ.get("JURY_ACCESS_CODE"), store)
        except LiveRefused as e:
            raise HTTPException(status_code=403, detail=str(e))
        run_id = uuid.uuid4().hex[:12]
        reserve(store, run_id, req.goal.strip())
        try:
            run_agent.spawn(run_id, req.goal.strip())
        except Exception as e:  # quota or payment: reported, the lock released, no retry
            store["lock"] = None
            store[f"{run_id}/status"] = {"state": "error", "goal": req.goal, "error": f"{type(e).__name__}: {e}"[:300]}
            raise HTTPException(status_code=503, detail="the run could not start")
        return {"run_id": run_id}

    @web.get("/api/runs/{run_id}/events")
    def events(run_id: str, after: int = 0):
        return events_after(store, run_id, after)

    @web.get("/api/runs/{run_id}/result")
    def result(run_id: str):
        res = store.get(f"{run_id}/result")
        if res is None:
            raise HTTPException(status_code=404, detail="no result yet")
        return res

    @web.get("/api/reference/{name}")
    def reference(name: str):
        """The recorded reference run (replay mode): result.json, report.md or events.jsonl."""
        if name not in ("result.json", "report.md", "events.jsonl"):
            raise HTTPException(status_code=404, detail="unknown file")
        with open(f"{REFERENCE}/{name}", encoding="utf-8") as f:
            text = f.read()
        if name == "result.json":
            return json.loads(text)
        if name == "events.jsonl":
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        return {"markdown": text}

    return web
