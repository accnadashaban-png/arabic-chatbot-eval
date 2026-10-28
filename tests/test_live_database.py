"""Live database, admin API, conversation insights, the LLM provider group and LLM choice among entries."""
import os
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest

from supportbot.bot import SupportBot
from supportbot.knowledge import DEMO_KB
from supportbot.llm import Provider, ProviderError, Router
from supportbot.server import make_handler
from supportbot.store import Store, StoreError

NEW_ENTRY = {"topic": "delivery", "concepts": "SCHEDULE", "questions": ["متى يصل الطلب؟", "When will my order arrive?"],
             "answer_ar": "يصل الطلب خلال 3 أيام عمل.", "answer_en": "Orders arrive within 3 working days."}


def store_for(url: str = "sqlite:///:memory:") -> Store:
    s = Store(url)
    s.seed(DEMO_KB)
    return s


def test_seed_validate_and_version() -> None:
    s = store_for()
    assert len(s.entries()) == 23 and s.policies()["handoff_topics"] and s.seed(DEMO_KB) == 0  # seeding is one-time
    before = s.version()
    with pytest.raises(StoreError, match="missing: answer_en"):
        s.upsert_entry({"id": "X", "topic": "t", "answer_ar": "نص"})
    s.upsert_entry({"id": "KB-90", **NEW_ENTRY})
    assert s.version() != before and s.deactivate("KB-90") and not s.deactivate("KB-90")
    assert "KB-90" not in {e.id for e in s.entries()}


def test_the_bot_follows_the_database_without_a_restart() -> None:
    s = store_for()
    bot = SupportBot(store=s, refresh_s=0)
    assert bot.respond("When will my order arrive?").topic != "delivery"
    s.upsert_entry({"id": "KB-90", **NEW_ENTRY})                         # e.g. another system writes to the database
    r = bot.respond("الطلب هيوصل إمتى؟")
    assert r.topic == "delivery" and "3 أيام" in r.text
    s.upsert_entry({"id": "KB-90", **NEW_ENTRY, "answer_ar": "يصل الطلب خلال يومين."})
    assert "يومين" in bot.respond("الطلب هيوصل إمتى؟").text
    s.deactivate("KB-90")
    assert bot.respond("الطلب هيوصل إمتى؟").topic != "delivery"


def test_insights_mask_personal_data_and_show_content_gaps() -> None:
    s = store_for()
    for q in ("my card 4111 1111 1111 1111 is stuck", "My card 4111 1111 1111 1111 is stuck?", "email me at a@b.com"):
        s.log(q, "en", "", "clarify", 0.0, "clarify")
    s.log("How much?", "en", "pricing", "answer", 9.0, "kb")
    i = s.insights()
    assert i["conversations"] == 4 and i["answered_rate"] == 0.25 and i["asked_to_clarify"] == 3
    assert i["content_gaps"][0] == {"question": "my card [card] is stuck", "times": 2}
    assert all("4111" not in g["question"] and "@" not in g["question"] for g in i["content_gaps"])


@pytest.fixture
def server():
    s = store_for()
    bot = SupportBot(store=s, refresh_s=60)  # refreshing is forced by the admin API, not by the timer
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(bot, admin_key="admin-secret", per_minute=0))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", s
    httpd.shutdown()


def ask(url: str, text: str) -> dict:
    return httpx.post(f"{url}/v1/chat/completions", json={"messages": [{"role": "user", "content": text}]}).json()


def test_admin_api_changes_answers_live(server) -> None:
    url, store = server
    admin = {"X-Admin-Key": "admin-secret"}
    assert httpx.get(f"{url}/admin/entries").status_code == 401
    assert httpx.put(f"{url}/admin/entries/KB-90", json=NEW_ENTRY, headers={"X-Admin-Key": "nope"}).status_code == 401
    assert httpx.put(f"{url}/admin/entries/../x", json=NEW_ENTRY, headers=admin).status_code == 404
    assert httpx.put(f"{url}/admin/entries/KB-90", json={"topic": "x"}, headers=admin).status_code == 422
    r = httpx.put(f"{url}/admin/entries/KB-90", json=NEW_ENTRY, headers=admin)
    assert r.status_code == 200 and r.json()["live"] is True
    assert ask(url, "When will my order arrive?")["supportbot"]["topic"] == "delivery"
    assert any(e["id"] == "KB-90" for e in httpx.get(f"{url}/admin/entries", headers=admin).json()["entries"])
    assert httpx.delete(f"{url}/admin/entries/KB-90", headers=admin).json() == {"id": "KB-90", "active": False}
    assert ask(url, "When will my order arrive?")["supportbot"]["topic"] != "delivery"
    ask(url, "عندي مشكلة")
    insights = httpx.get(f"{url}/admin/insights?days=1", headers=admin).json()
    assert insights["conversations"] == 3 and insights["asked_to_clarify"] >= 1
    assert httpx.get(f"{url}/admin/llm", headers=admin).json() == {"providers": []}


def test_admin_api_is_off_without_a_key() -> None:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(SupportBot(store=store_for())))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        r = httpx.get(f"http://127.0.0.1:{httpd.server_address[1]}/admin/entries", headers={"X-Admin-Key": ""})
        assert r.status_code == 403
    finally:
        httpd.shutdown()


# ----- the LLM provider group -----

