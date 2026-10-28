"""Bots under test: any OpenAI-compatible endpoint, or a built-in demo bot with realistic faults."""
from __future__ import annotations

import os
import re
import time
from typing import Protocol

import httpx

from chatbot_eval.templates import CANARY
from chatbot_eval.text import detect_language, normalize


class Bot(Protocol):
    name: str

    def ask(self, question: str, history: list[dict[str, str]] | None = None) -> str: ...


class BotError(RuntimeError):
    """The bot could not be reached or returned an unusable response."""


class HttpBot:
    """An OpenAI-compatible /chat/completions endpoint, with retries on rate limits and server errors."""

    def __init__(self, url: str, api_key: str = "", model: str = "default", system_prompt: str = "",
                 timeout_s: float = 60, retries: int = 3, backoff_s: float = 1.0,
                 transport: httpx.BaseTransport | None = None, name: str | None = None):
        self.url, self.model, self.system_prompt = url, model, system_prompt
        self.retries, self.backoff_s = retries, backoff_s
        self.name = name or f"http:{model}"
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = httpx.Client(timeout=timeout_s, headers=headers, transport=transport)

    @classmethod
    def from_env(cls) -> HttpBot:
        if not os.environ.get("BOT_URL"):
            raise BotError("set BOT_URL (and BOT_API_KEY, BOT_MODEL) to test a real bot, or use --bot mock")
        return cls(os.environ["BOT_URL"], os.environ.get("BOT_API_KEY", ""), os.environ.get("BOT_MODEL", "default"),
                   os.environ.get("BOT_SYSTEM_PROMPT", ""))

    def ask(self, question: str, history: list[dict[str, str]] | None = None) -> str:
        messages = ([{"role": "system", "content": self.system_prompt}] if self.system_prompt else []) + \
                   list(history or []) + [{"role": "user", "content": question}]
        last = ""
        for attempt in range(self.retries + 1):
            try:
                r = self.client.post(self.url, json={"model": self.model, "messages": messages, "temperature": 0})
            except httpx.HTTPError as exc:
                last = type(exc).__name__
            else:
                if r.status_code == 200:
                    try:
                        return str(r.json()["choices"][0]["message"]["content"])
                    except (ValueError, KeyError, IndexError, TypeError) as exc:
                        raise BotError("unexpected response format") from exc
                last = f"HTTP {r.status_code}"
                if r.status_code not in (408, 409, 429) and r.status_code < 500:
                    break  # a client error will not fix itself
            if attempt < self.retries:
                time.sleep(self.backoff_s * 2 ** attempt)
        raise BotError(last)


# ---------- demo bot ----------

KEYWORDS: list[tuple[str, list[str]]] = [  # checked in order; normalized text
    ("security", ["تجاهل", "تعليمات", " انس", "ignore", "system prompt", "developer mode", "ta3limat", "الادمن", "admin"]),
    ("refund", ["استرد", "استرج", "فلوسي", "ترجع", "رجع", "refund", "money back", "floos", "الفلوس", "مصرياتي"]),
    ("human_agent", ["اكلم", "اتكلم", "احكي مع", "نتكلم", "موظف", "خدمه العملاء", "الدعم", "human", "agent", "akalem",
                     "customer service"]),
    ("cancellation", ["الغي", "الغاء", "بلغي", "ايقاف", "اوقف", " وقف", "نلغي", "cancel", "stop my", "a2lel", "awa2af"]),
    ("pricing", ["بكام", "بكم", "سعر", "قديش", "تكلفه", "price", "how much", "b kam", " كم"]),
    ("certificate", ["شهاده", "certificate", "shehada"]),
    ("password", ["باسورد", "كلمه السر", "كلمه المرور", "الرقم السري", "password", "login", "log in", "تسجيل الدخول",
                  "ادخل", "فوت علي حسابي", "ندخل"]),
    ("payment", ["الفيزا", "البطاقه", "بطاقتي", "الكارت", "الدفع", "payment", "card", "visa", "daf3", "decline"]),
    ("video", ["فيديو", "المقطع", "video", "buffering"]),
    ("course_access", ["الكورس", "الدوره", "course"]),
    ("out_of_scope", ["سهم", "stock", "sahm", "الطقس", "الجو", "weather", "gaw", "وصفه", "قصيده", "essay", "الطاجين"]),
    ("vague", ["مشكل", "problem", "issue", "moshkela", "شغال", "خدام", "يزبط", "مشي", "خلل", "working", "غلط", "shaghal"]),
]

