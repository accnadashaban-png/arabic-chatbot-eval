"""The bot's live database: knowledge base, settings and a conversation log, in SQLite or PostgreSQL.

    SB_DATABASE_URL=sqlite:///supportbot.db                    (default, no setup)
    SB_DATABASE_URL=postgresql://user:pass@host:5432/support    (needs `pip install -e .[postgres]`)

The bot watches the knowledge base: an entry added or changed here (by the admin API, a script or another system)
is answered with a few seconds later, without a restart. Conversations are stored with personal data masked, so the
team can see what people ask and what the bot could not answer.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from supportbot.arabic import fold
from supportbot.guard import redact
from supportbot.knowledge import Entry, load_entries, load_policies

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS kb_entries (
        id TEXT PRIMARY KEY, topic TEXT NOT NULL, concepts TEXT NOT NULL DEFAULT '', questions TEXT NOT NULL DEFAULT '',
        answer_ar TEXT NOT NULL, answer_en TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL)""",
    "CREATE TABLE IF NOT EXISTS kb_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)",
    """CREATE TABLE IF NOT EXISTS conversations (
        id {serial}, at TEXT NOT NULL, session TEXT NOT NULL DEFAULT '', question TEXT NOT NULL, language TEXT NOT NULL,
        topic TEXT NOT NULL DEFAULT '', behavior TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 0, mode TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_conversations_at ON conversations (at)",
]
REQUIRED = ("id", "topic", "answer_ar", "answer_en")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


class StoreError(ValueError):
    pass


class Store:
    def __init__(self, url: str = "sqlite:///supportbot.db"):
        self.url = url
        self.lock = threading.Lock()
        if url.startswith(("postgresql://", "postgres://")):
            import psycopg  # optional dependency

            self.con: Any = psycopg.connect(url, autocommit=True)
            self.mark, serial = "%s", "BIGSERIAL PRIMARY KEY"
        elif url.startswith("sqlite:///"):
            path = url.removeprefix("sqlite:///")
            if path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            self.con = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
            self.con.execute("PRAGMA journal_mode=WAL")
            self.mark, serial = "?", "INTEGER PRIMARY KEY AUTOINCREMENT"
        else:
            raise StoreError("use sqlite:///path.db or postgresql://...")
        for statement in SCHEMA:
            self._run(statement.replace("{serial}", serial))

    # ----- low level -----

    def _run(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        sql = sql.replace("?", self.mark)
        with self.lock:
            cur = self.con.execute(sql, params)
            return list(cur.fetchall()) if cur.description else []

    # ----- knowledge base -----

    def seed(self, folder: Path) -> int:
        """Load a faq.csv / policies.json folder into an empty database. Returns how many entries were added."""
        if self._run("SELECT COUNT(*) FROM kb_entries")[0][0]:
            return 0
        for e in load_entries(folder):
            self.upsert_entry({"id": e.id, "topic": e.topic, "concepts": " ".join(sorted(e.concepts)),
                               "questions": list(e.questions), "answer_ar": e.answer["ar"], "answer_en": e.answer["en"]})
        if not self._run("SELECT 1 FROM kb_settings WHERE key = 'policies'"):
            self.set_policies(load_policies(folder))
        return len(self.entries())

    def upsert_entry(self, data: dict[str, Any]) -> Entry:
        missing = [f for f in REQUIRED if not str(data.get(f) or "").strip()]
        if missing:
            raise StoreError(f"missing: {', '.join(missing)}")
        questions = data.get("questions") or []
        if isinstance(questions, str):
            questions = [q for q in questions.split("|") if q.strip()]
        row = (str(data["id"]).strip()[:40], str(data["topic"]).strip()[:60], " ".join(str(data.get("concepts") or "").split())[:300],
               "|".join(q.strip()[:300] for q in questions[:20]), str(data["answer_ar"]).strip()[:2000],
               str(data["answer_en"]).strip()[:2000], _now())
        self._run("""INSERT INTO kb_entries (id, topic, concepts, questions, answer_ar, answer_en, active, updated_at)
                     VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                     ON CONFLICT (id) DO UPDATE SET topic = excluded.topic, concepts = excluded.concepts,
                     questions = excluded.questions, answer_ar = excluded.answer_ar, answer_en = excluded.answer_en,
                     active = 1, updated_at = excluded.updated_at""", row)
        return next(e for e in self.entries() if e.id == row[0])

    def deactivate(self, entry_id: str) -> bool:
        """Entries are switched off, not deleted, so past conversations still make sense."""
        found = self._run("SELECT 1 FROM kb_entries WHERE id = ? AND active = 1", (entry_id,))
        if found:
            self._run("UPDATE kb_entries SET active = 0, updated_at = ? WHERE id = ?", (_now(), entry_id))
        return bool(found)

    def entries(self) -> list[Entry]:
        rows = self._run("SELECT id, topic, concepts, questions, answer_ar, answer_en FROM kb_entries WHERE active = 1 ORDER BY id")
        return [Entry(r[0], r[1], frozenset(r[2].split()), tuple(q for q in r[3].split("|") if q), {"ar": r[4], "en": r[5]})
                for r in rows]

    def policies(self) -> dict[str, Any]:
        rows = self._run("SELECT value FROM kb_settings WHERE key = 'policies'")
        if not rows:
            raise StoreError("no policies yet: run `python -m supportbot init-db`")
        return dict(json.loads(rows[0][0]))

    def set_policies(self, policies: dict[str, Any]) -> None:
        self._run("""INSERT INTO kb_settings (key, value, updated_at) VALUES ('policies', ?, ?)
                     ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
                  (json.dumps(policies, ensure_ascii=False), _now()))

    def version(self) -> str:
        """Changes whenever an entry or a setting changes; cheap enough to check before every answer."""
        a = self._run("SELECT COUNT(*), MAX(updated_at) FROM kb_entries")[0]
        b = self._run("SELECT MAX(updated_at) FROM kb_settings")[0]
        return f"{a[0]}|{a[1]}|{b[0]}"

    # ----- conversation log and insights -----

    def log(self, question: str, language: str, topic: str, behavior: str, confidence: float, mode: str, session: str = "") -> None:
        """Questions are stored with emails, card numbers and phone numbers masked; no IP addresses are kept."""
        self._run("""INSERT INTO conversations (at, session, question, language, topic, behavior, confidence, mode)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (_now(), session[:64], redact(question)[:500], language, topic, behavior, float(confidence), mode))

    def insights(self, days: int = 7) -> dict[str, Any]:
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        rows = self._run("SELECT question, topic, behavior, mode FROM conversations WHERE at >= ?", (since,))
        total = len(rows)
        by = lambda i: dict(sorted(((k, sum(1 for r in rows if r[i] == k)) for k in {r[i] for r in rows}), key=lambda x: -x[1]))  # noqa: E731
        unanswered: dict[str, list[str]] = {}
        for q, _, behavior, _ in rows:
            if behavior == "clarify":
                unanswered.setdefault(fold(q).strip(" ?؟."), []).append(q)
        gaps = sorted(unanswered.values(), key=len, reverse=True)[:10]
        return {"days": days, "conversations": total,
                "answered_rate": round(sum(1 for r in rows if r[2] == "answer") / total, 3) if total else None,
                "handed_off": sum(1 for r in rows if r[2] == "handoff"), "asked_to_clarify": sum(1 for r in rows if r[2] == "clarify"),
                "by_behavior": by(2), "by_topic": by(1), "by_mode": by(3),
                "content_gaps": [{"question": g[0], "times": len(g)} for g in gaps]}
