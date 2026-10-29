"""LLM client tests with a fake OpenAI client: no network, no cost (SPEC 7: JSON truth test)."""

from types import SimpleNamespace as NS

import httpx
import openai
import pytest

from autolab import config
from autolab.llm import client as llm
from autolab.llm.schemas import SchemaError, parse_reply, strip_fences

VALID_PROPOSAL = ('{"hypothesis": "Cl on S sites widens Li paths", "proposals": [{"parent": "mp-985583", '
                  '"substitution": {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1}, "rationale": "x"}]}')


def chat_reply(text, reasoning="", n_in=10, n_out=20):
    usage = NS(prompt_tokens=n_in, completion_tokens=n_out, completion_tokens_details=NS(reasoning_tokens=5))
    return NS(choices=[NS(message=NS(content=text, reasoning_content=reasoning))], usage=usage)


def chunk(content=None, reasoning=None, usage=None):
    choices = [] if usage else [NS(delta=NS(content=content, reasoning_content=reasoning))]
    return NS(choices=choices, usage=usage)


class FakeOpenAI:
    """Returns prepared replies in order and records every request."""

    def __init__(self, replies=(), error=None):
        self.replies = list(replies)
        self.error = error
        self.requests = []
        self.chat = NS(completions=NS(create=self._create))
        self.responses = NS(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        if self.error:
            raise self.error
        return self.replies.pop(0)


def make(provider="baseten", replies=(), error=None, **limits):
    fake = FakeOpenAI(replies, error)
    return llm.LLMClient(provider, tracker=llm.UsageTracker(**limits), client=fake), fake


def test_strip_fences_and_schema_errors():
    assert strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert parse_reply(f"```json\n{VALID_PROPOSAL}\n```", "proposal")["proposals"][0]["parent"] == "mp-985583"
    with pytest.raises(SchemaError, match="missing the key 'stop'"):
        parse_reply('{"ranking": [], "lessons": [], "next_direction": "x"}', "analysis")
    with pytest.raises(SchemaError, match="substitution"):
        parse_reply('{"hypothesis": "h", "proposals": [{"parent": "p", "substitution": {"remove": "S"}, '
                    '"rationale": "r"}]}', "proposal")
    with pytest.raises(SchemaError, match="invalid JSON"):
        parse_reply("Sure! Here is the JSON:", "proposal")


def test_json_truth_valid_after_retry():
    """SPEC 7: valid JSON with all keys after <= 3 attempts; the error is sent back to the model."""
    client, fake = make(replies=[chat_reply("not json"), chat_reply('{"hypothesis": "h"}'),
                                 chat_reply(VALID_PROPOSAL)])
    obj, replies = client.complete_json([{"role": "user", "content": "propose"}], "proposal")
    assert obj["proposals"][0]["substitution"]["add"] == "Cl"
    assert len(replies) == 3 and len(fake.requests) == 3
    last = fake.requests[-1]["messages"]
    assert "missing the key 'proposals'" in last[-1]["content"] and last[-2]["role"] == "assistant"


def test_json_gives_up_after_three_attempts():
    client, fake = make(replies=[chat_reply("no")] * 5)
    with pytest.raises(llm.JSONReplyError):
        client.complete_json([{"role": "user", "content": "x"}], "analysis")
    assert len(fake.requests) == config.JSON_MAX_RETRIES == 3


def test_chat_stream_reasoning_usage_and_cost():
    stream = iter([chunk(reasoning="think "), chunk(reasoning="hard"), chunk(content="Hel"), chunk(content="lo"),
                   chunk(usage=NS(prompt_tokens=100, completion_tokens=1000, completion_tokens_details=None))])
    client, fake = make(replies=[stream])
    seen = []
    reply = client.chat([{"role": "user", "content": "hi"}], stream=True, on_reasoning=seen.append)
    assert (reply.text, reply.reasoning, seen) == ("Hello", "think hard", ["think ", "hard"])
    assert fake.requests[0]["stream_options"] == {"include_usage": True}
    assert reply.cost_usd == pytest.approx((100 * 1.25 + 1000 * 4.25) / 1e6)
    assert client.tracker.summary()["by_provider"]["baseten"]["output_tokens"] == 1000


def test_meta_uses_responses_api_with_reasoning_summary():
    usage = NS(input_tokens=50, output_tokens=300, output_tokens_details=NS(reasoning_tokens=250))
    resp = NS(output_text="ok", usage=usage,
              output=[NS(type="reasoning", summary=[NS(text="step 1")]), NS(type="message")])
    events = iter([NS(type="response.reasoning_summary_text.delta", delta="plan"),
                   NS(type="response.output_text.delta", delta="ok"),
                   NS(type="response.completed", response=resp)])
    client, fake = make("meta", replies=[resp, events])
    msgs = [{"role": "system", "content": "be brief"}, {"role": "user", "content": "hi"}]
    reply = client.chat(msgs, reasoning_effort="low")
    assert (reply.text, reply.reasoning, reply.reasoning_tokens) == ("ok", "step 1", 250)
    req = fake.requests[0]
    assert req["instructions"] == "be brief" and req["input"] == msgs[1:]
    assert req["reasoning"] == {"summary": "auto", "effort": "low"}
    streamed = client.chat(msgs, stream=True)
    assert (streamed.text, streamed.reasoning, streamed.output_tokens) == ("ok", "plan", 300)


def test_budget_stops_before_calling():
    client, fake = make(replies=[chat_reply("a")] * 3, max_calls=2)
    client.chat([{"role": "user", "content": "x"}])
    client.chat([{"role": "user", "content": "x"}])
    with pytest.raises(llm.BudgetExceeded):
        client.chat([{"role": "user", "content": "x"}])
    assert len(fake.requests) == 2
    cheap, fake = make(replies=[chat_reply("a", n_out=10_000)] * 2, max_cost_usd=0.01)
    cheap.chat([{"role": "user", "content": "x"}])  # $0.0425 > $0.01
    with pytest.raises(llm.BudgetExceeded):
        cheap.chat([{"role": "user", "content": "x"}])
    assert len(fake.requests) == 1


def test_quota_error_is_not_retried():
    response = httpx.Response(429, request=httpx.Request("POST", "https://example.invalid"))
    client, fake = make(error=openai.RateLimitError("rate limited", response=response, body=None))
    with pytest.raises(llm.QuotaError):
        client.complete_json([{"role": "user", "content": "x"}], "analysis")
    assert len(fake.requests) == 1


def test_unknown_provider_and_missing_key(monkeypatch):
    with pytest.raises(ValueError):
        llm.LLMClient("openrouter", client=FakeOpenAI())
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    with pytest.raises(config.MissingKeyError, match="FIREWORKS_API_KEY"):
        llm.LLMClient("fireworks")


def test_reply_cache_answers_a_known_question_for_free(tmp_path):
    from autolab.store.cache import JsonCache

    cache = JsonCache(tmp_path)
    fake = FakeOpenAI([chat_reply(VALID_PROPOSAL, "thinking", n_in=1000, n_out=2000)])
    first = llm.LLMClient("baseten", tracker=llm.UsageTracker(), client=fake, cache=cache)
    obj, replies = first.complete_json([{"role": "user", "content": "propose"}], "proposal")
    assert replies[0].cost_usd > 0 and not replies[0].cached and len(fake.requests) == 1

    tracker = llm.UsageTracker(max_calls=1)
    again = llm.LLMClient("baseten", tracker=tracker, client=FakeOpenAI([]), cache=cache)
    obj2, replies2 = again.complete_json([{"role": "user", "content": "propose"}], "proposal")
    assert obj2 == obj and replies2[0].cached and replies2[0].cost_usd == 0 and replies2[0].reasoning == "thinking"
    assert tracker.calls == 0 and tracker.cost_usd == 0  # no call, no cost
    with pytest.raises(IndexError):  # another question is not in the cache: a real call (none prepared here)
        again.complete_json([{"role": "user", "content": "something else"}], "proposal")