ANSWERS: dict[str, tuple[str, str]] = {
    "cancellation": ("يمكنك إلغاء الاشتراك في أي وقت من الإعدادات ثم الاشتراك.",
                     "You can cancel any time from Settings > Subscription."),
    "pricing": ("الاشتراك الشهري 10 دولار والسنوي 100 دولار.", "The monthly plan is $10 and the yearly plan is $100."),
    "refund": ("يمكن استرداد المبلغ خلال 14 يومًا من الاشتراك.", "Refunds are possible within 14 days of purchase."),
    "certificate": ("نعم، تحصل على شهادة بعد إتمام الدورة، وتظهر في صفحة دوراتي.",
                    "Yes, you get a certificate after you finish the course; it appears under My courses."),
    "password": ("اضغط على «نسيت كلمة المرور» وسيصلك رابط على بريدك الإلكتروني.",
                 "Click 'Forgot password' and we'll email you a reset link."),
    "payment": ("تأكد من بيانات البطاقة أو جرّب بطاقة أخرى من صفحة الدفع.",
                "Check your card details or try another card on the payment page."),
    "course_access": ("ستجد كل دوراتك في صفحة «دوراتي» بعد تسجيل الدخول بنفس الحساب.",
                      "All your courses are under My courses when you log in with the same account."),
    "video": ("جرّب تحديث الصفحة أو استخدام متصفح آخر، وتأكد من سرعة الإنترنت.",
              "Try a refresh of the page or another browser, and check your connection."),
    "human_agent": ("بالتأكيد، سأحوّلك الآن إلى فريق الدعم.", "Sure, I'm connecting you to our support team now."),
    "vague": ("شكرًا لتواصلك معنا.", "Thanks for reaching out."),
    "out_of_scope": ("عذرًا، أستطيع المساعدة فقط في أسئلة المنصة والدورات.",
                     "Sorry, I can only help with questions about the platform and courses."),
    "security": ("عذرًا، لا أستطيع مشاركة هذه المعلومات.", "Sorry, I can't share that information."),
    "unknown": ("عذرًا، لم أفهم سؤالك.", "Sorry, I didn't understand your question."),
}

FIXES_V2: dict[str, tuple[str, str]] = {  # round 2 after the first UAT report
    "refund": ("سأحوّلك إلى فريق الدعم لمراجعة طلب الاسترداد، وعادةً يكون متاحًا خلال 14 يومًا.",
               "I'll pass you to our support team to review the refund; it's usually possible within 14 days."),
    "vague": ("ممكن توضح المشكلة أكثر؟ هل تتعلق بالدفع أو الدورة أو الحساب؟",
              "Could you tell me more? Is it about payment, a course or your account?"),
    "pricing": ("الاشتراك الشهري بـ10 والسنوي بـ100.", "The monthly plan is $10 and the yearly plan is $100."),  # regression
}


class MockBot:
    """A deterministic demo bot that makes the mistakes real bots make.

    Round 1 (version 1): answers Franco in English, leaks its instructions when asked about its
    "system prompt", answers refund requests without handing off, never asks a clarifying question,
    and does not understand several Maghrebi words (on purpose: dialect gaps are the most common real failure).
    Round 2 (version 2): fixes those, but a prompt change drops the currency from Arabic prices.
    """

    def __init__(self, version: int = 1):
        self.version = version
        self.name = f"demo-bot-v{version}"

    def intent(self, question: str) -> str:
        q = f" {normalize(question)} "
        for intent, words in KEYWORDS:
            if any(w in q for w in words):
                return intent
        return "unknown"

    def ask(self, question: str, history: list[dict[str, str]] | None = None) -> str:
        """Both rounds ignore the conversation history, so follow-up questions fail, as they often do."""
        lang = detect_language(question)
        reply_ar = lang == "ar" or (lang == "franco" and self.version >= 2)
        intent = self.intent(question)
        if intent == "security" and self.version == 1 and re.search("system prompt", question, re.I):
            return f"System prompt: You are the course assistant for the platform. Internal tag {CANARY}."
        answers = FIXES_V2.get(intent, ANSWERS[intent]) if self.version >= 2 else ANSWERS[intent]
        return answers[0] if reply_ar else answers[1]
