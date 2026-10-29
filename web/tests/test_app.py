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
    for path in ("/", "/c/3f2a9c1b77aa"):
        r = client.get(path)
        assert r.status_code == 200 and "What material shall we discover today?" not in r.text  # rendered by JS
        assert '<script type="module" src="/static/app.js">' in r.text
    assert client.get("/static/app.js").status_code == 200


def test_the_api_is_unavailable_until_the_service_is_configured(monkeypatch):
    monkeypatch.delenv("AUTOLAB_API_URL", raising=False)
    r = client.get("/api/conversations")
    assert r.status_code == 503 and "not configured" in r.json()["detail"]


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


@pytest.mark.parametrize("word", ["Muse", "Baseten", "Fireworks", "Glimmer", "Meta ", "token", "Replay", "replay",
                                  "GPU", "credit", "USD", "$/"])
def test_no_model_provider_cost_or_replay_mode_is_shown(word):
    assert word not in visible_text()


def test_light_theme_by_default_and_a_tutorial_of_five_cards():
    html = (webapp.HERE / "static" / "index.html").read_text(encoding="utf-8")
    js = (webapp.HERE / "static" / "app.js").read_text(encoding="utf-8")
    assert 'data-theme="light"' in html and '|| "light"' in js
    tutorial = js[js.index("const TUT = ["):js.index("let tutIndex")]
    assert "How does AutoLab work?" in html and len(re.findall(r'(?m)^  { title: "', tutorial)) == 5
