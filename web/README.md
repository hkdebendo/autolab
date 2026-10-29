# AutoLab web interface (jury page)

Shows the AutoLab agents at work. Two modes:

- **Replay (default):** the recorded reference run (`results/2026-10-29_reference_run`,
  path in `web/config.json`) plays as if live — proposals, funnel steps with numbers,
  reviews, MD choice, Li-diffusion 3D animations, final ranking, novelty check.
- **Live (jury, access code):** the jury types a request; this server relays it to the
  Modal agent API and shows the events as they arrive. No model key here, no heavy
  computation here.

## Run locally (replay)

```bash
# from the repository root
python -m pip install -r requirements-web.txt
uvicorn web.app:app --port 8000
```

Then open http://127.0.0.1:8000 in a browser. The 3D viewers need network access
to the 3Dmol.js CDN; everything else works offline.

## Run locally (live)

```bash
AUTOLAB_LIVE=1 AUTOLAB_API_URL=https://<modal-agent-api> uvicorn web.app:app --port 8000
```

Without both variables the `/api/live/*` routes answer 403 "live mode disabled".

## Tests

```bash
python -m pytest web/tests -q
```

No network: replay order, 403-when-disabled, goal passthrough, relay passthrough
with a fake HTTP client.

## Deploy (Render, free tier)

`render.yaml` defines one web service (`uvicorn web.app:app`, `requirements-web.txt`).
The owner sets `AUTOLAB_API_URL` and `AUTOLAB_LIVE=1` in the Render dashboard.

## Files

- `web/app.py` — FastAPI: `/` + `/static/*`, `/api/replay/...` (reference-run files),
  `/api/live/...` (relay to Modal).
- `web/static/` — plain HTML + CSS + JavaScript, no build step.
- `web/tests/` — pytest suite (see above).
