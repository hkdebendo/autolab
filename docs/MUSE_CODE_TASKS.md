# Tasks for Muse Code: AutoLab web interface

The owner launches Muse Code with this file. **Muse Code works only in `web/` (plus `render.yaml` and
`requirements-web.txt` at the repository root). It never modifies `autolab/`, `modal_app/`, `scripts/`, `tests/`,
`results/` or `docs/`.** Commit messages for this work say "written with Muse Code".

## Goal

A web page, sent to the jury only (not published), that shows the AutoLab agents at work:

1. **Replay mode (default):** the recorded reference run plays as if live: Muse Spark's proposals and reasoning,
   each candidate going through the funnel with its numbers, Muse Spark Open's reviews, the choice of the molecular
   dynamics candidates, 3D animations of lithium diffusion, the final ranking and the novelty check with sources.
2. **Live mode (jury, access code):** the jury types a request in natural language; the agents run for real on
   Modal and the page shows their events as they happen. A request already answered replays from the caches at no
   cost; a new one triggers real work (Muse Spark, Muse Spark Open, UMA on GPUs, ...).

Render (free tier) only serves the page and relays the live calls: no heavy computation, no model key there.

## Data

### Replay (files in the repository, read-only)

`results/2026-10-29_reference_run/` (path in `web/config.json`, key `reference_run`):

- `events.jsonl`: one JSON object per line, in time order:
  `{"type": str, "candidate_id": str | null, "step": str, "data": {...}, "timestamp": "ISO 8601 UTC"}`.
- `result.json`: the whole run (iterations, candidates with every number, stages, final ranking, usage).
- `report.md`: the Markdown report.
- `replay/index.json`: `{"structures": [{"id", "formula", "file"}], "md": [{"id", "formula", "kind", "seed",
  "verdict", "file"}]}` (files relative to `replay/`).
- `replay/structures/<id>.json`: `{"id", "formula", "parent", "e_hull", "cell": 3x3 (A), "symbols": [...],
  "positions": [[x, y, z], ...] (A), "highlight": the substituted element or null}`.
- `replay/md/<id>_seed<k>.json`: one molecular dynamics run: `{"id", "formula", "kind" (candidate / parent),
  "parent", "seed", "cell": 3x3 supercell (A), "species": "Li", "framework": {"symbols", "positions"}` (static,
  drawn once), `"frames": [frame][Li][x, y, z]` (Li positions inside the cell, one frame every `frame_fs`
  femtoseconds, 400 frames over 40 ps), `"curve": {"t_ps", "msd_li_A2", "msd_framework_A2": {element: [...]}}`
  (mean squared displacement against time: Li climbs, the framework stays flat when it is intact),
  `"D_cm2_per_s", "D_sem_cm2_per_s", "ratio", "ratio_err", "verdict"` (tied / higher / lower, against the parent),
  `"conduction", "conduction_reason", "temperature_K"}`.

### Event types and steps (fields worth showing in **bold**)

| type | step | meaning | data |
|---|---|---|---|
| loop | start | run starts | **goal**, domain, **parents** (id, formula, nsites), prior (ids of earlier candidates), settings |
| loop | iteration | new iteration | **iteration** |
| llm | proposal | Muse Spark proposed substitutions | **reply.hypothesis**, **reply.proposals[]** (parent, substitution {remove, add, count, li_vacancies}, rationale), **reasoning_summary**, provider, tokens, cost_usd, seconds, cached |
| llm | analysis | Muse Spark read the results | **reply.lessons[]**, **reply.next_direction**, reply.ranking, reply.stop, reasoning_summary |
| llm | md_selection | Muse Spark chose the molecular dynamics candidates | **reply.selected[]**, **reply.rationale**, reasoning_summary |
| llm | error / budget | model failure or budget reached | provider, error |
| candidate | generate | structure built | **formula**, accepted, charge, arrangements, reason |
| candidate | known_check | already in Materials Project? | known[] |
| candidate | relax | UMA relaxation | arrangements, converged, spread_meV |
| candidate | hull | stability | **e_hull** (eV/atom), **e_hull_per_substitution**, decomposition[] |
| candidate | bandgap | electronic gap | **gap_optb88**, gap_mbj (eV), passes |
| candidate | ss_check | S-S bonds | ss_bonds |
| candidate | done | end of the funnel | **status** (passed / rejected / error / budget), rejected_at, reason |
| stage | `<name>` | a stage starts or ends | status (start / done / stopped / error) and a summary |
| stage | electrodes:calibration | Li3PS4 vs cathode check | cathode, uma, mp, diff, ok |
| candidate | electrodes:done | electrodes of one candidate | **window** (v_low, v_high), **passivation**, interface_reaction_energy, reduced_confidence, excluded |
| candidate | candidate_analyses:done | Muse Spark Open's review | **strengths[]**, **risks[]**, **md_priority**, **summary** |
| stage | molecular_dynamics:plan | MD runs to compute | runs, total_runs, usd, wall_s |
| candidate | molecular_dynamics:done | Li diffusion of one candidate | **D_cm2_per_s**, **ratio** (to its parent), **verdict**, conduction |
| loop | stop | run ends | reason, **final_ranking** |

