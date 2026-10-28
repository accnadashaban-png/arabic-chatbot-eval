"""python -m supportbot serve [--port 8070] [--kb folder]   |   python -m supportbot ask "سؤالك" """
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
    s.add_argument("--kb", help="your knowledge-base folder (faq.csv + policies.json)")
    a = sub.add_parser("ask", help="ask one question and show how it was answered")
    a.add_argument("question")
    a.add_argument("--kb")
    args = p.parse_args(argv)
    if args.cmd == "serve":
        from supportbot.server import serve
        serve(args.host, args.port, args.kb)
        return 0
    from supportbot.bot import SupportBot
    reply = SupportBot(args.kb).respond(args.question)
    print(json.dumps(reply.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
