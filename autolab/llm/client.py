"""OpenAI-compatible client for the language-model providers (SPEC 5.11).

The provider (meta, baseten, fireworks) comes from LLM_PROVIDER or the caller.
Every call is counted (tokens, estimated cost) in a UsageTracker that stops
the run before a limit is exceeded. No automatic retry: quota, payment and
rate-limit errors stop immediately; only a malformed JSON reply is asked
again, at most JSON_MAX_RETRIES times.
"""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Callable

import openai

from autolab import config
from autolab.llm.schemas import SchemaError, parse_reply

log = logging.getLogger(__name__)

Callback = Callable[[str], None] | None


class LLMError(RuntimeError):
    """A provider call failed."""


class QuotaError(LLMError):
    """Authentication, payment, quota or rate limit: stop and report, never retry."""


class BudgetExceeded(LLMError):
    """The run reached its call, token or cost limit."""


class JSONReplyError(LLMError):
    """No valid JSON reply after the allowed attempts."""


@dataclass
class Reply:
    provider: str
    model: str
    text: str
    reasoning: str
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int | None
    cost_usd: float
    seconds: float
    usage_estimated: bool = False


def cost_usd(provider: str, input_tokens: int, output_tokens: int) -> float:
    """Estimated cost from the prices in config.LLM_PROVIDERS."""
    p = config.LLM_PROVIDERS[provider]
    return (input_tokens * p["usd_per_m_input"] + output_tokens * p["usd_per_m_output"]) / 1e6


