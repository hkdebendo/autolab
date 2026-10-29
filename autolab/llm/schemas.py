"""JSON schemas of the model replies and their validation (SPEC 5.12).

A schema maps each required key to its Python type. Validation errors are
plain sentences: they are sent back to the model on a retry.
"""

from __future__ import annotations

import json
import re

PROPOSAL = {"hypothesis": str, "proposals": list}
PROPOSAL_ITEM = {"parent": str, "substitution": dict, "rationale": str}
SUBSTITUTION = {"remove": str, "add": str, "count": (int, str)}

ANALYSIS = {"ranking": list, "lessons": list, "next_direction": str, "stop": bool}
MD_SELECTION = {"selected": list, "rationale": str}

SCHEMAS = {"proposal": PROPOSAL, "analysis": ANALYSIS, "md_selection": MD_SELECTION}

TEMPLATES = {
    "proposal": {
        "hypothesis": "short sentence",
        "proposals": [{"parent": "mp-985583",
                       "substitution": {"remove": "S", "add": "Cl", "count": 1, "li_vacancies": 1},
                       "rationale": "short sentence"}],
    },
    "analysis": {"ranking": ["candidate_id"], "lessons": ["short sentence"],
                 "next_direction": "short sentence", "stop": False},
    "md_selection": {"selected": ["candidate_id"], "rationale": "short sentence"},
}

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.S)


class SchemaError(ValueError):
    """The reply is not valid JSON or misses required keys."""


def strip_fences(text: str) -> str:
    """Remove a ```json ... ``` wrapper if present."""
    m = _FENCE.match(text or "")
    return m.group(1) if m else (text or "").strip()


def _check_keys(obj, schema: dict, where: str) -> None:
    if not isinstance(obj, dict):
        raise SchemaError(f"{where} must be a JSON object, got {type(obj).__name__}")
    for key, kind in schema.items():
        if key not in obj:
            raise SchemaError(f"{where} is missing the key '{key}'")
        if not isinstance(obj[key], kind):
            raise SchemaError(f"{where}['{key}'] has the wrong type ({type(obj[key]).__name__})")


def validate(obj, name: str) -> dict:
    """Check a parsed reply against the named schema; return it unchanged."""
    _check_keys(obj, SCHEMAS[name], "the reply")
    if name == "proposal":
        for i, item in enumerate(obj["proposals"]):
            _check_keys(item, PROPOSAL_ITEM, f"proposals[{i}]")
            _check_keys(item["substitution"], SUBSTITUTION, f"proposals[{i}]['substitution']")
    return obj


def parse_reply(text: str, name: str) -> dict:
    """Strip fences, parse JSON and validate; raise SchemaError with a readable reason."""
    try:
        obj = json.loads(strip_fences(text))
    except json.JSONDecodeError as e:
        raise SchemaError(f"invalid JSON ({e.msg} at line {e.lineno}, column {e.colno})") from None
    return validate(obj, name)


def template(name: str) -> str:
    """Example of the expected JSON, to put in the instructions."""
    return json.dumps(TEMPLATES[name])
