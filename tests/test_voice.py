"""Dictation with Meta Muse Voice Transcribe (autolab/llm/voice.py) and its relay in the web server (/ws/voice).
No network: the Meta WebSocket is a stand-in."""

import asyncio
import json

from fastapi.testclient import TestClient

import web.app as webapp
from autolab import config
from autolab.llm import voice


def test_handshake_and_messages_of_the_meta_protocol():
    h = json.loads(voice.handshake("abc"))
    assert h["authorization"]["accessToken"] == "Bearer abc" and h["model"] == config.VOICE_MODEL
    assert h["mode"] == "PUSH_TO_TALK" and h["audioEncoding"] == "PCM_16KHZ"
    assert voice.parse('{"sessionId": "x"}') is None
    assert voice.parse('{"type": "transcript", "transcript": "Find new", "final": false}') == {"type": "partial", "text": "Find new"}
    assert voice.parse('{"type": "transcript", "transcript": "Find new sodium.", "final": true}')["type"] == "final"
    assert voice.parse('{"type": "error", "message": "x"}')["type"] == "error"
    assert voice.parse(b"not json") is None
    assert voice.max_bytes() == config.VOICE_MAX_SECONDS * 32000


def test_the_relay_refuses_without_a_key(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.setattr(webapp, "_env_file_value", lambda name: None)
    with TestClient(webapp.app).websocket_connect("/ws/voice") as ws:
        assert ws.receive_json()["type"] == "error"


class FakeMeta:
    """The Meta WebSocket: records what it receives, answers a final transcript after endStream."""

    def __init__(self):
        self.sent, self._out = [], asyncio.Queue()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def send(self, data):
        self.sent.append(data)
        if data == voice.END_STREAM:
            await self._out.put(json.dumps({"type": "transcript", "transcript": "Find sodium", "final": False}))
            await self._out.put(json.dumps({"type": "transcript", "transcript": "Find sodium electrolytes.", "final": True}))
            await self._out.put(None)

    def __aiter__(self):
        return self

    async def __anext__(self):
        item = await self._out.get()
        if item is None:
            raise StopAsyncIteration
        return item


def test_the_relay_streams_audio_to_meta_and_returns_the_transcript(monkeypatch):
    import websockets

    fake = FakeMeta()
    monkeypatch.setenv("MODEL_API_KEY", "secret")
    monkeypatch.setattr(websockets, "connect", lambda *a, **k: fake)
    with TestClient(webapp.app).websocket_connect("/ws/voice") as ws:
        ws.send_bytes(b"\x00\x01" * 1280)
        ws.send_text(json.dumps({"type": "stop"}))
        events = [ws.receive_json() for _ in range(3)]
    assert events[0] == {"type": "partial", "text": "Find sodium"}
    assert events[1] == {"type": "final", "text": "Find sodium electrolytes."} and events[2]["type"] == "done"
    assert json.loads(fake.sent[0])["authorization"]["accessToken"] == "Bearer secret"  # the key stays server-side
    assert fake.sent[1] == b"\x00\x01" * 1280 and fake.sent[-1] == voice.END_STREAM
