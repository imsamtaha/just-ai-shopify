import asyncio
import json
import logging
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from telegram.error import Conflict
from just_ai.catalog import COMMANDS, SKILLS, instructions
from just_ai.config import ConfigError, Settings, load_settings
from just_ai.handlers import Handlers
from just_ai.provider import Provider, ProviderError
from just_ai.runtime import StartupError, build_application, instance_lock, safe_logging
from just_ai.store import Store
from just_ai.ui import chunks, menu, options

TEST_TOKEN = "123456789:" + "A" * 35


def settings(**changes):
    args = dict(token=TEST_TOKEN, api_key="test-credential", model="test-model", allowed=frozenset({1, 2}))
    args.update(changes)
    return Settings(**args)


def update(text="/start", uid=1, chat_type="private", age=0):
    msg = SimpleNamespace(text=text, date=datetime.now(timezone.utc) - timedelta(seconds=age), reply_text=AsyncMock())
    return SimpleNamespace(effective_user=SimpleNamespace(id=uid, language_code="en"),
        effective_chat=SimpleNamespace(id=uid, type=chat_type), effective_message=msg, message=msg,
        callback_query=None)


class StoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "db.sqlite3"
        self.store = Store(self.path)
        await self.store.initialize()

    async def asyncTearDown(self):
        (await self.store.close())
        self.tmp.cleanup()

    async def test_user_isolation_and_persistence(self):
        item = (await self.store.add(1, "task", "Private"))
        self.assertFalse((await self.store.change_item(2, "task", item, True)))
        self.assertFalse((await self.store.change_item(2, "task", item)))
        self.assertEqual((await self.store.items(2, "task")), [])
        (await self.store.preference(1, "skin", "minimal"))
        (await self.store.exchange(1, "Question", "Answer"))
        (await self.store.close())
        self.store = Store(self.path)
        await self.store.initialize()
        self.assertEqual((await self.store.prefs(1))["skin"], "minimal")
        self.assertEqual(len((await self.store.history(1))), 2)
        self.assertEqual((await self.store.history(2)), [])
        self.assertTrue((await self.store.change_item(1, "task", item, True)))
        self.assertTrue((await self.store.items(1, "task"))[0]["done"])

    async def test_history_is_bounded_and_reset_keeps_notes(self):
        (await self.store.add(1, "note", "Keep"))
        for i in range(20):
            (await self.store.exchange(1, str(i), "reply"))
        self.assertEqual(len((await self.store.history(1))), 12)
        self.assertEqual((await self.store.history(1))[0]["content"], "14")
        (await self.store.reset(1))
        self.assertEqual((await self.store.history(1)), [])
        self.assertEqual(len((await self.store.items(1, "note"))), 1)

    async def test_quota_survives_forget_and_rolls_over(self):
        self.assertTrue((await self.store.reserve(1, 1, "2026-10-04")))
        (await self.store.forget(1))
        self.assertFalse((await self.store.reserve(1, 1, "2026-10-04")))
        self.assertTrue((await self.store.reserve(1, 1, "2026-10-05")))
        self.assertEqual((await self.store.used(1, "2026-10-04")), 0)

    async def test_forget_scoped_to_owner(self):
        for uid in (1, 2):
            (await self.store.add(uid, "note", "note"))
            (await self.store.exchange(uid, "q", "a"))
            (await self.store.preference(uid, "mode", "coding"))
        (await self.store.forget(1))
        self.assertEqual((await self.store.items(1, "note")), [])
        self.assertEqual((await self.store.history(1)), [])
        self.assertEqual((await self.store.prefs(1))["mode"], "general")
        self.assertEqual(len((await self.store.history(2))), 2)

    async def test_item_limits_and_sql_values(self):
        (await self.store.add(1, "note", "'); DROP TABLE items; --"))
        self.assertEqual(len((await self.store.items(1, "note"))), 1)
        for i in range(99):
            (await self.store.add(1, "note", "x"))
        with self.assertRaises(ValueError):
            (await self.store.add(1, "note", "overflow"))
        with self.assertRaises(ValueError):
            (await self.store.add(2, "note", "x" * 2001))
        with self.assertRaises(ValueError):
            (await self.store.preference(1, "mode; DROP TABLE items", "coding"))


