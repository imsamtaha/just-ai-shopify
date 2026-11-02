import asyncio
from dataclasses import replace
import hashlib
import hmac
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import httpx
from just_ai.config import ConfigError, Settings, load_settings
from just_ai.meta_config import MetaSettings, load_meta
from just_ai.meta_channels import Incoming, Inbox, incoming, reply, send_reply, valid_signature
from meta_server import Bridge, handler_for


def config():
    return MetaSettings(app_secret="test-app-secret", verify_token="test-verify-token-32-characters-long",
                        whatsapp_token="test-wa-secret", page_token="test-page-secret",
                        phone_id="111", page_id="222", version="v99.0",
                        whatsapp_users=frozenset({"123"}), messenger_users=frozenset({"456"}))


def wa(stamp, sender="123", mid="wa-message"):
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": {
        "metadata": {"phone_number_id": "111"}, "messages": [{"type": "text", "id": mid,
        "from": sender, "timestamp": str(stamp), "text": {"body": "/atlas"}}]}}]}]}


def messenger(stamp):
    return {"object": "page", "entry": [{"id": "222", "messaging": [{"sender": {"id": "456"},
        "recipient": {"id": "222"}, "timestamp": stamp * 1000,
        "message": {"mid": "page-message", "text": "/training"}}]}]}


def signed(raw):
    return "sha256=" + hmac.new(config().app_secret.encode(), raw, hashlib.sha256).hexdigest()