@dataclass
class UsageTracker:
    """Cumulative LLM usage of one run, with hard limits checked before each call."""

    max_calls: int = config.MAX_LLM_CALLS_PER_RUN
    max_tokens: int = config.MAX_TOKENS_PER_RUN
    max_cost_usd: float = config.MAX_LLM_COST_PER_RUN_USD
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    by_provider: dict = field(default_factory=dict)

    def check(self) -> None:
        if self.calls >= self.max_calls:
            raise BudgetExceeded(f"{self.calls} LLM calls made, limit is {self.max_calls} (MAX_LLM_CALLS_PER_RUN)")
        if self.input_tokens + self.output_tokens >= self.max_tokens:
            raise BudgetExceeded(f"{self.input_tokens + self.output_tokens} tokens used, limit is {self.max_tokens}")
        if self.cost_usd >= self.max_cost_usd:
            raise BudgetExceeded(f"${self.cost_usd:.4f} spent, limit is ${self.max_cost_usd}")

    def count_call(self, provider: str) -> None:
        self.calls += 1
        self.by_provider.setdefault(provider, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
        self.by_provider[provider]["calls"] += 1

    def add(self, reply: Reply) -> None:
        self.input_tokens += reply.input_tokens
        self.output_tokens += reply.output_tokens
        self.cost_usd += reply.cost_usd
        p = self.by_provider[reply.provider]
        p["input_tokens"] += reply.input_tokens
        p["output_tokens"] += reply.output_tokens
        p["cost_usd"] += reply.cost_usd

    def summary(self) -> dict:
        out = {k: v for k, v in asdict(self).items() if not k.startswith("max_")}
        out["cost_usd"] = round(self.cost_usd, 5)
        for p in out["by_provider"].values():
            p["cost_usd"] = round(p["cost_usd"], 5)
        return out


TRACKER = UsageTracker()  # default tracker of the current run


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _split_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    return system or None, [m for m in messages if m["role"] != "system"]


class LLMClient:
    """One provider behind the OpenAI SDK; `client` can be injected (tests)."""

    def __init__(self, provider: str | None = None, tracker: UsageTracker | None = None, client=None):
        self.provider = provider or config.LLM_PROVIDER
        if self.provider not in config.LLM_PROVIDERS:
            raise ValueError(f"unknown LLM provider {self.provider!r} (expected one of {list(config.LLM_PROVIDERS)})")
        self.spec = config.LLM_PROVIDERS[self.provider]
        self.model = self.spec["model"]
        self.tracker = tracker or TRACKER
        self.client = client or openai.OpenAI(
            base_url=self.spec["base_url"],
            api_key=config.require_key(self.spec["key"]),
            max_retries=0,  # no silent retries (CLAUDE.md)
            timeout=config.LLM_TIMEOUT,
        )

    # --- one call ----------------------------------------------------------

    def chat(
        self,
        messages: list[dict],
        stream: bool = False,
        on_text: Callback = None,
        on_reasoning: Callback = None,
        reasoning_effort: str | None = None,
        max_output_tokens: int = config.LLM_MAX_OUTPUT_TOKENS,
    ) -> Reply:
        """Send messages, return text, reasoning and usage. Streams through the callbacks."""
        self.tracker.check()
        self.tracker.count_call(self.provider)
        t0 = time.perf_counter()
        call = self._responses if self.spec["api"] == "responses" else self._chat_completions
        try:
            text, reasoning, usage = call(messages, stream, on_text, on_reasoning, reasoning_effort, max_output_tokens)
        except (openai.RateLimitError, openai.AuthenticationError, openai.PermissionDeniedError) as e:
            raise QuotaError(f"{self.provider}: {type(e).__name__} (HTTP {e.status_code}): stopping, no retry") from e
        except openai.APIStatusError as e:
            if e.status_code == 402:
                raise QuotaError(f"{self.provider}: payment required (HTTP 402): stopping, no retry") from e
            raise LLMError(f"{self.provider}: HTTP {e.status_code}: {e.message}") from e
        except openai.APIError as e:
            raise LLMError(f"{self.provider}: {type(e).__name__}: {e}") from e

        estimated = usage is None
        if estimated:
            prompt = " ".join(str(m["content"]) for m in messages)
            usage = (_estimate_tokens(prompt), _estimate_tokens(text + reasoning), None)
        n_in, n_out, n_reason = usage
        reply = Reply(self.provider, self.model, text, reasoning, n_in, n_out, n_reason,
                      cost_usd(self.provider, n_in, n_out), round(time.perf_counter() - t0, 2), estimated)
        self.tracker.add(reply)
        log.info("llm %s: in %d, out %d (reasoning %s), $%.5f, %.1f s%s", self.provider, n_in, n_out, n_reason,
                 reply.cost_usd, reply.seconds, " (usage estimated)" if estimated else "")
        return reply

    def _chat_completions(self, messages, stream, on_text, on_reasoning, effort, max_tokens):
        kwargs = {"model": self.model, "messages": messages, "max_tokens": max_tokens}
        if effort:
            kwargs["reasoning_effort"] = effort
        if not stream:
            resp = self.client.chat.completions.create(**kwargs)
            msg = resp.choices[0].message
            reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None) or ""
            return msg.content or "", reasoning, self._chat_usage(resp.usage)

        text, reasoning, usage = [], [], None
        for chunk in self.client.chat.completions.create(**kwargs, stream=True, stream_options={"include_usage": True}):
            if getattr(chunk, "usage", None):
                usage = self._chat_usage(chunk.usage)
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            r = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
            if r:
                reasoning.append(r)
                on_reasoning and on_reasoning(r)
            if delta.content:
                text.append(delta.content)
                on_text and on_text(delta.content)
        return "".join(text), "".join(reasoning), usage

    @staticmethod
    def _chat_usage(u):
        if u is None:
            return None
        details = getattr(u, "completion_tokens_details", None)
        return u.prompt_tokens, u.completion_tokens, getattr(details, "reasoning_tokens", None)

    def _responses(self, messages, stream, on_text, on_reasoning, effort, max_tokens):
        """Meta Responses API: the only way to see a reasoning summary with an external key."""
        instructions, rest = _split_system(messages)
        reasoning_opts = {"summary": "auto"}
        if effort:
            reasoning_opts["effort"] = effort
        kwargs = {"model": self.model, "input": rest, "reasoning": reasoning_opts, "max_output_tokens": max_tokens}
        if instructions:
            kwargs["instructions"] = instructions
        if not stream:
            resp = self.client.responses.create(**kwargs)
            return resp.output_text or "", self._summary(resp), self._responses_usage(resp.usage)

        text, reasoning, final = [], [], None
        for event in self.client.responses.create(**kwargs, stream=True):
            kind = getattr(event, "type", "")
            if kind == "response.reasoning_summary_text.delta":
                reasoning.append(event.delta)
                on_reasoning and on_reasoning(event.delta)
            elif kind == "response.output_text.delta":
                text.append(event.delta)
                on_text and on_text(event.delta)
            elif kind == "response.completed":
                final = event.response
            elif kind in ("response.failed", "error"):
                raise LLMError(f"{self.provider}: stream failed ({kind})")
        if final is not None and not text:
            text = [final.output_text or ""]
        return "".join(text), "".join(reasoning), self._responses_usage(getattr(final, "usage", None))

    @staticmethod
    def _summary(resp) -> str:
        parts = []
        for item in resp.output or []:
            if getattr(item, "type", "") == "reasoning":
                parts += [s.text for s in (getattr(item, "summary", None) or [])]
        return "\n\n".join(parts)

    @staticmethod
    def _responses_usage(u):
        if u is None:
            return None
        details = getattr(u, "output_tokens_details", None)
        return u.input_tokens, u.output_tokens, getattr(details, "reasoning_tokens", None)

    # --- JSON replies ------------------------------------------------------

    def complete_json(self, messages: list[dict], schema: str, max_attempts: int = config.JSON_MAX_RETRIES,
                      **kwargs) -> tuple[dict, list[Reply]]:
        """Ask until the reply parses and has the schema keys; the error is sent back to the model."""
        history = list(messages)
        replies: list[Reply] = []
        error = ""
        for _ in range(max_attempts):
            reply = self.chat(history, **kwargs)
            replies.append(reply)
            try:
                return parse_reply(reply.text, schema), replies
            except SchemaError as e:
                error = str(e)
                log.warning("llm %s: invalid JSON reply (%s)", self.provider, error)
                history += [
                    {"role": "assistant", "content": reply.text},
                    {"role": "user", "content": f"Your reply was rejected: {error}. "
                                                "Answer again with the JSON object only, no other text."},
                ]
        raise JSONReplyError(f"{self.provider}: no valid '{schema}' JSON after {max_attempts} attempts: {error}")
