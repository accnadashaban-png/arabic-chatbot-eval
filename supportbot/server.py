"""HTTP server: an OpenAI-compatible endpoint, the embeddable chat widget and a demo page.

    python -m supportbot serve                     # http://127.0.0.1:8070
    POST /v1/chat/completions                      {"messages": [{"role": "user", "content": "..."}]}
    GET  /widget.js                                <script src=".../widget.js" data-api="https://..." defer></script>

Standard library only. Security for a public widget: only the sites in SB_ALLOWED_ORIGINS may call the API from a
browser (CORS), each visitor is rate limited, requests are size limited and personal data is masked in logs.
SB_API_KEY adds a bearer key for server-to-server use (a key in browser code would be public).

Admin API (header X-Admin-Key = SB_ADMIN_KEY; disabled when no key is set):
    GET /admin/entries · PUT /admin/entries/<id> · DELETE /admin/entries/<id> · GET /admin/insights?days=7 · GET /admin/llm
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from supportbot.bot import SupportBot
from supportbot.guard import redact
from supportbot.store import Store, StoreError

log = logging.getLogger("supportbot")
WEB = Path(__file__).with_name("web")
MAX_BODY = 64_000
MAX_MESSAGES = 40
ENTRY_PATH = re.compile(r"^/admin/entries/([A-Za-z0-9_-]{1,40})$")


class RateLimiter:
    """At most `limit` requests per client in any 60-second window."""

    def __init__(self, limit: int):
        self.limit = limit
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, client: str) -> bool:
        if self.limit <= 0:
            return True
        now = time.monotonic()
        with self.lock:
            q = self.hits[client]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


def make_handler(bot: SupportBot, api_key: str = "", allowed_origins: tuple[str, ...] = (),
                 per_minute: int = 30, admin_key: str = "") -> type[BaseHTTPRequestHandler]:
    limiter = RateLimiter(per_minute)

    class Handler(BaseHTTPRequestHandler):
        server_version = "supportbot"

        def log_message(self, fmt: str, *args: Any) -> None:  # no raw request lines in logs
            return

        def _cors(self) -> None:
            origin = self.headers.get("Origin", "")
            if origin and origin in allowed_origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")

        def _send(self, status: int, body: bytes, kind: str = "application/json", cache: str = "no-store") -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self._cors()
            if kind.startswith("text/html"):
                self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                                 "script-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, data: dict[str, Any]) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"))

        def _admin(self) -> bool:
            """True if this is an authorised admin call; otherwise the error response is already sent."""
            if not admin_key:
                self._json(403, {"error": "the admin API is off: set SB_ADMIN_KEY"})
                return False
            if not hmac.compare_digest(self.headers.get("X-Admin-Key", ""), admin_key):
                self._json(401, {"error": "invalid admin key"})
                return False
            if not bot.store:
                self._json(409, {"error": "the bot is not connected to a database"})
                return False
            return True

        def _body(self) -> Any:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise StoreError("request too large")
            return json.loads(self.rfile.read(length) or b"{}")

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if path.startswith("/admin/"):
                if not self._admin():
                    return
                store = bot.store
                assert store is not None
                if path == "/admin/entries":
                    return self._json(200, {"entries": [{"id": e.id, "topic": e.topic, "concepts": sorted(e.concepts),
                                                         "questions": list(e.questions),
                                                         **{f"answer_{k}": v for k, v in e.answer.items()}}
                                                        for e in store.entries()]})
                if path == "/admin/insights":
                    days = int((parse_qs(urlsplit(self.path).query).get("days") or ["7"])[0] or 7)
                    return self._json(200, store.insights(max(1, min(days, 365))))
                if path == "/admin/llm":
                    return self._json(200, {"providers": bot.llm.status() if bot.llm else []})
                return self._json(404, {"error": "not found"})
            if self.path in ("/", "/index.html"):
                self._send(200, (WEB / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/widget.js":
                self._send(200, (WEB / "widget.js").read_bytes(), "text/javascript; charset=utf-8", "public, max-age=300")
            elif self.path == "/health":
                self._json(200, {"status": "ok", "entries": len(bot.entries), "llm": bool(bot.llm)})
            else:
                self._json(404, {"error": "not found"})

        def do_PUT(self) -> None:  # noqa: N802
            m = ENTRY_PATH.match(urlsplit(self.path).path)
            if not m:
                return self._json(404, {"error": "not found"})
            if not self._admin():
                return
            try:
                entry = bot.store.upsert_entry({**self._body(), "id": m.group(1)})  # type: ignore[union-attr]
            except (StoreError, ValueError, TypeError) as exc:
                return self._json(422, {"error": str(exc) if isinstance(exc, StoreError) else "send a JSON object"})
            bot.refresh(force=True)
            self._json(200, {"id": entry.id, "topic": entry.topic, "live": True})

        def do_DELETE(self) -> None:  # noqa: N802
            m = ENTRY_PATH.match(urlsplit(self.path).path)
            if not m:
                return self._json(404, {"error": "not found"})
            if not self._admin():
                return
            if not bot.store.deactivate(m.group(1)):  # type: ignore[union-attr]
                return self._json(404, {"error": "no active entry with that id"})
            bot.refresh(force=True)
            self._json(200, {"id": m.group(1), "active": False})

        def do_OPTIONS(self) -> None:  # noqa: N802 - CORS preflight from allowed sites
            if self.path != "/v1/chat/completions" or self.headers.get("Origin", "") not in allowed_origins:
                return self._json(403, {"error": "origin not allowed"})
            self.send_response(204)
            self._cors()
            self.send_header("Access-Control-Allow-Methods", "POST")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Max-Age", "600")
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/chat/completions":
                return self._json(404, {"error": "not found"})
            if api_key and not hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {api_key}"):
                return self._json(401, {"error": "invalid API key"})
            if not limiter.allow(self.client_address[0]):
                return self._json(429, {"error": "too many messages, please wait a minute"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                self.close_connection = True
                if length <= 16 * MAX_BODY:  # drain a moderately large body so the client reads a clean 413
                    self.rfile.read(length)
                return self._json(413, {"error": "request too large"})
            try:
                messages = json.loads(self.rfile.read(length) or b"{}")["messages"][-MAX_MESSAGES:]
                turns = [{"role": str(m["role"]), "content": str(m["content"])[:2000]} for m in messages
                         if m.get("role") in ("user", "assistant")]
                question = turns[-1]["content"]
                if turns[-1]["role"] != "user":
                    raise ValueError
            except (ValueError, KeyError, TypeError, IndexError):
                return self._json(400, {"error": "send messages ending with a user message"})
            start = time.perf_counter()
            reply = bot.respond(question, turns[:-1])
            log.info("%s -> %s (%s) in %.0f ms", redact(question)[:120], reply.topic or reply.behavior, reply.mode,
                     (time.perf_counter() - start) * 1000)
            if bot.store:
                bot.store.log(question, reply.language, reply.topic, reply.behavior, reply.confidence, reply.mode,
                              self.headers.get("X-Session", ""))
            self._json(200, {"id": f"sb-{int(time.time() * 1000)}", "object": "chat.completion", "model": bot.name,
                             "choices": [{"index": 0, "finish_reason": "stop",
                                          "message": {"role": "assistant", "content": reply.text}}],
                             "supportbot": {k: v for k, v in reply.to_dict().items() if k != "text"}})
    return Handler


def serve(host: str = "127.0.0.1", port: int = 8070, kb_dir: str | None = None, db_url: str | None = None) -> None:
    from supportbot.knowledge import DEMO_KB
    from supportbot.llm import Router

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    store = Store(db_url or os.environ.get("SB_DATABASE_URL", "sqlite:///supportbot.db"))
    added = store.seed(Path(kb_dir) if kb_dir else DEMO_KB)
    if added:
        print(f"New database: loaded {added} knowledge-base entries.")
    bot = SupportBot(kb_dir, llm=Router.from_env(), store=store)
    origins = tuple(o.strip().rstrip("/") for o in os.environ.get("SB_ALLOWED_ORIGINS", "").split(",") if o.strip())
    handler = make_handler(bot, os.environ.get("SB_API_KEY", ""), origins, int(os.environ.get("SB_RATE_PER_MINUTE", "30")),
                           os.environ.get("SB_ADMIN_KEY", ""))
    httpd = ThreadingHTTPServer((host, port), handler)
    print(f"Support bot on http://{host}:{port} ({len(bot.entries)} entries in {store.url.split('@')[-1]}, "
          f"{'LLM + ' if bot.llm else ''}knowledge-base answers). Ctrl+C to stop.")
    httpd.serve_forever()
