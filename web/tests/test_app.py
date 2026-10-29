"""Tests for the jury page backend (no network)."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

import web.app as appmod

REF = appmod.REF_DIR


@pytest.fixture
def client(monkeypatch):
    """Test client with live mode off, as on a plain checkout."""
    monkeypatch.delenv("AUTOLAB_LIVE", raising=False)
    monkeypatch.delenv("AUTOLAB_API_URL", raising=False)
    return TestClient(appmod.app)


def test_index_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "AutoLab" in response.text


def test_replay_events_keep_order(client):
    """Replay serves events.jsonl as an array, in file order."""
    lines = [json.loads(line) for line in (REF / "events.jsonl").read_text(encoding="utf-8").splitlines()
             if line.strip()]
    response = client.get("/api/replay/events.jsonl")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == len(lines) > 100
    assert [(e["type"], e["step"], e.get("candidate_id")) for e in events] == [
        (e["type"], e["step"], e.get("candidate_id")) for e in lines]


def test_replay_result_returns_goal(client):
    want = json.loads((REF / "result.json").read_text(encoding="utf-8"))["goal"]
    response = client.get("/api/replay/result.json")
    assert response.status_code == 200
    assert response.json()["goal"] == want
    assert "lithium" in want.lower()


def test_replay_unknown_file_404(client):
    assert client.get("/api/replay/nope.json").status_code == 404
    assert client.get("/api/replay/replay/md/../../app.py").status_code == 404


def test_live_routes_403_when_disabled(client):
    assert client.get("/api/live/health").status_code == 403
    assert client.post("/api/live/runs", json={"goal": "x", "access_code": "y"}).status_code == 403
    assert client.get("/api/live/runs/abc/events").status_code == 403
    assert client.get("/api/live/runs/abc/result").status_code == 403
    assert client.get("/api/live/health").json() == {"detail": "live mode disabled"}


def test_live_routes_403_without_url(monkeypatch):
    monkeypatch.setenv("AUTOLAB_LIVE", "1")
    monkeypatch.delenv("AUTOLAB_API_URL", raising=False)
    client = TestClient(appmod.app)
    assert client.get("/api/live/health").status_code == 403


class _FakeResponse:
    def __init__(self, status_code=200, content=b"{}"):
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": "application/json"}


def _patch_http(monkeypatch, response, error=None):
    """Replace the HTTP client with a fake that records its request."""
    seen = {}

    class FakeClient:
        def __init__(self, base_url=None, timeout=None):
            seen["base_url"] = base_url

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def request(self, method, path, content=None, params=None, headers=None):
            seen.update(method=method, path=path, content=content, params=params)
            if error is not None:
                raise error
            return response

    monkeypatch.setenv("AUTOLAB_LIVE", "1")
    monkeypatch.setenv("AUTOLAB_API_URL", "https://modal.test")
    monkeypatch.setattr("web.app.httpx.AsyncClient", FakeClient)
    return seen


def test_relay_passes_body_and_status_through(monkeypatch):
    seen = _patch_http(monkeypatch, _FakeResponse(403, b'{"detail": "wrong code"}'))
    response = TestClient(appmod.app).post("/api/live/runs", json={"goal": "hi", "access_code": "zz"})
    assert response.status_code == 403
    assert response.json() == {"detail": "wrong code"}
    assert seen["method"] == "POST" and seen["path"] == "/api/runs"
    assert json.loads(seen["content"]) == {"goal": "hi", "access_code": "zz"}


def test_relay_passes_query_through(monkeypatch):
    seen = _patch_http(monkeypatch, _FakeResponse(200, b'{"events":[],"next":3}'))
    response = TestClient(appmod.app).get("/api/live/runs/abc123/events?after=12")
    assert response.status_code == 200
    assert (seen["path"], seen["params"]) == ("/api/runs/abc123/events", {"after": 12})


def test_relay_unreachable_503(monkeypatch):
    _patch_http(monkeypatch, _FakeResponse(), error=httpx.ConnectError("down"))
    response = TestClient(appmod.app).get("/api/live/health")
    assert response.status_code == 503
