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
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from supportbot.arabic import fold, reply_language, stems, tokens
from supportbot.guard import is_attack, redact
from supportbot.knowledge import DEMO_KB, LEXICON, SECONDARY, STOPWORDS, Hit, Index, Lexicon, load_entries, load_policies
from supportbot.llm import ProviderError, Router, build_messages, grounded
from supportbot.store import Store

log = logging.getLogger("supportbot")
FOLLOW_UP_MAX_WORDS = 4
GREETING = {"ar": "أهلًا بك! كيف أقدر أساعدك؟ أستطيع المساعدة في الاشتراك والدفع والدورات وحسابك.",
            "en": "Hi! How can I help? I can help with your subscription, payments, courses and account."}
GREETING_WORDS = frozenset(fold(w) for w in [
    "hi", "hello", "hey", "hiya", "hola", "salam", "ahlan", "marhaba", "good", "morning", "evening", "afternoon", "there",
    "السلام", "عليكم", "سلام", "اهلا", "اهلين", "مرحبا", "مرحبتين", "هاي", "هلا", "يا", "صباح", "مساء", "الخير", "النور",
    "الفل", "كيفك", "ازيك", "عامل", "ايه", "شلونك",
])


def is_greeting(message: str) -> bool:
    """A message made only of greeting words (and punctuation)."""
    words = tokens(message)
    return bool(words) and len(words) <= 6 and all(w in GREETING_WORDS for w in words)


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
    """Answers from a knowledge-base folder, or from a live database (`store`) that it re-reads when it changes."""

    def __init__(self, kb_dir: str | Path | None = None, llm: Router | None = None, canary: str | None = None,
                 store: Store | None = None, refresh_s: float = 2.0):
        self.folder = Path(kb_dir or os.environ.get("SB_KB_DIR") or DEMO_KB)
        self.store, self.refresh_s = store, refresh_s
        self.lexicon = Lexicon.load(LEXICON, self.folder / "lexicon.csv")  # shared + the company's own words
        self._version, self._checked = "", 0.0
        self._reload_lock = threading.Lock()
        self._load()
        self.llm = llm
        self.canary = canary or f"SB-{secrets.token_hex(4)}"
        self.name = "support-bot" + ("+llm" if llm else "")

    def _load(self) -> None:
        if self.store:
            entries, policies, self._version = self.store.entries(), self.store.policies(), self.store.version()
        else:
            entries, policies = load_entries(self.folder), load_policies(self.folder)
        self.entries, self.policies, self.index = entries, policies, Index(entries, self.lexicon)

    def refresh(self, force: bool = False) -> bool:
        """Re-read the database if its contents changed (checked at most every `refresh_s` seconds)."""
        if not self.store or (not force and time.monotonic() - self._checked < self.refresh_s):
            return False
        with self._reload_lock:
            self._checked = time.monotonic()
            if self.store.version() == self._version:
                return False
            self._load()
            log.info("knowledge base reloaded: %d entries", len(self.entries))
            return True

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
        self.refresh()
        lang = reply_language(message)
        msgs = self.policies["messages"]
        if is_attack(message):
            log.info("refused an attack: %s", redact(message)[:200])
            return Reply(msgs["refuse_attack"][lang], "refuse", lang, "security", mode="guard")
        if is_greeting(message):  # "hi", "السلام عليكم": greet back instead of asking what they mean
            return Reply(msgs.get("greeting", GREETING)[lang], "answer", lang, "greeting", mode="kb")
        hit, follow_up = self._retrieve(message, history)
        if not self._confident(hit) or hit is None:
            if self.llm and hit is not None and hit.alternatives:  # unsure: let the model pick among the closest entries
                chosen = self._llm_choose(message, history, list(hit.alternatives), lang)
                if chosen:
                    return chosen
            return Reply(msgs["clarify"][lang], "clarify", lang, mode="clarify", confidence=round(hit.score, 2) if hit else 0.0)
        e = hit.entry
        behavior = self._behavior(e.topic)
        reply = Reply(e.answer[lang], behavior, lang, e.topic, [e.id], round(hit.score, 2),
                      notes=["read with the previous message"] if follow_up else [])
        if self.llm and behavior == "answer":
            self._llm_answer(reply, message, history, e)
        return reply

    def _behavior(self, topic: str) -> str:
        return ("handoff" if topic in self.policies["handoff_topics"]
                else "refuse" if topic in self.policies["refuse_topics"] else "answer")

    def _llm_choose(self, message: str, history: list[dict[str, str]], candidates: list[Any], lang: str) -> Reply | None:
        """When retrieval is unsure, the model reads the closest entries and either cites the one that answers the
        question or says CLARIFY. Its choice is only accepted if it cites exactly one of those entries; hand-offs and
        refusals then use the fixed knowledge-base text, and an answer must still pass the grounding checks."""
        try:
            text, provider = self.llm.complete(build_messages(  # type: ignore[union-attr]
                message, history, candidates, lang, self.policies.get("business", "the company"), self.canary, choose=True))
        except ProviderError:
            return None
        cited = [e for e in candidates if f"[{e.id}]" in text]
        if "CLARIFY" in text.upper() or len(cited) != 1:
            return None
        e, behavior = cited[0], self._behavior(cited[0].topic)
        reply = Reply(e.answer[lang], behavior, lang, e.topic, [e.id], notes=[f"{provider} picked {e.id} from {len(candidates)} entries"])
        ok, why = grounded(text, [e], lang, self.canary)
        if behavior == "answer" and ok:
            reply.text, reply.mode = text.strip(), "llm"
        elif behavior == "answer":
            reply.notes.append(f"its wording was rejected ({why}), answered with the entry text")
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
