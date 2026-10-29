"""The AutoLab service behind the interface (interface.md 4-12): conversations, research runs, follow-up questions,
stopping. Pure logic over a store (store/conversations.py) and injected models, so that it is tested without network;
modal_app/agent_app.py exposes it as a web API and runs the researches.
"""

from __future__ import annotations

import contextlib
import time
import uuid
from typing import Callable

from autolab import config
from autolab.agent import followup
from autolab.agent.progress import steps_from_events
from autolab.agent.scope import NEW_CHAT_NOTICE, enforce, scope_messages
from autolab.store.conversations import ACTIVE, question_key

BUSY = ("AutoLab is already running another research. Please try again when it has finished (the conversations in "
        "the history can be opened meanwhile).")
LIMIT = "The number of new researches allowed for this demonstration has been reached."
UNAVAILABLE = "AutoLab could not analyse this request right now. Please try again in a moment."
RUNNING = ("The research is still running: AutoLab will answer questions about it once it has finished. You can "
           "follow its steps above, or stop it.")


def run_state(status: str) -> str:
    return {"queued": "running", "stopping": "running", "running": "running", "done": "done",
            "interrupted": "interrupted", "error": "error"}.get(status, "done")


def ask_json(clients: list, messages: list[dict], schema: str) -> dict | None:
    """JSON reply from the first model that answers (main, then fallback once); None when none can."""
    from autolab.llm.client import LLMError

    for c in clients:
        if c is None:
            continue
        try:
            obj, _ = c.complete_json(messages, schema, max_output_tokens=config.AGENT_MAX_OUTPUT_TOKENS)
            return obj
        except LLMError:
            continue
    return None