Stages in order: `electrodes`, `candidate_analyses`, `md_selection`, `molecular_dynamics`, `ranking`, `novelty`.
The final ranking (`result.json` → `stages.ranking`: ranking, finalists, excluded with reasons) and the novelty check
(`stages.novelty`: control and candidates, each with level, label, summary, sources[] {title, url}) are read from
`result.json` (replay) or from the live result when these stage events arrive.

### Live API (Modal, already deployed by Claude; URL in the Render variable `AUTOLAB_API_URL`)

- `GET /api/health` → `{"ok", "busy", "live_runs_used", "live_runs_allowed"}`.
- `POST /api/runs` with `{"goal": str, "access_code": str}` → `{"run_id"}`, or 403 with a reason (wrong code, a run
  already going, cap reached), or 503.
- `GET /api/runs/{run_id}/events?after=n` → `{"events": [...new events...], "next": int, "status": {"state":
  starting / running / done / error, "goal", "error"?}}`. Poll every 2 s with `after = next`.
- `GET /api/runs/{run_id}/result` → the result (same shape as `result.json`), 404 until done.

## What to build

1. `web/app.py` — FastAPI:
   - `GET /` serves `web/static/index.html` (plain HTML + CSS + JavaScript, no build step).
   - `GET /api/replay/...` serves the files of the reference run listed above.
   - `GET /api/live/health`, `POST /api/live/runs`, `GET /api/live/runs/{id}/events`, `GET /api/live/runs/{id}/result`
     relay to `AUTOLAB_API_URL` (the browser never sees the Modal URL). If `AUTOLAB_LIVE` is not `1` or the URL is
     missing, they answer 403 "live mode disabled".
2. The page:
   - Header: AutoLab, the goal, a mode switch (Replay / Live), a speed selector for the replay (1x, 10x, 50x).
   - **Replay:** events shown one after the other, with the original time gaps divided by the speed (each gap at least
     0.4 s, at most 3 s, so that cached steps stay readable).
   - **Live:** a text box for the request (natural language, at most 500 characters) and an access code field; then
     the same timeline fed by the live events (shown at least 0.4 s apart); a clear message for each refusal.
   - **Timeline (left):** one card per event: proposals with their rationale and the hypothesis, reasoning folded by
     default, each funnel step with its number and a green/red mark, reviews, stage results. A small funnel diagram
     at the top lights up the current step (proposal → Materials Project → relaxation → stability → band gap →
     electrodes → reviews → MD choice → molecular dynamics → ranking → novelty).
   - **Candidates (right):** a table updated live (formula, E_hull, gap, window, passivation, D/D(parent), status);
     clicking a candidate opens its 3D structure (substituted element highlighted).
   - **Molecular dynamics viewer:** for a structure of the MD stage, the Li ions moving inside the static framework
     (play / pause, frame slider, optional short trails), the candidate next to its parent, and the MSD curve below
     (Li rising, framework flat), with D ± error, D/D(parent) and the verdict. Use 3Dmol.js or NGL from a CDN.
   - **End:** the final ranking with the finalists highlighted, the excluded candidates with their reason, the novelty
     check with its sources as links, the costs of the run (`usage`), and the sentence "Candidates are computational
     predictions, not proven materials."
   - Readable on a phone (one column under 700 px). No tracker, no analytics.
3. Deployment on Render: `render.yaml` (one free web service, `uvicorn web.app:app`), `requirements-web.txt`
   (fastapi, uvicorn, httpx, markdown). Environment variables set by the owner in Render: `AUTOLAB_API_URL`,
   `AUTOLAB_LIVE=1`. No model key, no `.env`.
4. Tests in `web/tests/` (pytest, no network): replay keeps the order of `events.jsonl`; the live routes answer 403
   when `AUTOLAB_LIVE` is not set; `GET /api/replay/result.json` returns the goal; the relay passes the request body
   and the status code through (with a fake HTTP client).

## Constraints

- No API key anywhere in `web/`. The access code is typed by the jury and passed through; it is checked on Modal.
- Do not write "cobalt-free electrolytes": the product searches "solid electrolytes for lithium-metal batteries"
  (cobalt-free concerns cathodes only).
- Keep it small and readable: a few hundred lines of Python and JavaScript.
