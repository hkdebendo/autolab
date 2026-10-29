"""Conversations, messages, events, results, candidates and file references (interface.md 13).

PostgresStore talks to Supabase PostgreSQL (DATABASE_URL, schema "autolab", migrations in db/migrations);
MemoryStore has the same methods, in memory, for the tests. The server is the only writer: the browser never
holds the research data alone.
"""

from __future__ import annotations

import copy
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from autolab import config

ACTIVE = ("queued", "running", "stopping")
MIGRATIONS = Path(__file__).resolve().parents[2] / "db" / "migrations"


def now() -> datetime:
    return datetime.now(timezone.utc)


def question_key(text: str) -> str:
    """A follow-up question reduced to its words (case, spaces and punctuation ignored): the same question asked
    again on the same research is answered from the stored answer."""
    return " ".join(re.findall(r"\w+", (text or "").lower()))[:500]


def candidate_rows(result: dict) -> list[dict]:
    pool = result.get("prior", []) + [c for r in result.get("iterations", []) for c in r["candidates"]]
    return [{"candidate_id": c["id"], "formula": c.get("formula"), "parent": c.get("parent"),
             "substitution": c.get("substitution"), "status": c.get("status"), "excluded_at": c.get("excluded_at"),
             "e_hull": c.get("e_hull"), "gap_optb88": c.get("gap_optb88"), "d_ratio": c.get("D_ratio_to_parent"),
             "md_verdict": c.get("md_verdict"), "novelty": c.get("novelty"),
             "data": {k: v for k, v in c.items() if k != "relaxed_atoms"}} for c in pool]


class MemoryStore:
    """Same interface as PostgresStore, in memory (tests)."""

    def __init__(self):
        self.convs: dict[str, dict] = {}
        self.msgs: dict[str, list[dict]] = {}
        self.evs: dict[str, list[dict]] = {}
        self.results: dict[str, dict] = {}
        self.cands: dict[str, list[dict]] = {}
        self.files: dict[str, dict[str, dict]] = {}
        self._lock = threading.Lock()
        self._next_msg = 1

    def migrate(self) -> list[str]:
        return []

    def create(self, conv: dict) -> dict:
        row = {"domain": None, "scope": None, "error": None, "source": "live", "cancel_requested_at": None,
               "deleted_at": None, "created_at": now(), "updated_at": now(), **conv}
        self.convs[row["id"]] = row
        self.msgs[row["id"]], self.evs[row["id"]], self.files[row["id"]] = [], [], {}
        return copy.deepcopy(row)

    def list(self, limit: int = 100) -> list[dict]:
        rows = [c for c in self.convs.values() if c["deleted_at"] is None]
        rows.sort(key=lambda c: c["updated_at"], reverse=True)
        return [{k: c[k] for k in ("id", "title", "status", "domain", "created_at", "updated_at")} for c in rows[:limit]]

    def get(self, cid: str) -> dict | None:
        c = self.convs.get(cid)
        return copy.deepcopy(c) if c and c["deleted_at"] is None else None

    def update(self, cid: str, **fields) -> None:
        self.convs[cid].update(fields, updated_at=now())

    def delete(self, cid: str) -> None:
        self.update(cid, deleted_at=now())

    def add_message(self, cid, role, kind, content, data=None, question_key=None) -> dict:
        with self._lock:
            m = {"id": self._next_msg, "conversation_id": cid, "role": role, "kind": kind, "content": content,
                 "data": data, "question_key": question_key, "created_at": now()}
            self._next_msg += 1
            self.msgs[cid].append(m)
            self.convs[cid]["updated_at"] = now()
        return copy.deepcopy(m)

    def messages(self, cid: str) -> list[dict]:
        return copy.deepcopy(self.msgs.get(cid, []))

    def find_answer(self, cid: str, key: str) -> dict | None:
        for m in reversed(self.msgs.get(cid, [])):
            if m["kind"] == "answer" and m["question_key"] == key:
                return copy.deepcopy(m)
        return None

    def append_event(self, cid: str, seq: int, event: dict) -> None:
        with self._lock:
            if all(e["seq"] != seq for e in self.evs[cid]):  # idempotent
                self.evs[cid].append({"seq": seq, **json.loads(json.dumps(event, default=str))})

    def events(self, cid: str, after: int = 0) -> list[dict]:
        return copy.deepcopy([e for e in sorted(self.evs.get(cid, []), key=lambda e: e["seq"]) if e["seq"] >= after])

    def save_result(self, cid: str, result: dict) -> None:
        self.results[cid] = json.loads(json.dumps(result, default=str))
        self.cands[cid] = candidate_rows(self.results[cid])

    def result(self, cid: str) -> dict | None:
        return copy.deepcopy(self.results.get(cid))

    def add_artifact(self, cid, name, kind, path, meta=None) -> None:
        self.files[cid][name] = {"name": name, "kind": kind, "path": path, "meta": meta}

    def artifacts(self, cid: str) -> list[dict]:
        return copy.deepcopy(list(self.files.get(cid, {}).values()))

    def active_research(self) -> dict | None:
        for c in self.convs.values():
            if c["status"] in ACTIVE and c["deleted_at"] is None and \
                    (now() - c["updated_at"]).total_seconds() < config.LIVE_RUN_TIMEOUT_S:
                return copy.deepcopy(c)
        return None

    def live_runs_used(self) -> int:
        return sum(1 for c in self.convs.values() if c["source"] == "live" and c["status"] != "answered")