class ConfigAndUiTests(unittest.TestCase):
    def test_provider_keys_are_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {"TELEGRAM_BOT_TOKEN": TEST_TOKEN, "AI_PROVIDER": "openrouter",
                   "OPENAI_API_KEY": "unused", "OPENAI_MODEL": "unused",
                   "OPENROUTER_API_KEY": "router-secret", "OPENROUTER_MODEL": "openai/gpt-4.1-mini"}
            result = load_settings(root, env)
            self.assertEqual(result.provider, "openrouter")
            self.assertEqual(result.api_key, "router-secret")
            self.assertEqual(result.model, "openai/gpt-4.1-mini")
            self.assertNotIn("router-secret", repr(result))
            self.assertFalse(load_settings(root, {**env, "OPENROUTER_API_KEY": ""}).ai_ready)
            with self.assertRaises(ConfigError):
                load_settings(root, {**env, "AI_PROVIDER": "unknown"})

    def test_config_hidden_and_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {"TELEGRAM_BOT_TOKEN": TEST_TOKEN, "OPENAI_API_KEY": "secret-test", "ALLOWED_USER_IDS": "1,2"}
            result = load_settings(root, env)
            self.assertNotIn(TEST_TOKEN, repr(result))
            self.assertNotIn("secret-test", repr(result))
            self.assertFalse(result.ai_ready)
            for name, value in (("DAILY_AI_LIMIT", "0"), ("COOLDOWN_SECONDS", "bad"),
                                ("ALLOWED_USER_IDS", "-1"), ("TELEGRAM_BOT_TOKEN", "bad")):
                with self.assertRaises(ConfigError):
                    load_settings(root, {**env, name: value})

    def test_config_uses_own_file_without_interpolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".env").write_text(f'TELEGRAM_BOT_TOKEN={TEST_TOKEN}\nOPENAI_API_KEY="literal${{DO_NOT_EXPAND}}"\n', encoding="utf-8")
            self.assertEqual(load_settings(root, {}).api_key, "literal${DO_NOT_EXPAND}")

    def test_unicode_chunks_are_lossless(self):
        text = "🟠مرحبا\n" * 1900
        parts = list(chunks(text))
        self.assertEqual("".join(parts), text)
        self.assertTrue(all(len(x.encode("utf-16-le")) // 2 <= 3500 for x in parts))

    def test_commands_and_callback_size(self):
        names = [cmd for cmd, _, _ in COMMANDS]
        self.assertEqual(len(names), len(set(names)))
        for keyboard in [menu(False), menu(True), options("mode", True), options("skin", False), options("language", True)]:
            for row in keyboard.inline_keyboard:
                for button in row:
                    self.assertLessEqual(len(button.callback_data.encode()), 64)
        for skill in SKILLS:
            self.assertIn("no browsing", instructions(skill, "minimal", "ar"))

    def test_single_instance_lock_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lock"
            with instance_lock(path):
                with self.assertRaises(StartupError):
                    with instance_lock(path):
                        pass
            with instance_lock(path):
                pass

    def test_safe_logging_hides_http(self):
        safe_logging()
        self.assertFalse(logging.getLogger("httpx").isEnabledFor(logging.INFO))
        self.assertFalse(logging.getLogger("telegram.ext").isEnabledFor(logging.ERROR))


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_openrouter_uses_its_endpoint_and_sanitizes_errors(self):
        def respond(request):
            self.assertEqual(str(request.url), "https://openrouter.ai/api/v1/responses")
            self.assertEqual(request.headers["Authorization"], "Bearer router-secret")
            body = json.loads(request.content)
            self.assertEqual(body["model"], "openai/gpt-4.1-mini")
            self.assertFalse(body["store"])
            return httpx.Response(402, text="PRIVATE_ACCOUNT_DETAILS")
        provider = Provider(settings(provider="openrouter", api_key="router-secret",
                                     model="openai/gpt-4.1-mini"), httpx.MockTransport(respond))
        try:
            with self.assertRaises(ProviderError) as error:
                await provider.answer("Rules", [{"role": "user", "content": "hi"}])
            self.assertIn("credits", str(error.exception))
            self.assertNotIn("PRIVATE_ACCOUNT_DETAILS", str(error.exception))
        finally:
            await provider.close()

    async def test_request_and_output_parsing(self):
        seen = []
        def respond(request):
            body = json.loads(request.content)
            seen.append(body)
            return httpx.Response(200, json={"status": "completed", "output": [
                {"type": "reasoning", "summary": []},
                {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Hello"}]}]})
        provider = Provider(settings(), httpx.MockTransport(respond))
        try:
            answer = await provider.answer("Rules", [{"role": "user", "content": "hi"}])
            self.assertEqual(answer, "Hello")
            self.assertFalse(seen[0]["store"])
            self.assertNotIn("tools", seen[0])
        finally:
            await provider.close()

    async def test_http_errors_never_expose_body(self):
        for status in (401, 403, 404, 429, 500):
            provider = Provider(settings(), httpx.MockTransport(lambda r: httpx.Response(status, text="SECRET_PRIVATE_BODY")))
            try:
                with self.assertRaises(ProviderError) as error:
                    await provider.answer("", [])
                self.assertNotIn("SECRET_PRIVATE_BODY", str(error.exception))
            finally:
                await provider.close()

    async def test_incomplete_invalid_and_empty_responses(self):
        for body in ({"status": "incomplete", "output": []}, {"status": "completed", "output": []}, []):
            provider = Provider(settings(), httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
            try:
                with self.assertRaises(ProviderError):
                    await provider.answer("", [])
            finally:
                await provider.close()

    async def test_timeout_is_sanitized(self):
        def timeout(request):
            raise httpx.ReadTimeout("private URL and key", request=request)
        provider = Provider(settings(), httpx.MockTransport(timeout))
        try:
            with self.assertRaises(ProviderError) as error:
                await provider.answer("", [])
            self.assertNotIn("private URL", str(error.exception))
        finally:
            await provider.close()


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "db")
        await self.store.initialize()
        self.provider = SimpleNamespace(answer=AsyncMock(return_value="Answer"), close=AsyncMock())
        self.handlers = Handlers(settings(), self.store, self.provider)

    async def asyncTearDown(self):
        (await self.store.close())
        self.tmp.cleanup()

    async def command(self, text, uid=1):
        event = update(text, uid)
        await self.handlers.command(event, None)
        return event

    async def test_unauthorized_group_and_stale_requests_never_call_ai(self):
        for event in (update("hi", uid=99), update("hi", chat_type="group"), update("hi", age=400)):
            await self.handlers.text(event, None)
        self.provider.answer.assert_not_awaited()
        event = await self.command("/whoami", 99)
        self.assertIn("99", event.message.reply_text.call_args.args[0])
        self.assertEqual((await self.store.history(99)), [])

    async def test_ai_saves_history_only_after_success(self):
        await self.handlers.text(update("Hello"), None)
        self.assertEqual(len((await self.store.history(1))), 2)
        self.handlers.last_request.clear()
        self.provider.answer.side_effect = ProviderError("Temporary failure")
        await self.handlers.text(update("Again"), None)
        self.assertEqual(len((await self.store.history(1))), 2)
        self.assertEqual((await self.store.used(1)), 2)

    async def test_failed_delivery_does_not_save_history(self):
        event = update("hello")
        event.message.reply_text.side_effect = RuntimeError("network")
        with self.assertRaises(RuntimeError):
            await self.handlers.text(event, None)
        self.assertEqual((await self.store.history(1)), [])

    async def test_cooldown_and_quota(self):
        self.handlers.settings = settings(daily_limit=1)
        await self.handlers.text(update("first"), None)
        await self.handlers.text(update("too soon"), None)
        self.handlers.last_request.clear()
        await self.handlers.text(update("quota"), None)
        self.assertEqual(self.provider.answer.await_count, 1)

    async def test_notes_tasks_complete_and_delete(self):
        await self.command("/note hello")
        await self.command("/task prepare proposal")
        task_id = (await self.store.items(1, "task"))[0]["id"]
        await self.command(f"/done {task_id}")
        self.assertEqual((await self.store.items(1, "task"))[0]["done"], 1)
        await self.command(f"/task_delete {task_id}", uid=2)
        self.assertEqual(len((await self.store.items(1, "task"))), 1)
        await self.command(f"/task_delete {task_id}")
        self.assertEqual((await self.store.items(1, "task")), [])

    async def test_multiline_commands_preserve_content(self):
        await self.command("/note@JustAI_chatbot\nFirst line\nSecond line")
        await self.command("/task\tPrepare the proposal\nInclude pricing")
        self.assertEqual((await self.store.items(1, "note"))[0]["content"],
                         "First line\nSecond line")
        self.assertEqual((await self.store.items(1, "task"))[0]["content"],
                         "Prepare the proposal\nInclude pricing")
        await self.command("/prompt\nDraft an email\nIn Arabic")
        self.assertEqual(self.provider.answer.call_args.args[1][-1]["content"],
                         "Draft an email\nIn Arabic")

    async def test_language_command_immediately_uses_selected_language(self):
        event = await self.command("/language ar")
        reply = event.message.reply_text.call_args
        self.assertIn("تم الحفظ", reply.args[0])
        self.assertEqual(next(button.text for row in reply.kwargs["reply_markup"].inline_keyboard for button in row if button.callback_data == "menu:skills"), "المهارات")
        event = await self.command("/language en")
        reply = event.message.reply_text.call_args
        self.assertIn("Saved", reply.args[0])
        self.assertEqual(next(button.text for row in reply.kwargs["reply_markup"].inline_keyboard for button in row if button.callback_data == "menu:skills"), "Skills")

    async def test_language_callback_immediately_refreshes_menu(self):
        for language, expected_text, expected_button in (
            ("ar", "تم الحفظ", "المهارات"), ("en", "Saved", "Skills"),
            ("ar", "تم الحفظ", "المهارات"), ("auto", "Saved", "Skills"),
        ):
            event = update("")
            event.message = None
            event.callback_query = SimpleNamespace(data=f"set:language:{language}", answer=AsyncMock())
            await self.handlers.callback(event, None)
            reply = event.effective_message.reply_text.call_args
            self.assertIn(expected_text, reply.args[0])
            self.assertEqual(next(button.text for row in reply.kwargs["reply_markup"].inline_keyboard for button in row if button.callback_data == "menu:skills"), expected_button)
            self.assertEqual((await self.store.prefs(1))["language"], language)

    async def test_forget_needs_recent_confirmation(self):
        (await self.store.add(1, "note", "keep"))
        await self.command("/forget confirm")
        self.assertEqual(len((await self.store.items(1, "note"))), 1)
        await self.command("/forget confirm")
        self.assertEqual((await self.store.items(1, "note")), [])

    async def test_all_menu_callbacks(self):
        buttons = [b for row in menu(False).inline_keyboard for b in row]
        buttons += [b for f in ("mode", "skin", "language") for row in options(f, False).inline_keyboard for b in row]
        for button in buttons:
            event = update("")
            event.message = None
            event.callback_query = SimpleNamespace(data=button.callback_data, answer=AsyncMock())
            await self.handlers.callback(event, None)
            event.effective_message.reply_text.assert_awaited()
        self.assertEqual((await self.store.prefs(1))["language"], "ar")

    async def test_callback_cannot_bypass_allowlist(self):
        event = update("", uid=99)
        event.message = None
        event.callback_query = SimpleNamespace(data="set:mode:coding", answer=AsyncMock())
        await self.handlers.callback(event, None)
        self.assertEqual((await self.store.prefs(99))["mode"], "general")

    async def test_all_documented_commands_reply(self):
        for cmd, _, _ in COMMANDS:
            event = await self.command("/" + cmd)
            event.message.reply_text.assert_awaited()

    async def test_existing_webhook_blocks_startup(self):
        app = build_application(settings(expected_username="testbot"), self.store, self.provider)
        stub = SimpleNamespace(bot=SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(username="testbot")),
            get_webhook_info=AsyncMock(return_value=SimpleNamespace(url="https://example.test/webhook"))),)
        with self.assertRaises(StartupError):
            await app.post_init(stub)

    async def test_wrong_identity_blocks_startup(self):
        app = build_application(settings(expected_username="expectedbot"), self.store, self.provider)
        stub = SimpleNamespace(bot=SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(username="differentbot"))))
        with self.assertRaises(StartupError):
            await app.post_init(stub)

    async def test_startup_registers_complete_command_menus(self):
        app = build_application(settings(expected_username="testbot"), self.store, self.provider)
        bot = SimpleNamespace(get_me=AsyncMock(return_value=SimpleNamespace(username="testbot")),
            get_webhook_info=AsyncMock(return_value=SimpleNamespace(url="")), set_my_commands=AsyncMock())
        await app.post_init(SimpleNamespace(bot=bot))
        self.assertEqual(bot.set_my_commands.await_count, 2)
        for call in bot.set_my_commands.call_args_list:
            self.assertEqual([command.command for command in call.args[0]], [cmd for cmd, _, _ in COMMANDS])

    async def test_empty_allowlist_is_setup_only(self):
        self.handlers.settings = settings(allowed=frozenset())
        await self.command("/note should not save")
        await self.handlers.text(update("should not call AI"), None)
        self.assertEqual((await self.store.items(1, "note")), [])
        self.provider.answer.assert_not_awaited()
        event = await self.command("/whoami")
        self.assertIn("1", event.message.reply_text.call_args.args[0])

    async def test_long_input_and_missing_model_skip_provider(self):
        await self.handlers.text(update("x" * 2001), None)
        self.handlers.settings = settings(model="")
        await self.handlers.text(update("hello"), None)
        self.provider.answer.assert_not_awaited()
        self.assertEqual((await self.store.used(1)), 0)

    async def test_conflict_stops_polling(self):
        from unittest.mock import Mock
        stop = Mock()
        context = SimpleNamespace(error=Conflict("conflict"), application=SimpleNamespace(stop_running=stop))
        await self.handlers.error(None, context)
        stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
