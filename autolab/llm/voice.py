"""Speech to text with Meta Muse Voice Transcribe (realtime WebSocket, push to talk).

Protocol (wss://api.meta.ai/v1/asr/realtime): a JSON handshake carrying the access token, then mono PCM16 audio as
binary frames of 80 ms, then {"type": "endStream"}; Meta answers with {"sessionId"}, cumulative partial transcripts
{"type": "transcript", "final": false} and a final one ("final": true). The key never leaves the server.
"""

from __future__ import annotations

import json

from autolab import config


def handshake(api_key: str) -> str:
    """The first frame of a session (compact JSON)."""
    token = api_key if api_key.lower().startswith("bearer ") else f"Bearer {api_key}"
    return json.dumps({"authorization": {"accessToken": token}, "audioEncoding": config.VOICE_ENCODING,
                       "model": config.VOICE_MODEL, "mode": "PUSH_TO_TALK", "partialMode": "CUMULATIVE",
                       "emitAudioProgress": True}, separators=(",", ":"))


END_STREAM = json.dumps({"type": "endStream"})


def parse(message: str | bytes) -> dict | None:
    """A message from Meta as an event for the browser: {"type": "partial" | "final", "text"} or {"type": "error"};
    None for the messages the browser does not need (session id, audio progress, speech start and end)."""
    try:
        d = json.loads(message)
    except (TypeError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    if d.get("type") == "error" or "error" in d:
        return {"type": "error", "message": "the transcription failed"}
    if d.get("type") == "transcript" and isinstance(d.get("transcript"), str):
        return {"type": "final" if d.get("final") is True else "partial", "text": d["transcript"]}
    if d.get("type") == "speechComplete" and isinstance(d.get("transcript"), str):
        return {"type": "final", "text": d["transcript"]}
    return None


def max_bytes() -> int:
    """Audio accepted in one recording (config.VOICE_MAX_SECONDS of 16 kHz PCM16): a cap on the cost."""
    return config.VOICE_MAX_SECONDS * 16000 * 2