class Service:
    """`models()` returns [main, fallback] clients for the scope check and the follow-ups; `spawn(cid)` starts the
    research of a conversation in the background (a Modal function in production)."""

    def __init__(self, store, models: Callable[[], list], spawn: Callable[[str], None]):
        self.store, self.models, self.spawn = store, models, spawn

    # --- reading -------------------------------------------------------------------------------------------------

    def history(self) -> list[dict]:
        return self.store.list()

    def view(self, cid: str) -> dict | None:
        conv = self.store.get(cid)
        if conv is None:
            return None
        events = self.store.events(cid)
        return {"conversation": _public(conv), "messages": [_message(m) for m in self.store.messages(cid)],
                "steps": steps_from_events(events, run_state(conv["status"])) if events or conv["status"] in ACTIVE
                else [], "events_count": len(events), "has_result": self.store.result(cid) is not None,
                "files": [a["name"] for a in self.store.artifacts(cid)]}

    def progress(self, cid: str, after: int = 0) -> dict | None:
        conv = self.store.get(cid)
        if conv is None:
            return None
        events = self.store.events(cid)
        return {"status": conv["status"], "events": [e for e in events if e["seq"] >= after], "next": len(events),
                "steps": steps_from_events(events, run_state(conv["status"]))}

    # --- writing -------------------------------------------------------------------------------------------------

    def start(self, text: str) -> dict:
        """A new conversation from a request: scope check, title, then the research if it can run."""
        text = (text or "").strip()
        if not text or len(text) > config.LIVE_GOAL_MAX_CHARS:
            raise ValueError(f"the request must be 1 to {config.LIVE_GOAL_MAX_CHARS} characters")
        reply = ask_json(self.models(), scope_messages(text), "scope")
        cid = uuid.uuid4().hex[:12]
        if reply is None:
            self.store.create({"id": cid, "title": text[:60], "goal": text, "status": "answered"})
            self.store.add_message(cid, "user", "request", text)
            self.store.add_message(cid, "assistant", "notice", UNAVAILABLE)
            return self.view(cid)
        scope = enforce(reply, in_conversation=False)
        self.store.create({"id": cid, "title": scope["title"], "goal": text, "domain": scope["domain"] or None,
                           "status": "answered", "scope": scope})
        self.store.add_message(cid, "user", "request", text)
        self.store.add_message(cid, "assistant", "scope", scope["reply"] or "", data=scope)
        if scope["action"] == "start":
            if self.store.active_research():
                self.store.add_message(cid, "assistant", "notice", BUSY)
            elif self.store.live_runs_used() >= config.LIVE_MAX_RUNS:
                self.store.add_message(cid, "assistant", "notice", LIMIT)
            else:
                self.store.update(cid, status="queued")
                try:
                    self.spawn(cid)
                except Exception as e:  # quota or payment: said, never retried
                    self.store.update(cid, status="error", error=f"{type(e).__name__}: {e}"[:300])
                    self.store.add_message(cid, "assistant", "notice", "The research could not start.")
        return self.view(cid)

    def post(self, cid: str, text: str) -> dict | None:
        """A message in an existing conversation: follow-up answered from the stored research, never a new one."""
        conv = self.store.get(cid)
        if conv is None:
            return None
        text = (text or "").strip()
        if not text or len(text) > config.LIVE_GOAL_MAX_CHARS * 4:
            raise ValueError("empty or too long message")
        key = question_key(text)
        self.store.add_message(cid, "user", "follow_up", text, question_key=key)
        if conv["status"] in ACTIVE:
            self.store.add_message(cid, "assistant", "notice", RUNNING)
            return self.view(cid)
        stored = self.store.find_answer(cid, key)
        if stored is not None:  # the same question on the same research: the stored answer, no model call
            self.store.add_message(cid, "assistant", "answer", stored["content"], data={"reused": True},
                                   question_key=key)
            return self.view(cid)
        result = self.store.result(cid)
        facts = followup.context(result) if result else {"goal": conv["goal"], "note": "no research was run"}
        reply = ask_json(self.models(), scope_messages(text, context={"goal": conv["goal"],
                                                                       "finalists": facts.get("finalists", [])[:3]}),
                         "scope")
        if reply is not None and enforce(reply, in_conversation=True)["action"] == "new_chat":
            self.store.add_message(cid, "assistant", "notice", NEW_CHAT_NOTICE, data={"action": "new_chat"})
            return self.view(cid)
        history = _qa_history(self.store.messages(cid))
        from autolab.llm.client import LLMError

        for model in self.models():
            if model is None:
                continue
            try:
                ans = model.chat(followup.followup_messages(text, facts, history),
                                 max_output_tokens=config.FOLLOWUP_MAX_OUTPUT_TOKENS)
            except LLMError:
                continue
            if ans.text.strip():
                self.store.add_message(cid, "assistant", "answer", ans.text.strip(), question_key=key)
                return self.view(cid)
        self.store.add_message(cid, "assistant", "notice", UNAVAILABLE)
        return self.view(cid)

    def cancel(self, cid: str) -> dict | None:
        """A real stop request: stored, read by the running research between its steps."""
        conv = self.store.get(cid)
        if conv is None:
            return None
        if conv["status"] in ("queued", "running"):
            self.store.update(cid, status="stopping", cancel_requested_at=time_now())
            self.store.add_message(cid, "assistant", "notice", "Stopping the research: the step in progress finishes, "
                                   "nothing new starts. The results already obtained are kept.")
        return self.view(cid)

    def rename(self, cid: str, title: str) -> dict | None:
        title = " ".join((title or "").split())[:80]
        if not title or self.store.get(cid) is None:
            return None
        self.store.update(cid, title=title)
        return self.view(cid)

    def delete(self, cid: str) -> bool:
        conv = self.store.get(cid)
        if conv is None or conv["status"] in ACTIVE:
            return False  # a running research is stopped first
        self.store.delete(cid)
        return True

    # --- the research itself (worker) ----------------------------------------------------------------------------

    def run(self, cid: str, make_agent: Callable, prior: list[dict], export: Callable | None = None) -> dict | None:
        """Run the research of a conversation: events stored as they happen, a stop request honoured, the result,
        the report and a summary stored at the end. `make_agent(events, should_stop)` builds the Agent."""
        from autolab.agent.events import EventLog
        from autolab.agent.loop import INTERRUPTED

        conv = self.store.get(cid)
        if conv is None or conv["status"] not in ("queued", "stopping"):
            return None
        if conv["status"] == "stopping":  # stopped before it started
            self.store.update(cid, status="interrupted")
            return None
        self.store.update(cid, status="running")
        seq = {"n": len(self.store.events(cid))}

        def sink(event: dict) -> None:
            self.store.append_event(cid, seq["n"], event)
            seq["n"] += 1

        events = EventLog(sink=sink)
        events.emit("loop", "scope", {k: v for k, v in (conv.get("scope") or {}).items() if k != "reply"})
        last = {"t": 0.0, "stop": False}

        def should_stop() -> bool:  # read from the store at most every few seconds
            if time.monotonic() - last["t"] > config.STOP_POLL_S:
                c = self.store.get(cid)
                last["stop"], last["t"] = bool(c and c.get("cancel_requested_at")), time.monotonic()
            return last["stop"]

        try:
            with live_limits():
                agent = make_agent(events, should_stop)
                result = agent.run(conv["goal"], None, config.LIVE_ITERATIONS, config.LIVE_CANDIDATES, prior=prior)
        except Exception as e:  # reported in the conversation, never retried
            self.store.update(cid, status="error", error=f"{type(e).__name__}: {e}"[:500])
            self.store.add_message(cid, "assistant", "notice", "The research stopped on an error; the steps already "
                                   "done are kept above.")
            return None
        self.store.save_result(cid, result)
        self.finish(cid, result, agent.domain)
        if export is not None:
            with contextlib.suppress(Exception):  # the 3D files are a bonus: never fail the research for them
                export(cid, result)
        self.store.update(cid, status="interrupted" if result["stop_reason"] == INTERRUPTED else "done")
        return result

    def finish(self, cid: str, result: dict, domain) -> None:
        """Summary and report messages of a finished research (also used to import recorded runs)."""
        st = result.get("stages", {})
        run_summary = next((s["text"] for s in reversed(result.get("summaries") or [])
                            if s.get("label") == "run" and s.get("text")), None)
        self.store.add_message(cid, "assistant", "summary", run_summary or code_summary(result))
        rep = st.get("report")
        stage = next((s for s in domain.stages if s.name == "report"), None)
        if rep and rep.get("status") in ("done", "stopped") and stage and stage.render:
            self.store.add_message(cid, "assistant", "report", "\n".join(stage.render(rep, result)),
                                   data={"champion": rep.get("champion"), "completeness": rep.get("completeness")})


