"""Is a request within what AutoLab can do, and is it a follow-up or a new discovery? (interface.md 10.2, 11)

The model reads the request against config.CAPABILITIES and answers in JSON; the code then holds it to that list:
a domain that is not implemented is never "supported", and in an existing conversation a new discovery is refused
(the user is invited to start a new chat), whatever the model says.
"""

from __future__ import annotations

import json

from autolab import config
from autolab.llm.schemas import template

INTENTS = ("new_discovery", "follow_up", "other")
STATUSES = ("supported", "planned", "unsupported")


def _system(in_conversation: bool) -> str:
    caps = config.CAPABILITIES
    supported = "\n".join(f"- {k}: {v}" for k, v in caps["supported"].items())
    planned = "\n".join(f"- {k}: {v}" for k, v in caps["planned"].items())
    where = ("The user writes inside an existing research conversation (its context is given). "
             "intent = follow_up for any question about that research (explanations, interpretation, limits, advice, "
             "validation or synthesis ideas, comparisons of its candidates); new_discovery only if the user asks to "
             "search for, generate or screen new materials." if in_conversation else
             "The user starts a new conversation.")
    return f"""You are the front desk of AutoLab, an AI research assistant for materials discovery.
Research areas that are implemented:
{supported}
Planned, not implemented yet:
{planned}
Never computed: {caps['not_computed']}.
{where}
Classify the message:
- intent: "new_discovery" (find, design, screen or rank new materials), "follow_up" (a question about an existing research) or "other".
- status: "supported" only if the request falls within an implemented area (domain = its key); "planned" if it belongs to a planned area (domain = its key); otherwise "unsupported" (domain = "").
- title: 3 to 6 words naming the research, in the user's language (e.g. "Halide-doped sulfide electrolytes").
- constraints: the explicit constraints of the request, as short phrases.
- reply: 2 or 3 plain sentences to the user, in their language. If supported: restate the goal and what AutoLab will evaluate. If planned or unsupported: say honestly that it is not available yet or not covered, and list the implemented areas. Never claim an analysis was done.
Note: an electrolyte contains no cobalt; "cobalt-free" only concerns cathodes: if the user asks for "cobalt-free electrolytes", say so kindly and treat it as a solid-electrolyte request.
Reply with JSON only, exactly this shape: {template("scope")}"""


def scope_messages(text: str, context: dict | None = None) -> list[dict]:
    user = {"message": text, **({"conversation": context} if context else {})}
    return [{"role": "system", "content": _system(context is not None)},
            {"role": "user", "content": json.dumps(user, default=str)}]


def enforce(reply: dict, in_conversation: bool) -> dict:
    """The model's classification held to config.CAPABILITIES and to the follow-up rule."""
    intent = reply.get("intent") if reply.get("intent") in INTENTS else "other"
    status = reply.get("status") if reply.get("status") in STATUSES else "unsupported"
    domain = reply.get("domain") or ""
    if status == "supported" and domain not in config.CAPABILITIES["supported"]:
        status = "planned" if domain in config.CAPABILITIES["planned"] else "unsupported"
    if status == "planned" and domain not in config.CAPABILITIES["planned"]:
        status = "unsupported"
    title = " ".join(str(reply.get("title") or "New research").split())[:60]
    out = {"intent": intent, "status": status, "domain": domain if status != "unsupported" else "",
           "title": title, "constraints": [str(c) for c in reply.get("constraints", [])][:8],
           "reply": str(reply.get("reply") or "").strip()}
    if in_conversation:
        out["action"] = "new_chat" if intent == "new_discovery" else "answer"
    else:
        out["action"] = "start" if intent == "new_discovery" and status == "supported" else "explain"
    return out


NEW_CHAT_NOTICE = ("This request appears to start a new material discovery. Start a new chat to keep this research "
                   "separate from your current investigation.")
