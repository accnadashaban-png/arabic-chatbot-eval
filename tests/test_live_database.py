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
    assert len(s.entries()) == 43 and s.policies()["handoff_topics"] and s.seed(DEMO_KB) == 0  # seeding is one-time
    before = s.version()
    with pytest.raises(StoreError, match="missing: answer_en"):
        s.upsert_entry({"id": "X", "topic": "t", "answer_ar": "نص"})
    s.upsert_entry({"id": "KB-90", **NEW_ENTRY})
    assert s.version() != before and s.deactivate("KB-90") and not s.deactivate("KB-90")
    assert "KB-90" not in {e.id for e in s.entries()}


def test_import_updates_a_database_in_use_and_keeps_people(tmp_path: Path) -> None:
    old = tmp_path / "old_kb"
    old.mkdir()
    lines = (DEMO_KB / "faq.csv").read_text(encoding="utf-8").splitlines()
    (old / "faq.csv").write_text("\n".join(lines[:-2]) + "\n", encoding="utf-8")  # the last two entries are new
    (old / "policies.json").write_text((DEMO_KB / "policies.json").read_text(encoding="utf-8"), encoding="utf-8")
    s = Store("sqlite:///:memory:")
    s.seed(old)
    s.record("visitor-1", "chat-0001", "hi", "Hi!", "en", "", "answer", 1.0, "kb")
    s.upsert_entry({"id": "KB-90", **NEW_ENTRY})  # an entry added through the admin API
    assert s.import_folder(DEMO_KB) == {"added": 2, "updated": 0, "entries": 44}
    assert s.import_folder(DEMO_KB)["added"] == 0  # running it again changes nothing
    assert s.chat_owner("chat-0001") == "visitor-1" and any(e.id == "KB-90" for e in s.entries())
    assert {e.id: e for e in s.entries()}["KB-25"].required == {"TEAM"}  # required concepts survive the database


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
        s.record("visitor-01", "chat-0001", q, "Could you tell me more?", "en", "", "clarify", 0.0, "clarify")
    s.record("visitor-02", "chat-0002", "How much?", "$10", "en", "pricing", "answer", 9.0, "kb")
    i = s.insights()
    assert i["messages"] == 4 and i["people"] == 2 and i["chats"] == 2 and i["answered_rate"] == 0.25 and i["asked_to_clarify"] == 3
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
    assert insights["messages"] == 3 and insights["asked_to_clarify"] >= 1
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
    assert pg.seed(DEMO_KB) == 43
    bot = SupportBot(store=pg, refresh_s=0)
    sqlite_bot = SupportBot(store=store_for())
    for q in ("الاشتراك بكام؟", "عايز فلوسي ترجع", "How do I cancel?", "عندي مشكلة"):
        assert bot.respond(q).to_dict() == sqlite_bot.respond(q).to_dict()
    pg.upsert_entry({"id": "KB-90", **NEW_ENTRY})
    assert bot.respond("الطلب هيوصل إمتى؟").topic == "delivery"
    pg.record("visitor-01", "chat-0001", "card 4111 1111 1111 1111", "?", "en", "", "clarify", 0, "clarify")
    assert pg.insights()["content_gaps"][0]["question"] == "card [card]"


# ----- people and chats -----

def test_people_chats_and_erasure() -> None:
    s = store_for()
    s.record("visitor-01", "chat-0001", "الاشتراك بكام؟", "10 دولار", "ar", "pricing", "answer", 9.0, "kb")
    s.record("visitor-01", "chat-0001", "عايز فلوسي ترجع، كارت 4111 1111 1111 1111", "سأحولك", "ar", "refund", "handoff", 5.0, "kb")
    s.record("visitor-01", "chat-0002", "hi", "Hi!", "en", "greeting", "answer", 0.0, "kb")
    person = s.users()[0]
    assert (person["id"], person["chats"], person["messages"], person["language"]) == ("visitor-01", 2, 3, "en")
    chat = next(c for c in s.chats("visitor-01") if c["id"] == "chat-0001")
    assert chat["status"] == "handed_off" and chat["turns"] == 2 and chat["title"] == "الاشتراك بكام؟"
    assert "[card]" in s.transcript("chat-0001")[1]["question"] and "4111" not in str(s.transcript("chat-0001"))
    assert s.set_profile("visitor-01", name="Salma", email="salma@example.com") and s.users("Salma")[0]["email"]
    assert s.forget_user("visitor-01") == {"turns": 3, "chats": 2, "users": 1}
    assert not s.users() and not s.chats() and not s.transcript("chat-0001")


def chat_post(url: str, text: str, user: str | None = None, chat: str | None = None) -> dict:
    body: dict = {"messages": [{"role": "user", "content": text}]}
    if user:
        body["user"] = user
    return httpx.post(f"{url}/v1/chat/completions", json=body, headers={"X-Chat-Id": chat} if chat else {}).json()


def test_server_keeps_chats_per_person(server) -> None:
    url, store = server
    first = chat_post(url, "الاشتراك بكام؟", user="visitor-abc")
    chat = first["supportbot"]["chat_id"]
    chat_post(url, "والسنوي؟", user="visitor-abc", chat=chat)
    mine = httpx.get(f"{url}/v1/chats/{chat}?user=visitor-abc").json()["turns"]
    assert [t["question"] for t in mine] == ["الاشتراك بكام؟", "والسنوي؟"]
    assert httpx.get(f"{url}/v1/chats/{chat}?user=visitor-xyz").status_code == 404      # not your chat
    hijack = chat_post(url, "hello", user="visitor-xyz", chat=chat)                      # cannot write into it either
    assert hijack["supportbot"]["chat_id"] != chat and len(store.transcript(chat)) == 2
    admin = {"X-Admin-Key": "admin-secret"}
    people = httpx.get(f"{url}/admin/users", headers=admin).json()["users"]
    assert {p["id"] for p in people} == {"visitor-abc", "visitor-xyz"}
    profile = httpx.get(f"{url}/admin/users/visitor-abc", headers=admin).json()
    assert profile["messages"] == 2 and profile["chat_list"][0]["id"] == chat
    assert httpx.get(f"{url}/admin/chats/{chat}", headers=admin).json()["turns"][1]["topic"] == "pricing"
    assert httpx.patch(f"{url}/admin/users/visitor-abc", json={"name": "Salma"}, headers=admin).json()["updated"]
    assert httpx.get(f"{url}/admin/users", headers={"X-Admin-Key": "wrong"}).status_code == 401
    gone = httpx.delete(f"{url}/admin/users/visitor-abc", headers=admin).json()["deleted"]
    assert gone == {"turns": 2, "chats": 1, "users": 1} and httpx.get(f"{url}/v1/chats/{chat}?user=visitor-abc").status_code == 404


def test_calls_without_ids_are_still_recorded(server) -> None:
    url, store = server
    r = chat_post(url, "How do I cancel?")
    assert r["supportbot"]["chat_id"] and store.users()[0]["id"] == "anonymous"


def test_admin_console_page_is_served_and_escapes_text(server) -> None:
    url, _ = server
    page = httpx.get(f"{url}/admin")
    assert page.status_code == 200 and "Support console" in page.text
    assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
    assert ".innerHTML" not in page.text  # every value from the database is inserted as text