def code_summary(result: dict) -> str:
    """A factual summary written by the code when no model summary exists."""
    rk = result.get("stages", {}).get("ranking", {})
    pool = {c["id"]: c for c in result.get("prior", []) + [c for r in result.get("iterations", [])
                                                          for c in r["candidates"]]}
    new = [c for r in result.get("iterations", []) for c in r["candidates"]]
    fin = [pool[i]["formula"] for i in rk.get("finalists", []) if i in pool]
    out = f"{len(new)} new candidates evaluated, {len(result.get('funnel_ranking', []))} passed the screening."
    if fin:
        out += f" Finalists: {', '.join(fin)}."
    if result.get("stop_reason") and result["stop_reason"] != "iterations done":
        out += f" Stopped: {result['stop_reason']}."
    return out


@contextlib.contextmanager
def live_limits():
    """The config limits of a live research, restored afterwards."""
    saved = {"MD_SELECT_MAX": config.MD_SELECT_MAX}
    config.MD_SELECT_MAX = config.LIVE_MD_SELECT_MAX
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(config, k, v)


def time_now():
    from autolab.store.conversations import now

    return now()


def _public(conv: dict) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in conv.items()
            if k in ("id", "title", "goal", "domain", "status", "error", "created_at", "updated_at", "scope")}


def _message(m: dict) -> dict:
    return {"id": m["id"], "role": m["role"], "kind": m["kind"], "content": m["content"], "data": m.get("data"),
            "created_at": m["created_at"].isoformat() if hasattr(m["created_at"], "isoformat") else m["created_at"]}


def _qa_history(messages: list[dict]) -> list[dict]:
    out, q = [], None
    for m in messages:
        if m["kind"] == "follow_up":
            q = m["content"]
        elif m["kind"] == "answer" and q:
            out.append({"question": q, "answer": m["content"]})
            q = None
    return out
