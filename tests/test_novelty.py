"""Novelty check with a fake Responses API (web search): no network, no cost."""

import json
from types import SimpleNamespace as NS

import pytest

from autolab import config
from autolab.agent import novelty
from autolab.llm import client as llm

LGPS = config.NOVELTY_CONTROL
CAND = {"id": "it2-c5", "formula": "Li11P4S15I", "parent": "mp-985583", "parent_formula": "Li3PS4",
        "substitution": {"remove": "S", "add": "I", "count": 1, "li_vacancies": 1}}


def response(text, citations=(), searches=2, results=3):
    annotations = [NS(type="url_citation", url=u, title=t, start_index=0, end_index=10) for u, t in citations]
    output = [NS(type="web_search_call", results=[{"type": "text_result", "url": f"https://r{i}.org", "title": "r"}
                                                  for i in range(results)]) for _ in range(searches)]
    output += [NS(type="reasoning", summary=[NS(text="looked up LGPS")]),
               NS(type="message", content=[NS(type="output_text", text=text, annotations=annotations)])]
    usage = NS(input_tokens=10_000, output_tokens=1_000, output_tokens_details=NS(reasoning_tokens=600))
    return NS(output=output, output_text=text, usage=usage)


class FakeResponses:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.responses = NS(create=self.create)

    def create(self, **kwargs):
        self.requests.append(kwargs)
        return self.replies.pop(0)


def meta(replies, cap=1.0):
    fake = FakeResponses(replies)
    return llm.LLMClient("meta", tracker=llm.UsageTracker(max_cost_usd=cap), client=fake), fake


def test_published_with_citations_keeps_only_api_links():
    text = ("LEVEL: published\nLi10GeP2S12 was reported in 2011 (see https://made-up.example/paper). "
            "It is a superionic conductor.")
    client, fake = meta([response(text, [("https://doi.org/10.1038/nmat3066", "Kamaya 2011"),
                                         ("https://doi.org/10.1038/nmat3066", "duplicate")])])
    r = novelty.check(LGPS, client, today="2026-10-28")
    assert (r["level"], r["label"]) == ("published", "already published")
    assert r["sources"] == [{"title": "Kamaya 2011", "url": "https://doi.org/10.1038/nmat3066"}]
    assert "made-up.example" not in r["summary"] and "LEVEL" not in r["summary"]
    assert any("URL(s) written by the model removed" in n for n in r["notes"])
    assert r["web_searches"] == 2 and r["sources_considered"] == 6
    # tokens + 2 searches at $0.0025
    assert r["cost_usd"] == pytest.approx((10_000 * 1.25 + 1_000 * 4.25) / 1e6 + 2 * 0.0025, abs=1e-5)
    req = fake.requests[0]
    assert req["tools"] == [{"type": "web_search", "search_context_size": config.NOVELTY_SEARCH_CONTEXT}]
    assert req["include"] == ["web_search_call.results"] and "Never write a URL" in req["instructions"]


def test_claim_without_citation_is_downgraded():
    client, _ = meta([response("LEVEL: related\nIodine-doped Li3PS4 has been studied.", citations=())])
    r = novelty.check(CAND, client)
    assert r["level"] == "none_found" and r["label"] == "no publication found in this search"
    assert any("unsourced claim discarded" in n for n in r["notes"])


def test_overclaims_are_removed_and_missing_level_is_flagged():
    text = "Li11P4S15I has never been reported. Related Li3PS4-LiI glasses exist."
    client, _ = meta([response(text, [("https://doi.org/x", "LiI-Li3PS4 glass")])])
    r = novelty.check(CAND, client)
    assert "never" not in r["summary"] and "glasses exist" in r["summary"]
    assert r["level"] == "none_found" and any("no level" in n for n in r["notes"])
    assert any("over-claiming" in n for n in r["notes"])


def test_candidate_description_names_the_family():
    msg = novelty.messages_for(CAND)[1]["content"]
    assert "Li11P4S15I" in msg and "I-substituted Li3PS4" in msg and "1 Li vacancies" in msg


def test_control_first_then_candidates_and_budget_stop():
    replies = [response("LEVEL: published\nLGPS is known.", [("https://doi.org/a", "a")]),
               response("LEVEL: none_found\nNothing found for this composition.")]
    client, fake = meta(replies, cap=0.02)  # the first call (~$0.022) already exceeds the cap
    out = novelty.novelty_check([CAND, CAND], client)
    assert out["control"]["control_ok"] is True and out["candidates"] == []
    assert out["stopped"].startswith("budget") and len(fake.requests) == 1
    text = novelty.render(json.loads(json.dumps(out)))
    assert "## Novelty check" in text and "(control, expected: already published)" in text
    assert "[a](https://doi.org/a)" in text and "Stopped" in text


def test_web_search_needs_the_responses_api():
    client = llm.LLMClient("baseten", tracker=llm.UsageTracker(), client=FakeResponses([]))
    with pytest.raises(llm.LLMError, match="Responses API"):
        client.web_search([{"role": "user", "content": "x"}])
