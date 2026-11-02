"""The web server of the interface: the page, the relay to the AutoLab service, and what the page never shows
(interface.md 15). No network: the AutoLab service is a fake HTTP transport."""

import json
import re

import httpx
import pytest
from fastapi.testclient import TestClient

import web.app as webapp

client = TestClient(webapp.app)


def test_the_page_opens_at_home_and_at_a_conversation_address():
    for path in ("/", "/c/3f2a9c1b77aa", "/results", "/results/cathode", "/settings", "/settings/sodium", "/settings/cathode/edit", "/benchmarks", "/benchmarks/sodium"):
        r = client.get(path)
        assert r.status_code == 200 and "What material shall we discover today?" not in r.text  # rendered by JS
        assert '<script type="module" src="/static/app.js">' in r.text
    assert client.get("/static/app.js").status_code == 200


def test_the_api_is_unavailable_until_the_service_is_configured(monkeypatch):
    monkeypatch.delenv("AUTOLAB_API_URL", raising=False)
    monkeypatch.setattr(webapp, "_env_file_value", lambda name: None)  # no .env either
    r = client.get("/api/conversations")
    assert r.status_code == 503 and "not configured" in r.json()["detail"]


def test_the_service_address_can_come_from_the_env_file(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("MP_API_KEY=x\nAUTOLAB_API_URL=https://svc.example  # comment\n", encoding="utf-8")
    monkeypatch.setattr(webapp, "HERE", tmp_path / "web")
    assert webapp._env_file_value("AUTOLAB_API_URL") == "https://svc.example"
    assert webapp._env_file_value("MISSING") is None


def test_the_relay_passes_method_body_query_and_status_through(monkeypatch):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path, request.url.query.decode(), request.content))
        if request.url.path.endswith("/cancel"):
            return httpx.Response(404, json={"detail": "conversation not found"})
        return httpx.Response(200, json={"ok": True, "echo": json.loads(request.content or b"null")})

    real = httpx.AsyncClient
    monkeypatch.setattr(webapp.httpx, "AsyncClient",
                        lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    monkeypatch.setenv("AUTOLAB_API_URL", "https://service.example/")
    r = client.post("/api/conversations", json={"message": "Find sulfide electrolytes"})
    assert r.status_code == 200 and r.json()["echo"] == {"message": "Find sulfide electrolytes"}
    assert client.get("/api/conversations/abc/progress", params={"after": 12}).status_code == 200
    assert client.post("/api/conversations/abc/cancel").status_code == 404
    assert client.patch("/api/conversations/abc", json={"title": "New title"}).status_code == 200
    assert client.delete("/api/conversations/abc").status_code == 200
    assert [s[0] for s in seen] == ["POST", "GET", "POST", "PATCH", "DELETE"]
    assert seen[1][1] == "/api/conversations/abc/progress" and seen[1][2] == "after=12"


def visible_text() -> str:
    """The page and its script without code comments: what can end up on screen."""
    html = (webapp.HERE / "static" / "index.html").read_text(encoding="utf-8")
    js = (webapp.HERE / "static" / "app.js").read_text(encoding="utf-8")
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    js = re.sub(r"(?m)^\s*//.*$|\s//\s.*$", "", js)
    html = re.sub(r"<!--.*?-->|<script>.*?</script>", "", html, flags=re.S)
    return html + js


@pytest.mark.parametrize("word", ["Baseten", "Fireworks", "token", "Replay", "replay", "GPU", "credit", "USD", "$/"])
def test_no_provider_cost_or_replay_mode_is_shown(word):
    assert word not in visible_text()


def test_the_models_at_work_are_named_with_what_they_do():
    """Owner, 2026-11-02: show which model works and what it does (interface.md 15 amended)."""
    text = visible_text()
    for model in ("Muse Spark", "Muse Spark Open", "Muse Glimmer", "UMA", "GapModel", "Materials Project"):
        assert model in text


def test_the_live_view_uses_the_websocket_and_formulas_get_subscripts():
    js = (webapp.HERE / "static" / "app.js").read_text(encoding="utf-8")
    assert "/ws/conversations/" in js and "function chem(" in js and "₀₁₂₃₄₅₆₇₈₉" in js
    assert "reused" in js  # results taken from the saved computations are marked


def test_the_lab_opens_full_screen_and_a_paused_replay_can_be_resumed():
    js = (webapp.HERE / "static" / "app.js").read_text(encoding="utf-8")
    css = (webapp.HERE / "static" / "styles.css").read_text(encoding="utf-8")
    assert "function labSetFull(" in js and "data-full" in js and ".lab.full" in css
    assert "Resume watching" in js and "function labQuit(" in js and "data-restart" in js and "data-stop" in js
    assert 'full: mode === "watch"' in js  # a live research stays in the chat until the button opens it


def test_light_theme_by_default_and_a_tutorial_of_five_cards():
    html = (webapp.HERE / "static" / "index.html").read_text(encoding="utf-8")
    js = (webapp.HERE / "static" / "app.js").read_text(encoding="utf-8")
    assert 'data-theme="light"' in html and '|| "light"' in js
    tutorial = js[js.index("const TUT = ["):js.index("let tutIndex")]
    assert "How does AutoLab work?" in html and len(re.findall(r'(?m)^  { title: "', tutorial)) == 5


def test_the_results_page_shows_champions_by_domain_with_report_and_research_buttons():
    js = (webapp.HERE / "static" / "app.js").read_text(encoding="utf-8")
    html = (webapp.HERE / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="results-btn"' in html and "/champions" in js and "function showResults(" in js
    assert "Final report (PDF)" in js and "Open the research" in js and "data-domain" in js


def test_the_settings_page_shows_every_domain_rule_from_config_without_the_service(monkeypatch):
    from autolab import config

    monkeypatch.setattr(webapp, "_service_url", lambda: None)  # read locally, never relayed
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = r.json()
    assert [d["key"] for d in data["domains"]] == ["electrolyte", "cathode", "sodium"]
    rules = {x["name"]: x for d in data["domains"] for g in d["groups"] for x in g["rules"]}
    assert rules["SODIUM_BANDGAP_MIN"]["value"] == config.SODIUM_BANDGAP_MIN
    assert rules["MD_SCREEN_TEMPERATURE_K"]["status"] == "validated"
    assert {x["status"] for x in rules.values()} <= {"validated", "justified", "budget"}
    assert all(hasattr(config, name) for name in rules)


def test_the_benchmark_page_lists_the_tests_of_every_domain_with_a_verdict(monkeypatch):
    from pathlib import Path

    monkeypatch.setattr(webapp, "_service_url", lambda: None)  # recorded results, never relayed
    data = client.get("/api/benchmarks").json()
    assert [d["key"] for d in data["domains"]] == ["electrolyte", "cathode", "sodium"]
    tests = [t for d in data["domains"] for t in d["tests"]]
    assert {t["verdict"] for t in tests} <= {"passed", "failed", "measured"}
    assert any(t["verdict"] == "failed" for t in tests)  # failures are shown
    root = Path(__file__).resolve().parents[2]
    assert all((root / t["source"]).is_dir() for t in tests if t["source"])  # every cited result folder exists


def test_the_home_suggestions_are_the_replay_examples_of_the_service():
    from pathlib import Path

    from autolab import config

    js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text(encoding="utf-8")
    block = js[js.index("const EXAMPLES = ["):js.index("];", js.index("const EXAMPLES = ["))]
    shown = re.findall(r'"([^"]+)"', block)
    assert shown == [text for text, _ in config.REPLAY_EXAMPLES]
