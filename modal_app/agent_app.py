"""AutoLab service on Modal (production): the conversations API used by the web page, and the researches.

Deploy:   modal deploy modal_app/agent_app.py      (after modal_app/uma_app.py)

- api: the web API of the interface (conversations, messages, progress, stop, rename, delete, 3D files), over the
  Supabase PostgreSQL database (DATABASE_URL); scope checks and follow-up answers by the language models.
- run_research: one research on CPU (orchestration, Materials Project, pymatgen); UMA relaxations and MD go
  to the GPU functions of autolab-uma, the champion's DFT band gap to autolab-dft (CPU). It reads and writes the caches of the autolab-data volume (the whole .cache of
  the development PC), so nothing already computed is computed again; its events go to the database as they happen.

Keys live only in the Modal secret config.MODAL_KEYS_SECRET, created by the owner (MODEL_API_KEY, BASETEN_API_KEY,
MP_API_KEY, FIREWORKS_API_KEY, GLIMMER_DEPLOYMENT, DATABASE_URL). No access code (owner, 2026-10-29): one research at
a time and config.LIVE_MAX_RUNS new researches in all protect the budget. No warm container, short limits.
"""

import json
import os

import modal

from autolab import config

DATA = "/data"
REFERENCE = "/app/reference"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("pymatgen==2026.10.24", "mp-api==0.47.0", "ase==3.29.0", "openai==3.40.0", "python-dotenv==1.2.4",
                 "fastapi[standard]", "psycopg[binary]==3.2.12")  # only Meta models at run time
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

    class Production(Service):
        def reuse(self, cid: str, src: dict, scope: dict) -> None:
            """A known request: its recorded research is replayed in hybrid mode by replay_research (agent/hybrid.py),
            the agents working live on the recorded computations; copied as it was if that cannot start."""
            for a in self.store.artifacts(src["id"]):  # the 3D files of the recorded research
                self.store.add_artifact(cid, a["name"], a["kind"], a["path"], a.get("meta"))
            self.store.update(cid, status="running")
            try:
                replay_research.spawn(cid, src["id"])
            except Exception:  # quota or payment: said in the log, the recorded research is shown as it was
                super().reuse(cid, src, scope)

    return Production(PostgresStore(), models, lambda cid: run_research.spawn(cid))


CHAMPIONS_FILE = f"{DATA}/cache/champions.json"  # the results page, computed once for every container


def _forget_champions() -> None:
    if os.path.exists(CHAMPIONS_FILE):
        os.remove(CHAMPIONS_FILE)
        data.commit()


# nonpreemptible: a preempted research container lost its unsaved results and left the research stuck (2026-11-01)
@app.function(cpu=2.0, memory=6144, volumes={DATA: data}, secrets=[keys], timeout=config.LIVE_RUN_TIMEOUT_S,
              max_containers=1, nonpreemptible=True)
def run_research(cid: str) -> dict | None:
    from autolab.agent.events import EventLog
    from autolab.agent.loop import Agent
    from autolab.agent.runs import analyst_client, client, director_client, load_prior, summarizer
    from autolab.analysis.replay_export import export_run
    from autolab.sim.backend import RelaxBudget

    svc = _service()

    def make_agent(events: EventLog, should_stop) -> Agent:
        brain = client(config.LLM_PROVIDER, config.LLM_COST_CAPS_USD[config.LLM_PROVIDER])
        fallback = client(config.LLM_FALLBACK_PROVIDER, config.LLM_COST_CAPS_USD[config.LLM_FALLBACK_PROVIDER])
        return Agent(brain or fallback, fallback if brain else None, events=events,
                     budget=RelaxBudget(config.LIVE_MAX_RELAXATIONS),
                     analyst=analyst_client(config.CANDIDATE_ANALYSIS_PROVIDER),
                     novelty_client=client(config.NOVELTY_PROVIDER, config.NOVELTY_COST_CAP_USD),
                     summarizer=summarizer(events), director=director_client(), should_stop=should_stop)

    def export(cid_: str, result: dict) -> None:
        index = export_run(result, f"{DATA}/runs/{cid_}")
        svc.store.add_artifact(cid_, "index.json", "index", f"runs/{cid_}/index.json")
        for kind in ("structures", "md"):
            for e in index[kind]:
                svc.store.add_artifact(cid_, e["file"], kind.rstrip("s"), f"runs/{cid_}/{e['file']}", e)

    try:
        result = svc.run(cid, make_agent, prior=load_prior(f"{REFERENCE}/result.json", "ref"), export=export,
                         checkpoint=data.commit)  # caches saved after each step, not only at the end
        return {"conversation": cid, "final_ranking": (result or {}).get("final_ranking")}
    finally:
        _forget_champions()  # a new champion may have appeared
        data.commit()  # new cache entries and the 3D files stay for the next researches


@app.function(cpu=1.0, memory=2048, secrets=[keys], timeout=1200, max_containers=2, nonpreemptible=True)
def replay_research(cid: str, src: str) -> None:
    """Hybrid replay of the recorded research `src` into conversation `cid` (agent/hybrid.py): proposals and
    computations recorded, analyses, reviews, summaries (Muse Spark) and campaign review (Muse Wonder) live. No GPU."""
    from autolab.agent import hybrid

    svc = _service()
    m = hybrid.models(glimmer=False)  # a sleeping Muse Glimmer deployment is billed by GPU time: not woken up
    try:
        if m is None:  # no model key: the recorded research as it was
            from autolab.agent.service import Service

            Service.reuse(svc, cid, svc.store.get(src), {})
            return
        hybrid.replay(svc.store, cid, src, m, svc.finish)
    except Exception as e:  # reported in the conversation, never retried
        svc.store.update(cid, status="error", error=f"{type(e).__name__}: {e}"[:500])
        svc.store.add_message(cid, "assistant", "notice", "The replay stopped on an error; the steps already shown "
                              "are kept above.")


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

    @web.get("/api/champions")
    def champions(refresh: bool = False):
        """The results page, kept in the volume for every container (reading the reports takes seconds): computed
        again when a research ends or is deleted, or with ?refresh=1."""
        data.reload()
        if os.path.exists(CHAMPIONS_FILE) and not refresh:
            with open(CHAMPIONS_FILE, encoding="utf-8") as f:
                return json.load(f)
        out = svc.champions()
        os.makedirs(os.path.dirname(CHAMPIONS_FILE), exist_ok=True)
        with open(CHAMPIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(out, f, default=str)
        data.commit()
        return out

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
        _forget_champions()
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
