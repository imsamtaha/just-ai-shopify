"""Regression tests and an offline bot lifecycle smoke test. No network access."""
import asyncio
import json
import io
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram import Update
from telegram.request import BaseRequest

from just_ai.config import Settings, load_settings
from just_ai.runtime import build_application
from just_ai.store import Store


class AsyncPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'workspace.sqlite3'
        self.store = Store(self.path)
        await self.store.initialize()

    async def asyncTearDown(self):
        await self.store.close()
        self.tmp.cleanup()

    async def test_memory_is_scoped_to_both_chat_and_user(self):
        await self.store.exchange(1, 'chat A', 'answer A', chat_id=10)
        await self.store.exchange(1, 'chat B', 'answer B', chat_id=20)
        await self.store.exchange(2, 'user B', 'answer C', chat_id=10)
        self.assertEqual((await self.store.history(1, 10))[0]['content'], 'chat A')
        await self.store.reset(1, 10)
        self.assertEqual(await self.store.history(1, 10), [])
        self.assertEqual(len(await self.store.history(1, 20)), 2)
        self.assertEqual(len(await self.store.history(2, 10)), 2)
        await self.store.forget(1)
        self.assertEqual(await self.store.history(1, 20), [])
        self.assertEqual(len(await self.store.history(2, 10)), 2)

    async def test_concurrent_quota_reservations_cannot_exceed_limit(self):
        results = await asyncio.gather(*(self.store.reserve(1, 3) for _ in range(20)))
        self.assertEqual(sum(results), 3)
        self.assertEqual(await self.store.used(1), 3)

    async def test_old_database_migrates_without_losing_records(self):
        await self.store.close()
        legacy = Path(self.tmp.name) / 'legacy.sqlite3'
        with closing(sqlite3.connect(legacy)) as db:
            db.execute('CREATE TABLE messages (id INTEGER PRIMARY KEY, user_id INTEGER, role TEXT, content TEXT)')
            db.execute("INSERT INTO messages(user_id,role,content) VALUES (1,'user','keep me')")
            db.commit()
        self.store = Store(legacy)
        await self.store.initialize()
        self.assertEqual(await self.store.history(1, 1), [{'role': 'user', 'content': 'keep me'}])
        self.assertEqual(await self.store.history(1, 2), [])
        await self.store.close()
        await self.store.initialize()
        self.assertEqual(len(await self.store.history(1, 1)), 1)

    async def test_failed_transaction_rolls_back(self):
        with self.assertRaises(RuntimeError):
            async with self.store._transaction() as db:
                await db.execute("INSERT INTO items(user_id,kind,content) VALUES (1,'note','rollback')")
                raise RuntimeError('test failure')
        self.assertEqual(await self.store.items(1, 'note'), [])

    async def test_startup_and_shutdown_are_idempotent(self):
        await self.store.initialize()
        await self.store.add(1, 'note', 'saved')
        await self.store.close()
        await self.store.close()
        await self.store.initialize()
        self.assertEqual((await self.store.items(1, 'note'))[0]['content'], 'saved')


class OfflineTelegram(BaseRequest):
    """Only handles known Telegram methods in memory; never opens a socket."""
    def __init__(self):
        self.calls = []
        self.replies = []

    @property
    def read_timeout(self):
        return 5

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def do_request(self, url, method, request_data=None, **kwargs):
        endpoint = url.rsplit('/', 1)[-1]
        self.calls.append(endpoint)
        params = request_data.parameters if request_data else {}
        if endpoint == 'getMe':
            result = {'id': 123456789, 'is_bot': True, 'first_name': 'JUST AI', 'username': 'JustAI_chatbot'}
        elif endpoint == 'getWebhookInfo':
            result = {'url': '', 'pending_update_count': 0, 'has_custom_certificate': False}
        elif endpoint == 'setMyCommands':
            result = True
        elif endpoint == 'sendMessage':
            self.replies.append(params['text'])
            result = {'message_id': len(self.replies), 'date': int(datetime.now(timezone.utc).timestamp()),
                      'chat': {'id': params['chat_id'], 'type': 'private'}, 'text': params['text']}
        else:
            raise AssertionError('Unexpected Telegram method in offline smoke test')
        return 200, json.dumps({'ok': True, 'result': result}).encode()


class ApplicationSmokeTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_offline_lifecycle_commands_memory_and_shutdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'smoke.sqlite3')
            fake = OfflineTelegram()
            provider = SimpleNamespace(answer=AsyncMock(return_value='Local test answer'), close=AsyncMock())
            settings = Settings(token='123456789:' + 'A' * 35, api_key='offline', model='offline',
                                allowed=frozenset({1}), cooldown=0)
            app = build_application(settings, store, provider, request=fake)
            errors = []
            async def capture_error(update, context):
                errors.append(type(context.error).__name__)
            app.add_error_handler(capture_error)
            try:
                await app.initialize()
                await app.post_init(app)
                await app.start()
                self.assertEqual(fake.replies, [], 'Startup must not send unsolicited chat messages')
                commands = ['/start', '/help', '/note private note', '/notes', '/task Ship bot',
                            '/tasks', '/settings mode coding', '/settings', '/settings language invalid',
                            '/prompt Draft an email', 'Hello', '/history', '/done 2', '/tasks']
                for index, text in enumerate(commands, 1):
                    message = {'message_id': index, 'date': int(datetime.now(timezone.utc).timestamp()),
                               'chat': {'id': 1, 'type': 'private'},
                               'from': {'id': 1, 'is_bot': False, 'first_name': 'Offline test'}, 'text': text}
                    if text.startswith('/'):
                        message['entities'] = [{'type': 'bot_command', 'offset': 0, 'length': len(text.split()[0])}]
                    event = Update.de_json({'update_id': index, 'message': message}, app.bot)
                    before = len(fake.replies)
                    await app.process_update(event)
                    self.assertGreater(len(fake.replies), before, text)
                self.assertEqual(errors, [])
                self.assertEqual((await store.prefs(1))['mode'], 'coding')
                self.assertEqual((await store.prefs(1))['language'], 'auto')
                self.assertEqual(len(await store.history(1, 1)), 4)
                self.assertEqual(await store.history(1, 999), [])
                self.assertEqual(len(provider.answer.call_args.args[1]), 3)
                self.assertEqual((await store.items(1, 'task'))[0]['done'], 1)
                self.assertNotIn('deleteWebhook', fake.calls)
                self.assertNotIn('getUpdates', fake.calls)
            finally:
                if app.running:
                    await app.stop()
                await app.shutdown()
                await app.post_shutdown(app)
            self.assertIsNone(store.db)
            provider.close.assert_awaited_once()

    async def test_missing_credentials_skip_live_network(self):
        import doctor
        from just_ai.config import ConfigError
        with patch.object(doctor, 'load_settings', side_effect=ConfigError('Missing token')), \
             patch.object(doctor, 'remote', new_callable=AsyncMock) as remote, \
             patch.object(doctor, 'database_check', new_callable=AsyncMock, return_value=True), \
             patch('sys.argv', ['doctor.py', '--live']):
            # doctor.main owns its loop; run off this test's loop.
            result = await asyncio.to_thread(doctor.main)
        self.assertEqual(result, 1)
        remote.assert_not_awaited()


class IdentityTests(unittest.TestCase):
    def test_configuration_wizard_saves_secrets_without_echoing(self):
        import configure
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            token = '123456789:' + 'B' * 35
            key = 'test-only-secret-never-print'
            captured = io.StringIO()
            with patch.object(configure, 'ROOT', root), \
                 patch('sys.stdin.isatty', return_value=True), \
                 patch.object(configure.getpass, 'getpass', side_effect=[token, key]), \
                 patch('builtins.input', side_effect=['openrouter', 'openai/gpt-4.1-mini', '1', 'myconfirmedbot']), \
                 redirect_stdout(captured):
                result = configure.main()
            self.assertEqual(result, 0)
            self.assertNotIn(token, captured.getvalue())
            self.assertNotIn(key, captured.getvalue())
            settings = load_settings(root, {})
            self.assertEqual(settings.token, token)
            self.assertEqual(settings.api_key, key)
            self.assertEqual(settings.provider, 'openrouter')
            self.assertEqual(settings.model, 'openai/gpt-4.1-mini')
            self.assertEqual(settings.allowed, frozenset({1}))
            self.assertEqual(settings.expected_username, 'myconfirmedbot')
            self.assertEqual(list(root.glob('.env-*')), [])

    def test_named_bot_is_default_and_secrets_are_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = load_settings(Path(tmp), {'TELEGRAM_BOT_TOKEN': '123456789:' + 'A' * 35})
            self.assertEqual(settings.expected_username, 'justai_chatbot')
            self.assertNotIn(settings.token, repr(settings))


if __name__ == '__main__':
    unittest.main()
