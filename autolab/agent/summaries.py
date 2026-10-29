"""Plain-language summaries by Muse Glimmer (SPEC 5.11: small fast tasks), written in the background.

Glimmer runs on a dedicated Fireworks deployment that scales to zero: a request to a sleeping deployment gets an
immediate HTTP 503 while it wakes up. The summarizer waits for it (config.GLIMMER_WARMUP_MAX_S at most, polling
every config.GLIMMER_POLL_S), in its own thread, so the loop never waits for a summary. A summary that cannot be
written is reported, never retried beyond that wait.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

from autolab import config

SYSTEM = """You write for the jury of a scientific hackathon, in plain English. AutoLab is an AI agent that searches for new solid electrolytes for lithium-metal batteries: Muse Spark proposes chemical substitutions in known crystals, UMA simulates them, filters keep the stable, insulating ones, and molecular dynamics compares their lithium diffusion with their parent crystal.
Summarize the data you are given in at most 3 short sentences (iteration) or 5 short sentences (whole run): what was tried, what passed or failed and why, what the agent concluded. Readers are not specialists: name compounds by their chemical formula, never by a database id (such as mp-985583: Li3PS4, mp-641703: Li7P3S11); give at most two or three key numbers, rounded (energies to 2 decimals in eV/atom, gaps to 1 decimal in eV), with their units. Use only the numbers given; never invent a value, never claim a material is proven or new to science (the results are computational predictions). No lists, no headings, plain text only."""


def summary_messages(kind: str, data: dict) -> list[dict]:
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Summarize this {kind}.\n{json.dumps(data, default=str)}"}]


class Summarizer:
    """Writes summaries in one background thread and emits an event ("llm", "summary") when each is ready."""

    def __init__(self, client, events, wait_s: float = config.GLIMMER_WARMUP_MAX_S,
                 poll_s: float = config.GLIMMER_POLL_S, sleep: Callable[[float], None] = time.sleep):
        self.client, self.events = client, events
        self.wait_s, self.poll_s, self.sleep = wait_s, poll_s, sleep
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.futures: list[Future] = []

    @property
    def provider(self) -> str:
        return self.client.provider

    def _chat(self, messages: list[dict]):
        from autolab.llm.client import LLMError

        waited = 0.0
        while True:
            try:
                return self.client.chat(messages, max_output_tokens=config.GLIMMER_MAX_OUTPUT_TOKENS,
                                        reasoning_effort=config.GLIMMER_REASONING_EFFORT)
            except LLMError as e:
                if "HTTP 503" not in str(e) or waited >= self.wait_s:  # only a waking deployment is waited for
                    raise
                self.sleep(self.poll_s)
                waited += self.poll_s

    def _write(self, kind: str, label: str, data: dict) -> dict:
        from autolab.llm.client import LLMError

        t0 = time.perf_counter()
        try:
            reply = self._chat(summary_messages(kind, data))
        except LLMError as e:
            out = {"kind": kind, "label": label, "text": None, "error": str(e)[:300]}
        else:
            out = {"kind": kind, "label": label, "text": reply.text.strip() or None, "provider": reply.provider,
                   "cached": reply.cached, "output_tokens": reply.output_tokens}
            if not out["text"]:
                out["error"] = "empty answer (the reasoning used every output token)"
        out["seconds"] = round(time.perf_counter() - t0, 1)
        self.events.emit("llm", "summary", out)
        return out

    def submit(self, kind: str, label: str, data: dict) -> None:
        self.futures.append(self.pool.submit(self._write, kind, label, data))

    def close(self, timeout: float | None = None) -> list[dict]:
        """The summaries written so far, in order (waiting `timeout` s at most for the pending ones)."""
        out, deadline = [], None if timeout is None else time.monotonic() + timeout
        for f in self.futures:
            left = None if deadline is None else max(0.0, deadline - time.monotonic())
            try:
                out.append(f.result(timeout=left))
            except Exception as e:  # still waking or failed: said in the result, never retried
                out.append({"kind": None, "label": None, "text": None, "error": f"{type(e).__name__}: {e}"[:300]})
        self.pool.shutdown(wait=False, cancel_futures=True)
        return out