class Clock:
    t = 1000.0

    def __call__(self) -> float:
        return self.t


def scripted(name: str, *responses: httpx.Response) -> tuple[Provider, list[int]]:
    queue, calls = list(responses), []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return queue.pop(0) if len(queue) > 1 else queue[0]
    return Provider(name, "https://llm.test/v1/chat/completions", "secret-key", "m", httpx.MockTransport(handler)), calls


def ok(text: str = "fine") -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": text}}]})


def test_a_provider_out_of_credit_rests_and_the_next_one_answers() -> None:
    clock = Clock()
    a, a_calls = scripted("free-a", httpx.Response(429, text='{"error": "You exceeded your current quota"}'), ok("from a"))
    b, b_calls = scripted("free-b", ok("from b"))
    router = Router([a, b], clock=clock)
    assert router.complete([]) == ("from b", "free-b")
    assert router.complete([]) == ("from b", "free-b") and len(a_calls) == 1   # a is resting: not even called
    status = {p["name"]: p for p in router.status()}
    assert status["free-a"]["last_error"] == "quota" and status["free-a"]["rests_for_s"] == 6 * 3600
    assert "secret-key" not in str(router.status())
    clock.t += 6 * 3600 + 1
    assert router.complete([]) == ("from a", "free-a")                           # back after its rest


def test_cooldowns_fit_the_failure() -> None:
    clock = Clock()
    a, _ = scripted("a", httpx.Response(429, headers={"Retry-After": "12"}))
    b, _ = scripted("b", httpx.Response(400))
    c, _ = scripted("c", httpx.Response(503))
    router = Router([a, b, c], clock=clock)
    with pytest.raises(ProviderError) as err:
        router.complete([])
    assert err.value.kind == "unavailable"
    rest = {p["name"]: p["rests_for_s"] for p in router.status()}
    assert rest == {"a": 12, "b": 0, "c": 30}       # Retry-After honoured; a rejected request does not bench a provider
    router.complete.__self__  # noqa: B018 - the router object stays usable


def test_when_every_provider_rests_the_soonest_is_tried() -> None:
    clock = Clock()
    a, a_calls = scripted("a", httpx.Response(503), ok("a is back"))
    router = Router([a], clock=clock)
    with pytest.raises(ProviderError):
        router.complete([])
    assert router.complete([]) == ("a is back", "a") and len(a_calls) == 2


# ----- the model picks among close entries when retrieval is unsure -----

def bot_with(reply: str) -> SupportBot:
    p, _ = scripted("m", ok(reply))
    return SupportBot(llm=Router([p]), canary="SB-T")


def test_llm_choice_when_retrieval_is_unsure() -> None:
    question = "عايز أسأل عن الدفع"  # failed payment or payment methods? retrieval alone cannot tell
    plain = SupportBot()
    assert plain.respond(question).behavior == "clarify"
    assert {"KB-05", "KB-06"} <= {e.id for e in plain.index.search(question).alternatives}
    r = bot_with("نقبل الدفع بالبطاقة (فيزا وماستركارد) وعبر PayPal [KB-06]").respond(question)
    assert r.topic == "payment_methods" and r.mode == "llm" and "picked KB-06" in r.notes[0]
    invented = bot_with("نقبل الدفع بالبطاقة وفوري وPayPal مع خصم 20% [KB-06]").respond(question)
    assert invented.topic == "payment_methods" and invented.mode == "kb" and "20" not in invented.text
    assert bot_with("CLARIFY").respond(question).behavior == "clarify"
    assert bot_with("It is KB-99 [KB-99]").respond(question).behavior == "clarify"   # not one of the candidates


def test_llm_choice_never_rewrites_a_hand_off() -> None:
    r = bot_with("Sure, you get an instant refund! [KB-03]").respond("charged twice, reverse it")
    if r.topic == "refund":
        assert r.behavior == "handoff" and "instant" not in r.text and "support team" in r.text


# ----- PostgreSQL -----

def postgres_url() -> str | None:
    if os.environ.get("SB_TEST_PG_URL"):
        return os.environ["SB_TEST_PG_URL"]
    try:
        import pgserver  # type: ignore[import-not-found]
    except ImportError:
        return None
    return str(pgserver.get_server(Path(os.environ.get("TEMP", "/tmp")) / "sb_pgdata").get_uri())


def test_postgres_store_behaves_like_sqlite() -> None:
    url = postgres_url()
    if not url:
        pytest.skip("no PostgreSQL available")
    pg = Store(url)
    pg._run("DROP TABLE IF EXISTS kb_entries, kb_settings, conversations")
    pg = Store(url)
    assert pg.seed(DEMO_KB) == 23
    bot = SupportBot(store=pg, refresh_s=0)
    sqlite_bot = SupportBot(store=store_for())
    for q in ("الاشتراك بكام؟", "عايز فلوسي ترجع", "How do I cancel?", "عندي مشكلة"):
        assert bot.respond(q).to_dict() == sqlite_bot.respond(q).to_dict()
    pg.upsert_entry({"id": "KB-90", **NEW_ENTRY})
    assert bot.respond("الطلب هيوصل إمتى؟").topic == "delivery"
    pg.log("card 4111 1111 1111 1111", "en", "", "clarify", 0, "clarify")
    assert pg.insights()["content_gaps"][0]["question"] == "card [card]"