class MetaTests(unittest.TestCase):
    def test_meta_configuration_and_no_telegram_dependency(self):
        self.assertFalse(load_meta(values={}).webhook_ready)
        for value in ("v1/../../me", "99"):
            with self.assertRaises(ConfigError):
                load_meta(values={"META_GRAPH_VERSION": value})
        with self.assertRaises(ConfigError):
            load_meta(values={"META_PUBLIC_URL": "http://example.com"})
        with tempfile.TemporaryDirectory() as tmp:
            result = load_settings(Path(tmp), {}, require_telegram=False)
            self.assertFalse(result.ai_ready)
        self.assertNotIn("test-app-secret", repr(config()))
        self.assertNotIn("test-page-secret", repr(config()))

    def test_signature_rejects_tampering_and_missing_secret(self):
        raw = b'{"object":"page"}'
        self.assertTrue(valid_signature(raw, signed(raw), config().app_secret))
        self.assertFalse(valid_signature(raw + b' ', signed(raw), config().app_secret))
        self.assertFalse(valid_signature(raw, signed(raw), ""))
        self.assertFalse(valid_signature(raw, "عربي", config().app_secret))

    def test_channel_scope_and_freshness(self):
        self.assertEqual(incoming(wa(1000), config(), now=1001)[0].channel, "whatsapp")
        self.assertEqual(incoming(messenger(1000), config(), now=1001)[0].channel, "messenger")
        self.assertFalse(incoming(wa(1000), replace(config(), phone_id="999"), now=1001))
        self.assertFalse(incoming(messenger(1000), replace(config(), page_id="999"), now=1001))
        self.assertFalse(incoming(wa(1000), config(), now=1500))
        echoed = messenger(1000)
        echoed['entry'][0]['messaging'][0]['message']['is_echo'] = True
        self.assertFalse(incoming(echoed, config(), now=1001))

    def test_durable_deduplication_and_no_retry_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'inbox.sqlite3'
            inbox = Inbox(path)
            event = Incoming('whatsapp', 'message1', '123', '/atlas', 1000)
            inbox.enqueue([event, event], now=1000)
            self.assertEqual(inbox.claim(), event)
            self.assertIsNone(inbox.claim())
            restarted = Inbox(path)
            restarted.enqueue([event], now=1001)
            self.assertIsNone(restarted.claim())
            with restarted.connect() as db:
                self.assertEqual(db.execute('SELECT state,text FROM inbox').fetchone(), ('uncertain', ''))

    def test_sender_limits_are_scoped_per_channel(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Inbox(Path(tmp) / 'db')
            events = [Incoming('whatsapp', str(i), '123', '/atlas', 1000) for i in range(31)]
            events.append(Incoming('messenger', 'other', '123', '/atlas', 1000))
            inbox.enqueue(events, now=1000)
            with inbox.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM inbox').fetchone()[0], 31)

    def test_webhook_http_challenge_auth_and_no_private_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Inbox(Path(tmp) / 'db')
            bridge = Bridge(config(), Settings(token='', api_key=''), inbox)
            server = ThreadingHTTPServer(('127.0.0.1', 0), handler_for(bridge))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = 'http://127.0.0.1:' + str(server.server_address[1])
                with httpx.Client(base_url=base, trust_env=False) as client:
                    params = {'hub.mode': 'subscribe', 'hub.verify_token': config().verify_token, 'hub.challenge': '12345'}
                    self.assertEqual(client.get('/meta/webhook', params=params).text, '12345')
                    self.assertEqual(client.get('/meta/webhook').status_code, 403)
                    self.assertEqual(client.get('/.env').status_code, 404)
                    raw = json.dumps(wa(int(time.time()))).encode()
                    self.assertEqual(client.post('/meta/webhook', content=raw, headers={'Content-Type': 'application/json'}).status_code, 403)
                    self.assertIsNone(inbox.claim())
                    headers = {'Content-Type': 'application/json', 'X-Hub-Signature-256': signed(raw)}
                    self.assertEqual(client.post('/meta/webhook', content=raw, headers=headers).status_code, 200)
                    self.assertEqual(inbox.claim().sender, '123')
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_unapproved_sender_never_enters_inbox_for_atlas(self):
        with tempfile.TemporaryDirectory() as tmp:
            inbox = Inbox(Path(tmp) / 'db')
            bridge = Bridge(config(), Settings(token='', api_key=''), inbox)
            raw = json.dumps(wa(int(time.time()), sender='999')).encode()
            self.assertEqual(bridge.receive(raw, signed(raw)), 200)
            self.assertIsNone(inbox.claim())

    def test_send_targets_correct_account_without_secrets_in_url(self):
        for channel, account, token in [('whatsapp', '111', 'test-wa-secret'), ('messenger', '222', 'test-page-secret')]:
            with self.subTest(channel=channel):
                def respond(request):
                    self.assertEqual(str(request.url), f'https://graph.facebook.com/v99.0/{account}/messages')
                    self.assertEqual(request.headers['Authorization'], 'Bearer ' + token)
                    data = json.loads(request.content)
                    self.assertEqual(data.get('to') or data['recipient']['id'], '123')
                    return httpx.Response(200, json={'message_id': 'ok', 'messages': [{'id': 'ok'}]})
                send_reply(Incoming(channel, 'mid', '123', '/atlas', time.time()), 'hello', config(), httpx.MockTransport(respond))


class ReplyTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_reports_require_channel_authorization(self):
        event = Incoming('messenger', 'mid', '123', '/atlas', time.time())
        with patch('just_ai.meta_channels.atlas.summary') as summary:
            self.assertIsNone(await reply(event, config(), Settings(token='', api_key='')))
            summary.assert_not_called()
        text = await reply(replace(event, text='/whoami'), config(), Settings(token='', api_key=''))
        self.assertIn('123', text)

    async def test_reports_work_without_ai_and_no_fabricated_answer(self):
        event = Incoming('whatsapp', 'mid', '123', '/training', time.time())
        with patch('just_ai.meta_channels.atlas.summary', return_value='Recorded report'):
            self.assertEqual(await reply(event, config(), Settings(token='', api_key='')), 'Recorded report')
        text = await reply(replace(event, text='What is ATLAS?'), config(), Settings(token='', api_key=''))
        self.assertIn('paused', text)


if __name__ == '__main__':
    unittest.main()
