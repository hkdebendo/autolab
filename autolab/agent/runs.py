"""What a run needs to start, shared by scripts/run_loop.py and the production app: model clients (with the reply
cache) and the candidates of earlier runs."""

from __future__ import annotations

import json
from pathlib import Path

from autolab import config
from autolab.llm.client import LLMClient, UsageTracker

# Fields written by the stages: earlier candidates come back with their funnel results only, the stages of the new
# run decide again (from the caches).
STAGE_FIELDS = {"window", "passivation", "passivation_reaction_energy", "passivation_products", "metallic_products",
                "interfaces", "interface_reaction_energy", "interface_polysulfides", "electrodes_polysulfides",
                "electrodes_reduced_confidence", "excluded_at", "exclusion_reason", "md_cached", "md_selected",
                "D_cm2_per_s", "D_sem_cm2_per_s", "D_ratio_to_parent", "D_ratio_err", "md_verdict", "conduction",
                "md_framework_intact", "novelty"}  # reviews ("analysis") are kept: not paid twice


def reply_cache():
    from autolab.store.cache import JsonCache

    return JsonCache(config.CACHE_DIR / "llm") if config.LLM_REPLY_CACHE else None


def client(provider: str, cap: float, max_calls: int = config.MAX_LLM_CALLS_PER_RUN) -> LLMClient | None:
    """A model client with its own caps and the reply cache, or None when its key is missing (said, never shown)."""
    if not provider or provider == "none":
        return None
    if not config.has_key(config.LLM_PROVIDERS[provider]["key"]):
        print(f"{config.LLM_PROVIDERS[provider]['key']} missing: provider {provider} disabled")
        return None
    return LLMClient(provider, tracker=UsageTracker(max_calls=max_calls, max_cost_usd=cap), cache=reply_cache())


def analyst_client(provider: str) -> LLMClient | None:
    """Client of the parallel candidate analyses, with room for one call per analysed candidate (and retries)."""
    if not provider or provider == "none":
        return None
    return client(provider, config.LLM_COST_CAPS_USD[provider], config.CANDIDATE_ANALYSIS_MAX * config.JSON_MAX_RETRIES)


def load_prior(path: Path, tag: str) -> list[dict]:
    """Candidates of an earlier run (candidates.json, or result.json with its own earlier candidates), ids prefixed
    with `tag` to stay unique (ids already prefixed by an earlier run are kept); funnel results only."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "candidates" in data:
        cands = data["candidates"]
    else:
        cands = data.get("prior", []) + [c for r in data["iterations"] for c in r["candidates"]]
    out = []
    for c in cands:
        c = {k: v for k, v in c.items() if k not in STAGE_FIELDS}
        out.append(c if ":" in c["id"] else {**c, "id": f"{tag}:{c['id']}"})
    return out
