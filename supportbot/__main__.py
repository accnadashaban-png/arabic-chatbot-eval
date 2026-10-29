"""python -m supportbot serve [--port 8070] [--db url] [--kb folder]   |   python -m supportbot ask "سؤالك"
python -m supportbot import --kb my_kb [--db url]   # add or update your knowledge base in a database already in use"""
from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="supportbot")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="run the HTTP endpoint and chat page")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8070)
    s.add_argument("--kb", help="a knowledge-base folder (faq.csv + policies.json) to load into a new database")
    s.add_argument("--db", help="sqlite:///file.db or postgresql://... (default: SB_DATABASE_URL or sqlite:///supportbot.db)")
    i = sub.add_parser("import", help="add or update entries from a faq.csv folder; people and chats are kept")
    i.add_argument("--kb", required=True)
    i.add_argument("--db", help="default: SB_DATABASE_URL or sqlite:///supportbot.db")
    a = sub.add_parser("ask", help="ask one question and show how it was answered")
    a.add_argument("question")
    a.add_argument("--kb")
    args = p.parse_args(argv)
    if args.cmd == "serve":
        from supportbot.server import serve
        serve(args.host, args.port, args.kb, args.db)
        return 0
    if args.cmd == "import":
        import os
        from pathlib import Path

        from supportbot.store import Store
        store = Store(args.db or os.environ.get("SB_DATABASE_URL") or "sqlite:///supportbot.db")
        print(json.dumps(store.import_folder(Path(args.kb)), indent=2))
        return 0
    from supportbot.bot import SupportBot
    reply = SupportBot(args.kb).respond(args.question)
    print(json.dumps(reply.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