class PostgresStore:
    """Supabase PostgreSQL (DATABASE_URL). One short connection per call: the API and the agent run in different
    containers, and Supabase's session pooler keeps the number of real connections low."""

    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or config.require_key("DATABASE_URL")

    def _conn(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self.dsn, row_factory=dict_row, autocommit=True, connect_timeout=15)

    @staticmethod
    def _j(x):
        from psycopg.types.json import Jsonb

        return None if x is None else Jsonb(json.loads(json.dumps(x, default=str)))

    def migrate(self) -> list[str]:
        """Apply the migrations not applied yet, in order; returns their names."""
        applied = []
        with self._conn() as c:
            c.execute("create schema if not exists autolab")
            c.execute("create table if not exists autolab.schema_migrations "
                      "(version text primary key, applied_at timestamptz not null default now())")
            done = {r["version"] for r in c.execute("select version from autolab.schema_migrations")}
            for f in sorted(MIGRATIONS.glob("*.sql")):
                if f.stem in done:
                    continue
                with c.transaction():
                    c.execute(f.read_text(encoding="utf-8"))
                    c.execute("insert into autolab.schema_migrations (version) values (%s)", (f.stem,))
                applied.append(f.stem)
        return applied

    def create(self, conv: dict) -> dict:
        cols = ["id", "title", "goal", "domain", "status", "scope", "source"]
        vals = [conv.get(k) if k != "scope" else self._j(conv.get("scope")) for k in cols]
        vals[cols.index("source")] = conv.get("source", "live")
        with self._conn() as c:
            return c.execute(f"insert into autolab.conversations ({', '.join(cols)}) values "
                             f"({', '.join(['%s'] * len(cols))}) returning *", vals).fetchone()

    def list(self, limit: int = 100) -> list[dict]:
        with self._conn() as c:
            return c.execute("select id, title, status, domain, created_at, updated_at from autolab.conversations "
                             "where deleted_at is null order by updated_at desc limit %s", (limit,)).fetchall()

    def get(self, cid: str) -> dict | None:
        with self._conn() as c:
            return c.execute("select * from autolab.conversations where id = %s and deleted_at is null",
                             (cid,)).fetchone()

    def update(self, cid: str, **fields) -> None:
        if not fields:
            return
        sets = ", ".join(f"{k} = %s" for k in fields)
        vals = [self._j(v) if k == "scope" else v for k, v in fields.items()]
        with self._conn() as c:
            c.execute(f"update autolab.conversations set {sets}, updated_at = now() where id = %s", (*vals, cid))

    def delete(self, cid: str) -> None:
        self.update(cid, deleted_at=now())

    def add_message(self, cid, role, kind, content, data=None, question_key=None) -> dict:
        with self._conn() as c:
            m = c.execute("insert into autolab.messages (conversation_id, role, kind, content, data, question_key) "
                          "values (%s, %s, %s, %s, %s, %s) returning *",
                          (cid, role, kind, content, self._j(data), question_key)).fetchone()
            c.execute("update autolab.conversations set updated_at = now() where id = %s", (cid,))
        return m

    def messages(self, cid: str) -> list[dict]:
        with self._conn() as c:
            return c.execute("select * from autolab.messages where conversation_id = %s order by id", (cid,)).fetchall()

    def find_answer(self, cid: str, key: str) -> dict | None:
        with self._conn() as c:
            return c.execute("select * from autolab.messages where conversation_id = %s and kind = 'answer' and "
                             "question_key = %s order by id desc limit 1", (cid, key)).fetchone()

    def append_event(self, cid: str, seq: int, event: dict) -> None:
        with self._conn() as c:
            c.execute("insert into autolab.events (conversation_id, seq, type, step, candidate_id, data, ts) values "
                      "(%s, %s, %s, %s, %s, %s, %s) on conflict do nothing",
                      (cid, seq, event["type"], event["step"], event.get("candidate_id"), self._j(event["data"]),
                       event["timestamp"]))

    def events(self, cid: str, after: int = 0) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("select seq, type, step, candidate_id, data, ts from autolab.events where "
                             "conversation_id = %s and seq >= %s order by seq", (cid, after)).fetchall()
        return [{"seq": r["seq"], "type": r["type"], "step": r["step"], "candidate_id": r["candidate_id"],
                 "data": r["data"], "timestamp": r["ts"].isoformat()} for r in rows]

    def save_result(self, cid: str, result: dict) -> None:
        rows = candidate_rows(json.loads(json.dumps(result, default=str)))
        with self._conn() as c, c.transaction():
            c.execute("insert into autolab.results (conversation_id, result) values (%s, %s) on conflict "
                      "(conversation_id) do update set result = excluded.result", (cid, self._j(result)))
            c.execute("delete from autolab.candidates where conversation_id = %s", (cid,))
            for r in rows:
                c.execute("insert into autolab.candidates (conversation_id, candidate_id, formula, parent, "
                          "substitution, status, excluded_at, e_hull, gap_optb88, d_ratio, md_verdict, novelty, data) "
                          "values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                          (cid, r["candidate_id"], r["formula"], r["parent"], self._j(r["substitution"]), r["status"],
                           r["excluded_at"], r["e_hull"], r["gap_optb88"], r["d_ratio"], r["md_verdict"], r["novelty"],
                           self._j(r["data"])))

    def result(self, cid: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("select result from autolab.results where conversation_id = %s", (cid,)).fetchone()
        return row["result"] if row else None

    def add_artifact(self, cid, name, kind, path, meta=None) -> None:
        with self._conn() as c:
            c.execute("insert into autolab.artifacts (conversation_id, name, kind, path, meta) values "
                      "(%s, %s, %s, %s, %s) on conflict (conversation_id, name) do update set path = excluded.path, "
                      "meta = excluded.meta", (cid, name, kind, path, self._j(meta)))

    def artifacts(self, cid: str) -> list[dict]:
        with self._conn() as c:
            return c.execute("select name, kind, path, meta from autolab.artifacts where conversation_id = %s "
                             "order by name", (cid,)).fetchall()

    def active_research(self) -> dict | None:
        with self._conn() as c:
            return c.execute("select * from autolab.conversations where status = any(%s) and deleted_at is null and "
                             "updated_at > now() - make_interval(secs => %s) order by created_at limit 1",
                             (list(ACTIVE), config.LIVE_RUN_TIMEOUT_S)).fetchone()

    def live_runs_used(self) -> int:
        with self._conn() as c:
            return c.execute("select count(*) as n from autolab.conversations where source = 'live' and "
                             "status <> 'answered'").fetchone()["n"]
