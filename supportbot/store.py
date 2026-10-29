"""The bot's live database: knowledge base, settings and a conversation log, in SQLite or PostgreSQL.

    SB_DATABASE_URL=sqlite:///supportbot.db                    (default, no setup)
    SB_DATABASE_URL=postgresql://user:pass@host:5432/support    (needs `pip install -e .[postgres]`)

The bot watches the knowledge base: an entry added or changed here (by the admin API, a script or another system)
is answered with a few seconds later, without a restart.

People, chats and messages are stored like a support inbox: each visitor (an anonymous id from the widget, or your own
user id), each of their chats, and every exchange with what the bot did (answered, handed off, refused, asked to
clarify). Questions are stored with emails, card numbers and phone numbers masked, and a person's data can be erased.
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
from supportbot.knowledge import Entry, load_entries, load_policies, make_entry

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS kb_entries (
        id TEXT PRIMARY KEY, topic TEXT NOT NULL, concepts TEXT NOT NULL DEFAULT '', questions TEXT NOT NULL DEFAULT '',
        answer_ar TEXT NOT NULL, answer_en TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL)""",
    "CREATE TABLE IF NOT EXISTS kb_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)",
    """CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '', language TEXT NOT NULL DEFAULT '',
        first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, chats INTEGER NOT NULL DEFAULT 0, messages INTEGER NOT NULL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS chats (
        id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users (id), started_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        title TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'open', turns INTEGER NOT NULL DEFAULT 0,
        last_topic TEXT NOT NULL DEFAULT '')""",
    """CREATE TABLE IF NOT EXISTS turns (
        id {serial}, chat_id TEXT NOT NULL REFERENCES chats (id), user_id TEXT NOT NULL, at TEXT NOT NULL,
        question TEXT NOT NULL, answer TEXT NOT NULL, language TEXT NOT NULL, topic TEXT NOT NULL DEFAULT '',
        behavior TEXT NOT NULL, confidence REAL NOT NULL DEFAULT 0, mode TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_turns_at ON turns (at)",
    "CREATE INDEX IF NOT EXISTS idx_turns_chat ON turns (chat_id)",
    "CREATE INDEX IF NOT EXISTS idx_chats_user ON chats (user_id, updated_at)",
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
            self.upsert_entry({"id": e.id, "topic": e.topic, "concepts": e.concept_text,
                               "questions": list(e.questions), "answer_ar": e.answer["ar"], "answer_en": e.answer["en"]})
        if not self._run("SELECT 1 FROM kb_settings WHERE key = 'policies'"):
            self.set_policies(load_policies(folder))
        return len(self.entries())

    def import_folder(self, folder: Path) -> dict[str, int]:
        """Add or update every entry of a faq.csv folder (and its policies) in a database that is already in use.
        People, chats and entries that are not in the file are kept."""
        before = {e.id: e for e in self.entries()}
        added = updated = 0
        for e in load_entries(folder):
            old = before.get(e.id)
            if old != e:
                self.upsert_entry({"id": e.id, "topic": e.topic, "concepts": e.concept_text, "questions": list(e.questions),
                                   "answer_ar": e.answer["ar"], "answer_en": e.answer["en"]})
                added, updated = (added + 1, updated) if old is None else (added, updated + 1)
        if (folder / "policies.json").exists():
            self.set_policies(load_policies(folder))
        return {"added": added, "updated": updated, "entries": len(self.entries())}

    def upsert_entry(self, data: dict[str, Any]) -> Entry:
        missing = [f for f in REQUIRED if not str(data.get(f) or "").strip()]
        if missing:
            raise StoreError(f"missing: {', '.join(missing)}")
        questions = data.get("questions") or []
        if isinstance(questions, str):
            questions = [q for q in questions.split("|") if q.strip()]
        concepts = data.get("concepts") or ""
        if isinstance(concepts, list):  # the admin API returns concepts as a list; accept it back
            concepts = " ".join(str(c) for c in concepts)
        row = (str(data["id"]).strip()[:40], str(data["topic"]).strip()[:60], " ".join(str(concepts).split())[:300],
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
        return [make_entry(*r) for r in rows]

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

    # ----- people, chats and messages -----

    def record(self, user_id: str, chat_id: str, question: str, answer: str, language: str, topic: str, behavior: str,
               confidence: float, mode: str) -> None:
        """Store one exchange. The visitor and the chat are created on first sight. The question is stored with emails,
        card numbers and phone numbers masked; no IP addresses are kept."""
        now, q = _now(), redact(question)[:1000]
        self._run("""INSERT INTO users (id, language, first_seen, last_seen, chats, messages) VALUES (?, ?, ?, ?, 0, 0)
                     ON CONFLICT (id) DO UPDATE SET last_seen = excluded.last_seen, language = excluded.language""",
                  (user_id, language, now, now))
        new_chat = not self._run("SELECT 1 FROM chats WHERE id = ?", (chat_id,))
        if new_chat:
            self._run("""INSERT INTO chats (id, user_id, started_at, updated_at, title, status, turns, last_topic)
                         VALUES (?, ?, ?, ?, ?, 'open', 0, '')""", (chat_id, user_id, now, now, q[:80]))
        status = "handed_off" if behavior == "handoff" else None
        self._run("""UPDATE chats SET updated_at = ?, turns = turns + 1, last_topic = CASE WHEN ? = '' THEN last_topic ELSE ? END,
                     status = COALESCE(?, status) WHERE id = ?""", (now, topic, topic, status, chat_id))
        self._run("UPDATE users SET messages = messages + 1, chats = chats + ? WHERE id = ?", (1 if new_chat else 0, user_id))
        self._run("""INSERT INTO turns (chat_id, user_id, at, question, answer, language, topic, behavior, confidence, mode)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (chat_id, user_id, now, q, answer[:4000], language, topic, behavior, float(confidence), mode))

    def chat_owner(self, chat_id: str) -> str | None:
        rows = self._run("SELECT user_id FROM chats WHERE id = ?", (chat_id,))
        return str(rows[0][0]) if rows else None

    def transcript(self, chat_id: str) -> list[dict[str, Any]]:
        rows = self._run("""SELECT at, question, answer, language, topic, behavior, confidence, mode FROM turns
                            WHERE chat_id = ? ORDER BY id""", (chat_id,))
        keys = ("at", "question", "answer", "language", "topic", "behavior", "confidence", "mode")
        return [dict(zip(keys, r, strict=True)) for r in rows]

    def users(self, search: str = "", limit: int = 50) -> list[dict[str, Any]]:
        rows = self._run("""SELECT id, name, email, language, first_seen, last_seen, chats, messages FROM users
                            WHERE id LIKE ? OR name LIKE ? OR email LIKE ? ORDER BY last_seen DESC LIMIT ?""",
                         (f"%{search}%", f"%{search}%", f"%{search}%", max(1, min(limit, 500))))
        keys = ("id", "name", "email", "language", "first_seen", "last_seen", "chats", "messages")
        return [dict(zip(keys, r, strict=True)) for r in rows]

    def chats(self, user_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        where, params = ("WHERE user_id = ?", (user_id,)) if user_id else ("", ())
        rows = self._run(f"""SELECT id, user_id, started_at, updated_at, title, status, turns, last_topic FROM chats {where}
                             ORDER BY updated_at DESC LIMIT ?""", (*params, max(1, min(limit, 500))))
        keys = ("id", "user_id", "started_at", "updated_at", "title", "status", "turns", "last_topic")
        return [dict(zip(keys, r, strict=True)) for r in rows]

    def set_profile(self, user_id: str, name: str | None = None, email: str | None = None) -> bool:
        """Name and email are optional, for businesses that know who is chatting (a logged-in app, a CRM)."""
        if not self._run("SELECT 1 FROM users WHERE id = ?", (user_id,)):
            return False
        if name is not None:
            self._run("UPDATE users SET name = ? WHERE id = ?", (name.strip()[:120], user_id))
        if email is not None:
            self._run("UPDATE users SET email = ? WHERE id = ?", (email.strip()[:200], user_id))
        return True

    def forget_user(self, user_id: str) -> dict[str, int]:
        """Delete a person and everything they said, for data-deletion requests. Cannot be undone."""
        counts = {"turns": self._run("SELECT COUNT(*) FROM turns WHERE user_id = ?", (user_id,))[0][0],
                  "chats": self._run("SELECT COUNT(*) FROM chats WHERE user_id = ?", (user_id,))[0][0],
                  "users": self._run("SELECT COUNT(*) FROM users WHERE id = ?", (user_id,))[0][0]}
        self._run("DELETE FROM turns WHERE user_id = ?", (user_id,))
        self._run("DELETE FROM chats WHERE user_id = ?", (user_id,))
        self._run("DELETE FROM users WHERE id = ?", (user_id,))
        return {k: int(v) for k, v in counts.items()}

    def insights(self, days: int = 7) -> dict[str, Any]:
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
        rows = self._run("SELECT question, topic, behavior, mode, language, user_id, chat_id, at FROM turns WHERE at >= ?", (since,))
        total = len(rows)
        by = lambda i: dict(sorted(((k, sum(1 for r in rows if r[i] == k)) for k in {r[i] for r in rows}), key=lambda x: -x[1]))  # noqa: E731
        unanswered: dict[str, list[str]] = {}
        for r in rows:
            if r[2] == "clarify":
                unanswered.setdefault(fold(r[0]).strip(" ?؟."), []).append(r[0])
        gaps = sorted(unanswered.values(), key=len, reverse=True)[:10]
        chats = {r[6] for r in rows}
        per_day: dict[str, int] = {}
        for r in rows:
            per_day[str(r[7])[:10]] = per_day.get(str(r[7])[:10], 0) + 1
        return {"days": days, "messages": total, "people": len({r[5] for r in rows}), "chats": len(chats),
                "messages_per_chat": round(total / len(chats), 2) if chats else None,
                "answered_rate": round(sum(1 for r in rows if r[2] == "answer") / total, 3) if total else None,
                "handed_off": sum(1 for r in rows if r[2] == "handoff"), "asked_to_clarify": sum(1 for r in rows if r[2] == "clarify"),
                "by_behavior": by(2), "by_topic": by(1), "by_mode": by(3), "by_language": by(4),
                "per_day": dict(sorted(per_day.items())),
                "content_gaps": [{"question": g[0], "times": len(g)} for g in gaps]}
