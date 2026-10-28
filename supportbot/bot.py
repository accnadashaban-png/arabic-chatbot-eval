"""The support bot: guard, retrieve, decide, answer, verify.

    message -> guard (attacks are refused)
            -> retrieval over the knowledge base (dialect lexicon + BM25)
            -> follow-up resolution (a short "and the yearly one?" is read with the previous message)
            -> policy (answer, hand off to people, refuse, or ask to clarify when unsure)
            -> answer from the knowledge base, or an LLM answer that passed the grounding checks
"""
from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from supportbot.arabic import reply_language, stems
from supportbot.guard import is_attack, redact
from supportbot.knowledge import DEMO_KB, LEXICON, SECONDARY, STOPWORDS, Hit, Index, Lexicon, load_entries, load_policies
from supportbot.llm import ProviderError, Router, build_messages, grounded

log = logging.getLogger("supportbot")
FOLLOW_UP_MAX_WORDS = 4


@dataclass
class Reply:
    text: str
    behavior: str                 # answer, handoff, refuse, clarify
    language: str
    topic: str = ""
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.0
    mode: str = "kb"              # kb, llm, guard, clarify
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class SupportBot:
    def __init__(self, kb_dir: str | Path | None = None, llm: Router | None = None, canary: str | None = None):
        folder = Path(kb_dir or os.environ.get("SB_KB_DIR") or DEMO_KB)
        self.entries = load_entries(folder)
        self.policies = load_policies(folder)
        self.index = Index(self.entries, Lexicon.load(LEXICON, folder / "lexicon.csv"))  # shared + the company's own words
        self.llm = llm
        self.canary = canary or f"SB-{secrets.token_hex(4)}"
        self.name = "support-bot" + ("+llm" if llm else "")

    # ----- decisions -----

    def _confident(self, hit: Hit | None) -> bool:
        if not hit or hit.margin < self.policies["min_margin"]:
            return False
        return hit.score >= (self.policies["min_score"] if hit.anchored else self.policies["min_score_words_only"])

    def _retrieve(self, message: str, history: list[dict[str, str]]) -> tuple[Hit | None, bool]:
        hit = self.index.search(message)
        previous = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")
        short = len([s for s in stems(message) if s not in STOPWORDS]) <= FOLLOW_UP_MAX_WORDS
        names_a_topic = bool(hit and hit.concepts - SECONDARY)
        if self._confident(hit) and (names_a_topic or not (previous and short)):
            return hit, False
        if previous and short:  # "والسنوي؟", "وبتظهر فين؟": read together with the last question
            if is_attack(f"{previous} {message}"):  # an attack split over two messages
                return None, False
            combined = self.index.search(f"{previous} {message}")
            if self._confident(combined):
                return combined, True
        return hit, False

    def respond(self, message: str, history: list[dict[str, str]] | None = None) -> Reply:
        history = history or []
        lang = reply_language(message)
        msgs = self.policies["messages"]
        if is_attack(message):
            log.info("refused an attack: %s", redact(message)[:200])
            return Reply(msgs["refuse_attack"][lang], "refuse", lang, "security", mode="guard")
        hit, follow_up = self._retrieve(message, history)
        if not self._confident(hit) or hit is None:
            return Reply(msgs["clarify"][lang], "clarify", lang, mode="clarify", confidence=round(hit.score, 2) if hit else 0.0)
        e = hit.entry
        behavior = ("handoff" if e.topic in self.policies["handoff_topics"]
                    else "refuse" if e.topic in self.policies["refuse_topics"] else "answer")
        reply = Reply(e.answer[lang], behavior, lang, e.topic, [e.id], round(hit.score, 2),
                      notes=["read with the previous message"] if follow_up else [])
        if self.llm and behavior == "answer":
            self._llm_answer(reply, message, history, e)
        return reply

    def _llm_answer(self, reply: Reply, message: str, history: list[dict[str, str]], entry: Any) -> None:
        sources = [entry, *[x for x in self.entries if x.topic == entry.topic and x.id != entry.id]]
        try:
            text, provider = self.llm.complete(build_messages(message, history, sources, reply.language,  # type: ignore[union-attr]
                                                              self.policies.get("business", "the company"), self.canary))
        except ProviderError as exc:
            reply.notes.append(f"LLM unavailable, answered from the knowledge base ({exc})")
            return
        ok, why = grounded(text, sources, reply.language, self.canary)
        if ok:
            reply.text, reply.mode = text.strip(), "llm"
            reply.notes.append(f"written by {provider}, grounded")
        else:
            reply.notes.append(f"LLM answer rejected ({why}), answered from the knowledge base")

    # ----- evaluator protocol -----

    def ask(self, question: str, history: list[dict[str, str]] | None = None) -> str:
        return self.respond(question, history).text
