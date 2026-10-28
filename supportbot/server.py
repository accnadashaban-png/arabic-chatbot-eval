"""HTTP server: an OpenAI-compatible endpoint any client (or the evaluator) can call, plus a chat page.

    python -m supportbot serve                     # http://127.0.0.1:8070
    POST /v1/chat/completions                      {"messages": [{"role": "user", "content": "..."}]}

Standard library only. Optional bearer key (SB_API_KEY), request size limit, personal data redacted in logs.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from supportbot.bot import SupportBot
from supportbot.guard import redact

log = logging.getLogger("supportbot")
PAGE = Path(__file__).with_name("web") / "chat.html"
MAX_BODY = 64_000
MAX_MESSAGES = 40


def make_handler(bot: SupportBot, api_key: str = "") -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "supportbot"

        def log_message(self, fmt: str, *args: Any) -> None:  # no raw request lines in logs
            return

        def _send(self, status: int, body: bytes, kind: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if kind.startswith("text/html"):
                self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                                 "script-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, data: dict[str, Any]) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"))

        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/health":
                self._json(200, {"status": "ok", "entries": len(bot.entries), "llm": bool(bot.llm)})
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/v1/chat/completions":
                return self._json(404, {"error": "not found"})
            if api_key and not hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {api_key}"):
                return self._json(401, {"error": "invalid API key"})
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
            self._json(200, {"id": f"sb-{int(time.time() * 1000)}", "object": "chat.completion", "model": bot.name,
                             "choices": [{"index": 0, "finish_reason": "stop",
                                          "message": {"role": "assistant", "content": reply.text}}],
                             "supportbot": {k: v for k, v in reply.to_dict().items() if k != "text"}})
    return Handler


def serve(host: str = "127.0.0.1", port: int = 8070, kb_dir: str | None = None) -> None:
    from supportbot.llm import Router

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    bot = SupportBot(kb_dir, llm=Router.from_env())
    httpd = ThreadingHTTPServer((host, port), make_handler(bot, os.environ.get("SB_API_KEY", "")))
    print(f"Support bot on http://{host}:{port} ({len(bot.entries)} knowledge-base entries, "
          f"{'LLM + ' if bot.llm else ''}knowledge-base answers). Ctrl+C to stop.")
    httpd.serve_forever()
