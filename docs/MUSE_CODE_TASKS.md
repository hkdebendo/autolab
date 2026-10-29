# Tasks for Muse Code: AutoLab web interface (replay mode)

Owner launches Muse Code with this file. **Muse Code works only in `web/` (and `render.yaml`, `requirements-web.txt`
at the repository root). It never modifies `autolab/`, `scripts/`, `tests/`, `results/` or `docs/` (except
adding its own notes in `web/README.md`).** Commit messages for this work mention "written with Muse Code".

## Goal

A small public web page that shows the AutoLab agent at work by **replaying a recorded run**: the events of the
reference run are displayed one after the other, as if live: Muse Spark's proposals and reasoning, each candidate
going through the funnel with its numbers, the stages after the iterations (electrodes, choice of candidates for
molecular dynamics, Li diffusion, final ranking, novelty check). No GPU, no API key and no paid call are needed to
run it.

## Data to replay (read-only)

The reference run is a folder `results/<date>_reference_run/` (path given in `web/config.json`, key
`reference_run`; until it exists, use `results/2026-10-29_step1_run/`). It contains:

- `events.jsonl`: one JSON object per line, in time order:
  `{"type": str, "candidate_id": str | null, "step": str, "data": {...}, "timestamp": "ISO 8601 UTC"}`.
- `result.json`: the whole run (iterations, candidates with every number, stages, final ranking, usage).
- `report.md`: the Markdown report.

Event types and steps (data fields worth showing in **bold**):

| type | step | meaning | data |
|---|---|---|---|
| loop | start | run starts | **goal**, domain, **parents** (id, formula, nsites), prior (ids of earlier candidates), settings, thresholds |
| loop | iteration | new iteration | **iteration** |
| llm | proposal | Muse Spark proposed substitutions | **reply.hypothesis**, **reply.proposals[]** (parent, substitution {remove, add, count, li_vacancies}, rationale), **reasoning_summary**, provider, input/output tokens, cost_usd, seconds |
| llm | analysis | Muse Spark read the results | **reply.lessons[]**, **reply.next_direction**, reply.ranking, reply.stop, reasoning_summary |
| llm | md_selection | Muse Spark chose candidates for molecular dynamics | **reply.selected[]**, **reply.rationale**, reasoning_summary |
| llm | error / budget | model failure or budget reached | provider, error |
| candidate | generate | structure built | **formula**, accepted, charge, arrangements, reason |
| candidate | known_check | already in Materials Project? | known[] |
| candidate | relax | UMA relaxation | arrangements, converged, spread_meV |
| candidate | hull | stability | **e_hull** (eV/atom), **e_hull_per_substitution**, decomposition[] (formula, fraction) |
| candidate | bandgap | electronic gap | **gap_optb88**, gap_mbj (eV), passes |
| candidate | ss_check | S-S bonds | ss_bonds |
| candidate | done | end of the funnel | **status** (passed / rejected / error / budget), rejected_at, reason |
| stage | `<name>` | a stage starts or ends | status (start / done / stopped / error) and a summary |
| stage | electrodes:calibration | Li3PS4 vs cathode check | cathode, uma, mp, diff, ok |
| candidate | electrodes:done | electrodes of one candidate | **window** (v_low, v_high), **passivation**, interface_reaction_energy, reduced_confidence, excluded |
| stage | molecular_dynamics:plan | MD runs to compute | runs, total_runs, usd, wall_s |
| candidate | molecular_dynamics:done | Li diffusion of one candidate | **D_cm2_per_s**, **ratio** (to its parent), **verdict** (tied / higher / lower), conduction |
| loop | stop | run ends | reason, **final_ranking** |

Stage names, in order: `electrodes`, `md_selection`, `molecular_dynamics`, `ranking`, `novelty`. The final
ranking (`result.json` → `stages.ranking`: ranking, finalists, excluded with reasons) and the novelty check
(`stages.novelty`: control and candidates, each with level, label, summary, sources[] {title, url}) are read from
`result.json` when the `ranking` and `novelty` stage events arrive.

## What to build

1. `web/app.py` — FastAPI:
   - `GET /` serves the page (`web/static/index.html`, plain HTML + CSS + a small JavaScript file, no build step).
   - `GET /api/run` returns `result.json` of the reference run (goal, parents, settings, usage).
   - `GET /api/events` returns the events list; `GET /api/replay?speed=10` streams them with Server-Sent Events,
     keeping the original order and spacing the original time gaps divided by `speed` (each gap capped at 3 s).
   - `GET /api/report` returns `report.md` (rendered as HTML on the page, with a "full report" link).
   - Live mode (`POST /api/live`) exists but is **disabled by default**: it answers 403 unless the environment
     variable `AUTOLAB_LIVE=1` is set; it never runs on Render. Do not implement the live run itself: leave a
     clear TODO that calls `scripts/run_loop.py`.
2. The page:
   - Header: AutoLab, one-line goal, a "Replay" button and a speed selector (1x, 10x, 50x).
   - Left column, timeline: one card per event as it arrives (proposals with their rationale and the hypothesis,
     reasoning summary folded by default, each funnel step with its number and a green/red mark, stage results).
   - Right column: candidate table updated live (formula, E_hull, gap, window, passivation, D/D(parent), status)
     and, at the end, the final ranking with the finalists highlighted, the excluded candidates with their reason,
     and the novelty check with its sources as links.
   - Footer: costs of the run (usage in `result.json`) and the sentence "Candidates are computational
     predictions, not proven materials."
   - Readable on a phone (one column under 700 px). No external tracker, no analytics.
3. Deployment on Render: `render.yaml` (one free web service, `uvicorn web.app:app`), `requirements-web.txt`
   (fastapi, uvicorn, markdown). The service only reads files from the repository: no secret, no `.env`.
4. Tests in `web/tests/` (pytest, no network): the replay keeps the order of `events.jsonl`; `/api/live` answers
   403 by default; `/api/run` returns the goal.

## Constraints

- No API key anywhere; nothing in `autolab/` is imported except, optionally, nothing at all (read the JSON files).
- Do not write "cobalt-free electrolytes": the product searches "solid electrolytes for lithium-metal batteries".
- Keep it small: a few hundred lines in total.
