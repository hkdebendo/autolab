# Progress

Spending to date (2026-10-29, before step 1): Modal ~6.8 $ (calibration 3.26 $ billed, 600 K screening of 5 candidates ~3.5 $); Meta ~0.1 $.

Step 1 run launched 2026-10-29 ~07:20: 1 iteration, 3 candidates, --novelty, prior = 9 step-9 candidates. Estimate: Meta ~0.2 $ (cap 1 $ + novelty cap 1 $); Modal relaxations 0.3-0.6 $, MD up to ~2.6 $ (stage cap 5 $): may exceed 3 $ in one run (announced here).

**Step 1 done (2026-10-29)** — real run results/2026-10-29_step1_run: Muse Spark proposed 3 new candidates (Li11P4S15Br, Li6P2SeS7, Li7P3S10O), all passed the funnel; with the 9 step-9 candidates: 2 Na excluded (non-passivating), Li13P6S21Cl excluded (framework: Cl at 40 % of Li), all MD verdicts "tied". Finalists: Li6P2SeS7 (E_hull -0.007, D/D(parent) 0.66 ± 0.21), Li7P3SeS10, Li11P4S15I; novelty: LGPS control "published", the 3 finalists "close family already studied".
Fixed on the way: novelty parser (control was misread), unrelated search results as sources, cached MD applied to all eligible candidates, console encoding; stages rerun from cache (scripts/rerun_stages.py).
Cost: Meta 0.27 $ (3 brain calls 0.06 $, novelty 0.21 $); Modal ~1.2 $ (55 relaxations T4, 2 MD runs A10G). Totals: Modal ~7.5 $ / 15 $, Meta ~0.4 $ / 20 $.
Next: step 2, validation benchmark (4 good, 8 bad known compounds, blind).

**Step 2 done (2026-10-29)** — blind benchmark results/2026-10-29_benchmark: good electrolytes passing the funnel 3/4 (2/4 with the Li-metal check), bad compounds rejected 8/8.
Failures: Li6PS5Cl at the hull (0.080 eV/atom, ordered cell; MP 0.083), LGPS non-passivating (Li15Ge4, its known real weakness). Caveat: 6 of the 8 bad ones are stopped by the gap alone.
Cost: 40 new relaxations on Modal T4 (~0.3 $); no LLM call. Totals: Modal ~7.8 $ / 15 $, Meta ~0.4 $ / 20 $.
Next: step 3, reference run (2-3 iterations, 5 candidates).

Step 3 reference run launched 07:55: 2 iterations x 5 candidates, prior 13. Estimate: Modal ~1.2 $ relaxations + up to ~2.7 $ MD (stage cap 5 $) = may exceed 3 $ in one run (announced here); Meta ~0.4 $.
Reference run (first pass) done 08:20: 10 proposals, 9 passed the funnel, 1 not evaluated (relaxation cap 160 reached), 5 Na/Mg candidates excluded (non-passivating); MD choice flaw fixed; stages rerun from the electrodes 08:24, estimate <= 3 $ Modal (3 new candidates x 2 seeds), ~0.2 $ Baseten, ~0.3 $ Meta.

**Step 3 done (2026-10-29)** — reference run results/2026-10-29_reference_run (replay: events.jsonl, result.json, report.md, replay/ with 21 structures and 22 MD runs for the 3D views): 2 iterations, 10 new proposals by Muse Spark, 9 passed the funnel (1 not evaluated: relaxation cap), 5 Na/Mg candidates excluded at Li metal; 16 reviews by Muse Spark Open; MD on 3 new candidates (all tied with their parent); finalists Li6P2SeS7, Li12P4SeS15 (new), Li7P3SeS10, all "close family already studied"; LGPS control "published".
Cost: Meta 0.31 $, Baseten 0.37 $ (26 calls for 16 reviews: malformed JSON retried), Modal ~3.2 $ (155 relaxations T4, 6 MD runs A10G). Totals: Modal ~10.4 $ / 15 $, Meta ~0.7 $ / 20 $, Baseten ~0.4 $ / 10 $.
Next: production backend on Modal (live agents, cache-first), then docs/MUSE_CODE_TASKS.md for the web.

**Production backend (2026-10-29)** — modal_app/agent_app.py (whole loop on Modal CPU, live API with jury access code, one run at a time, LIVE_MAX_RUNS = 6), model reply cache (known request = free replay), whole .cache uploaded to the Modal volume autolab-data (36 MD runs, 623 relaxations). Not deployed yet: waits for the owner's Modal secret `autolab-keys`.
**docs/MUSE_CODE_TASKS.md is ready**: the owner can launch Muse Code on web/ (replay, live mode through Modal, 3D Li diffusion, MSD curves). Claude does not touch web/ meanwhile.
Next: deploy and test the agent app once the secret exists; step 5 (README) meanwhile.
