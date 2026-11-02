import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from just_ai.config import ConfigError
from just_ai.shopify_config import SHOP_ID, SHOP_DOMAIN, ShopifySettings, load_shopify_settings
from just_ai.shopify_api import ShopifyClient, ShopifyError
from just_ai.shopify_controls import ShopifyControls, entity_id
from just_ai.store import Store
from just_ai.handlers import Handlers
from test_bot import settings as bot_settings, update


def settings(**kwargs):
    return replace(ShopifySettings(enabled=True, owners=frozenset({1}), token="test-private-token"), **kwargs)


PRODUCT = {"id": "gid://shopify/Product/10", "title": "A kit", "status": "ACTIVE", "descriptionHtml": "<p>Old</p>", "updatedAt": "2026-10-26T00:00:00Z", "variants": {"nodes": [], "pageInfo": {"hasNextPage": False}}}
VARIANT = {"id": "gid://shopify/ProductVariant/20", "title": "Default", "price": "20.00", "product": {"id": PRODUCT["id"], "title": "A kit", "updatedAt": PRODUCT["updatedAt"]}}
ORDER = {"id": "gid://shopify/Order/30", "name": "#1001", "updatedAt": "2026-10-26T00:00:00Z", "createdAt": "2026-10-26T00:00:00Z", "note": "", "closed": False, "cancelledAt": None, "test": False, "canMarkAsPaid": True, "paymentGatewayNames": ["Whish Money"], "displayFinancialStatus": "PENDING", "displayFulfillmentStatus": "UNFULFILLED", "totalPriceSet": {"shopMoney": {"amount": "20.00", "currencyCode": "USD"}}, "totalOutstandingSet": {"shopMoney": {"amount": "20.00", "currencyCode": "USD"}}, "lineItems": {"nodes": [{"name": "A kit", "quantity": 1}], "pageInfo": {"hasNextPage": False}}}
IDENTITY = {"shop": {"id": SHOP_ID, "name": "Just AI", "myshopifyDomain": "njcr1h-zx.myshopify.com", "currencyCode": "USD"}, "currentAppInstallation": {"accessScopes": [{"handle": s} for s in ("write_products", "write_orders")]}}


class ConfigTests(unittest.TestCase):
    def test_disabled_config_does_not_read_or_validate_secrets(self):
        with tempfile.TemporaryDirectory() as root:
            conf = load_shopify_settings(Path(root), {"SHOPIFY_ENABLED": "false", "SHOPIFY_ADMIN_ACCESS_TOKEN": "secret"})
            self.assertFalse(conf.ready)
            self.assertNotIn("secret", repr(conf))

    def test_owners_must_be_positive_and_base_authorized(self):
        with tempfile.TemporaryDirectory() as root:
            values = {"SHOPIFY_ENABLED": "true", "SHOPIFY_ADMIN_ACCESS_TOKEN": "private-token", "ALLOWED_USER_IDS": "1"}
            for owners in ("", "-1", "abc", "2", "1,2"):
                with self.assertRaises(ConfigError):
                    load_shopify_settings(Path(root), values | {"SHOPIFY_OWNER_IDS": owners})
            conf = load_shopify_settings(Path(root), values | {"SHOPIFY_OWNER_IDS": "1"})
            self.assertTrue(conf.ready)
            self.assertNotIn("private-token", repr(conf))

    def test_host_version_and_auth_method_are_validated(self):
        with tempfile.TemporaryDirectory() as root:
            values = {"SHOPIFY_ENABLED": "true", "SHOPIFY_OWNER_IDS": "1", "ALLOWED_USER_IDS": "1", "SHOPIFY_ADMIN_ACCESS_TOKEN": "private-token"}
            for changes in ({"SHOPIFY_SHOP_DOMAIN": "attacker.example"}, {"SHOPIFY_EXPECTED_SHOP_ID": "other"}, {"SHOPIFY_API_VERSION": "unstable"}, {"SHOPIFY_CLIENT_ID": "another-auth"}):
                with self.assertRaises(ConfigError):
                    load_shopify_settings(Path(root), values | changes)

    def test_entity_ids_cannot_inject_queries(self):
        self.assertEqual(entity_id("20", "ProductVariant"), VARIANT["id"])
        for value in ("20 } mutation", "-1", "0", PRODUCT["id"], "https://example.com"):
            with self.assertRaises(ValueError):
                entity_id(value, "ProductVariant")


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_store_identity_is_checked_before_any_record_access(self):
        seen = []
        def respond(request):
            seen.append(json.loads(request.content))
            body = copy.deepcopy(IDENTITY)
            body["shop"]["id"] = "gid://shopify/Shop/999"
            return httpx.Response(200, json={"data": body})
        client = ShopifyClient(settings(), httpx.MockTransport(respond))
        try:
            with self.assertRaisesRegex(ShopifyError, "wrong_shop"):
                await client.query("products")
            self.assertEqual(len(seen), 1)
            self.assertIn("BotIdentity", seen[0]["query"])
        finally:
            await client.close()

    async def test_fixed_host_and_scopes_fail_closed(self):
        seen = []
        def respond(request):
            self.assertEqual(request.url.host, SHOP_DOMAIN)
            self.assertEqual(request.headers["X-Shopify-Access-Token"], "test-private-token")
            seen.append(request)
            body = copy.deepcopy(IDENTITY)
            body["currentAppInstallation"]["accessScopes"] = []
            return httpx.Response(200, json={"data": body})
        client = ShopifyClient(settings(), httpx.MockTransport(respond))
        try:
            with self.assertRaisesRegex(ShopifyError, "missing_scope"):
                await client.mutate("order_note", {"input": {"id": ORDER["id"], "note": "x"}})
            self.assertEqual(len(seen), 1)
        finally:
            await client.close()
        client = ShopifyClient(settings(domain="untrusted.example"), httpx.MockTransport(respond))
        try:
            with self.assertRaisesRegex(ShopifyError, "wrong_shop"):
                await client.identity()
            self.assertEqual(len(seen), 1)
        finally:
            await client.close()

    async def test_mutation_timeout_is_never_retried_or_exposed(self):
        writes = []
        def respond(request):
            if "BotIdentity" in json.loads(request.content)["query"]:
                return httpx.Response(200, json={"data": IDENTITY})
            writes.append(request)
            raise httpx.ReadTimeout("PRIVATE_SECRET", request=request)
        client = ShopifyClient(settings(), httpx.MockTransport(respond))
        try:
            with self.assertRaisesRegex(ShopifyError, "outcome_unknown") as exc:
                await client.mutate("order_note", {"input": {"id": ORDER["id"], "note": "x"}})
            self.assertEqual(len(writes), 1)
            self.assertNotIn("PRIVATE_SECRET", str(exc.exception))
        finally:
            await client.close()

    async def test_upstream_errors_and_redirects_never_leak(self):
        for status, body in [(302, {}), (403, {}), (500, {}), (200, {"errors": [{"message": "PRIVATE_SECRET"}]}), (200, ["PRIVATE_SECRET"])]:
            seen = []
            def respond(request):
                seen.append(request)
                return httpx.Response(status, json=body, headers={"Location": "https://attacker.example"})
            client = ShopifyClient(settings(), httpx.MockTransport(respond))
            try:
                with self.assertRaises(ShopifyError) as exc:
                    await client.identity()
                self.assertNotIn("PRIVATE_SECRET", str(exc.exception))
                self.assertEqual(len(seen), 1)
            finally:
                await client.close()

    async def test_client_credentials_refresh_and_keep_original_shop_identity(self):
        clock = [0]
        grants, identities = [], []
        def respond(request):
            if request.url.path.endswith("access_token"):
                grants.append(request)
                return httpx.Response(200, json={"access_token": "short-lived-private-token", "expires_in": 120})
            identities.append(request)
            return httpx.Response(200, json={"data": IDENTITY})
        client = ShopifyClient(settings(token="", client_id="private-id", client_secret="private-secret"), httpx.MockTransport(respond), clock=lambda: clock[0])
        try:
            result = await client.identity()
            self.assertEqual(result["id"], SHOP_ID)
            await client.identity()
            self.assertEqual(len(grants), 1)
            clock[0] = 61
            await client.identity()
            self.assertEqual(len(grants), 2)
            self.assertEqual(len(identities), 2)
            self.assertTrue(all(r.url.host == SHOP_DOMAIN for r in grants + identities))
        finally:
            await client.close()

    async def test_user_errors_are_rejected_without_echoing_customer_text(self):
        def respond(request):
            if "BotIdentity" in json.loads(request.content)["query"]:
                return httpx.Response(200, json={"data": IDENTITY})
            return httpx.Response(200, json={"data": {"orderUpdate": {"order": None, "userErrors": [{"message": "PRIVATE_CUSTOMER_TEXT"}]}}})
        client = ShopifyClient(settings(), httpx.MockTransport(respond))
        try:
            with self.assertRaisesRegex(ShopifyError, "rejected") as exc:
                await client.mutate("order_note", {"input": {"id": ORDER["id"]}})
            self.assertNotIn("PRIVATE_CUSTOMER", str(exc.exception))
        finally:
            await client.close()


class ControlsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "state.sqlite3")
        await self.store.initialize()
        self.clock = [100]
        self.data = {"product": copy.deepcopy(PRODUCT), "variant": copy.deepcopy(VARIANT), "order": copy.deepcopy(ORDER)}
        async def query(kind, variables):
            if kind == "orders":
                return {"orders": {"nodes": [copy.deepcopy(self.data["order"])], "pageInfo": {"hasNextPage": False}}}
            return {"node" if kind == "variant" else kind: copy.deepcopy(self.data[kind])}
        async def mutate(action, variables):
            if action == "product_update":
                self.data["product"].update(variables["product"])
            elif action == "price":
                self.data["variant"]["price"] = variables["variants"][0]["price"]
            elif action == "order_note":
                self.data["order"]["note"] = variables["input"]["note"]
            elif action == "mark_paid":
                self.data["order"]["canMarkAsPaid"] = False
                self.data["order"]["totalOutstandingSet"]["shopMoney"]["amount"] = "0.00"
            elif action in ("archive_order", "reopen_order"):
                self.data["order"]["closed"] = action == "archive_order"
            return {"id": "test"}
        self.client = SimpleNamespace(query=AsyncMock(side_effect=query), mutate=AsyncMock(side_effect=mutate), identity=AsyncMock(return_value=IDENTITY["shop"]), close=AsyncMock())
        self.send = AsyncMock()
        self.controls = ShopifyControls(settings(), self.store, self.send, self.client, clock=lambda: self.clock[0])

    async def asyncTearDown(self):
        await self.controls.close()
        await self.store.close()
        self.temp.cleanup()

    async def prepare(self, command="product_title", text="10 Better kit"):
        await self.controls.command(update(), command, text, False)
        self.assertEqual(len(self.controls.pending), 1)
        return next(iter(self.controls.pending))

    async def confirm(self, token, uid=1):
        await self.controls.callback(update(uid=uid), "shop:yes:" + token, False)

    async def test_preview_does_not_mutate_and_confirm_applies_once(self):
        token = await self.prepare()
        self.client.mutate.assert_not_awaited()
        await self.confirm(token)
        await self.confirm(token)
        self.assertEqual(self.client.mutate.await_count, 1)
        self.assertEqual(self.data["product"]["title"], "Better kit")
        self.assertEqual((await self.store.shop_history())[0]["status"], "verified")

    async def test_only_owner_in_private_chat_can_read_or_confirm(self):
        for event in (update(uid=2), update(chat_type="group")):
            await self.controls.command(event, "shop", "", False)
        self.client.identity.assert_not_awaited()
        token = await self.prepare()
        await self.confirm(token, uid=2)
        self.assertIn(token, self.controls.pending)
        event = update()
        event.effective_chat.id = 999
        await self.controls.callback(event, "shop:yes:" + token, False)
        self.client.mutate.assert_not_awaited()
        await self.confirm(token)
        self.client.mutate.assert_awaited_once()

    async def test_expired_cancelled_and_superseded_confirmation_cannot_mutate(self):
        expired = await self.prepare()
        self.clock[0] += 121
        await self.confirm(expired)
        cancelled = await self.prepare()
        await self.controls.callback(update(), "shop:no:" + cancelled, False)
        await self.confirm(cancelled)
        old = await self.prepare()
        new = await self.prepare(text="10 Latest")
        await self.confirm(old)
        self.client.mutate.assert_not_awaited()
        await self.confirm(new)
        self.assertEqual(self.data["product"]["title"], "Latest")

    async def test_changed_record_is_not_overwritten(self):
        token = await self.prepare()
        self.data["product"]["title"] = "Another edit"
        await self.confirm(token)
        self.client.mutate.assert_not_awaited()
        self.assertFalse(await self.store.shop_history())

    async def test_unknown_outcome_persists_block_until_owner_reviews(self):
        token = await self.prepare()
        self.client.mutate.side_effect = ShopifyError("outcome_unknown")
        await self.confirm(token)
        self.assertTrue(await self.store.shop_unresolved(PRODUCT["id"]))
        await self.controls.command(update(), "product_title", "10 Retry", False)
        self.assertFalse(self.controls.pending)
        await self.store.close()
        await self.store.initialize()
        self.assertTrue(await self.store.shop_unresolved(PRODUCT["id"]))
        row = (await self.store.shop_history())[0]
        token = await self.prepare("shopack", str(row["id"]))
        await self.confirm(token)
        self.assertFalse(await self.store.shop_unresolved(PRODUCT["id"]))
        self.assertEqual(self.client.mutate.await_count, 1)

    async def test_failed_readback_does_not_report_success(self):
        token = await self.prepare()
        self.client.mutate.side_effect = None
        self.client.mutate.return_value = {"id": PRODUCT["id"]}
        await self.confirm(token)
        self.assertEqual((await self.store.shop_history())[0]["status"], "verification_failed")
        self.assertNotIn("Saved and verified", self.send.call_args.args[1])

    async def test_failed_preview_delivery_discards_confirmation(self):
        self.send.side_effect = RuntimeError("Telegram delivery failed")
        with self.assertRaises(RuntimeError):
            await self.controls.command(update(), "product_title", "10 Title", False)
        self.assertFalse(self.controls.pending)
        self.client.mutate.assert_not_awaited()

    async def test_money_validation_and_successful_decimal_readback(self):
        for amount in ("-1", "0", "nan", "inf", "1e3", "1.234", "1000000", "20 USD"):
            await self.controls.command(update(), "price", "20 " + amount, False)
            self.assertFalse(self.controls.pending)
        token = await self.prepare("price", "20 29.9")
        await self.confirm(token)
        self.assertEqual(self.data["variant"]["price"], "29.90")

    async def test_description_is_escaped_and_replace_warning_is_visible(self):
        token = await self.prepare("product_description", "10 <script>bad()</script>\nنموذج")
        self.assertIn("entire description", self.send.call_args.args[1])
        await self.confirm(token)
        self.assertEqual(self.data["product"]["descriptionHtml"], "<p>&lt;script&gt;bad()&lt;/script&gt;<br>نموذج</p>")

    async def test_mark_paid_requires_eligible_whish_and_explicit_confirmation(self):
        self.data["order"]["paymentGatewayNames"] = ["Credit Card"]
        await self.controls.command(update(), "mark_paid", "#1001", False)
        self.assertFalse(self.controls.pending)
        self.data["order"]["paymentGatewayNames"] = ["Whish Money"]
        token = await self.prepare("mark_paid", "#1001")
        self.assertIn("independently verifying", self.send.call_args.args[1])
        self.client.mutate.assert_not_awaited()
        await self.confirm(token)
        self.assertFalse(self.data["order"]["canMarkAsPaid"])
        await self.controls.command(update(), "mark_paid", "#1001", False)
        self.assertFalse(self.controls.pending)
        self.assertEqual(self.client.mutate.await_count, 1)

    async def test_order_note_and_archive_reopen_are_verified(self):
        for command, text in (("order_note", "#1001 تم التحقق\nمن الدفع"), ("archive_order", "#1001"), ("reopen_order", "#1001")):
            token = await self.prepare(command, text)
            await self.confirm(token)
        self.assertEqual(self.data["order"]["note"], "تم التحقق\nمن الدفع")
        self.assertFalse(self.data["order"]["closed"])
        self.assertTrue(all(x["status"] == "verified" for x in await self.store.shop_history()))

    async def test_base_allowlist_and_stale_guard_still_apply(self):
        provider = SimpleNamespace(answer=AsyncMock(), close=AsyncMock())
        handlers = Handlers(bot_settings(), self.store, provider, settings())
        handlers.shopify = self.controls
        await handlers.command(update("/shop", uid=99), None)
        await handlers.command(update("/shop", age=400), None)
        self.client.identity.assert_not_awaited()
        await handlers.command(update("/shop"), None)
        self.client.identity.assert_awaited_once()
        provider.answer.assert_not_awaited()
        self.assertFalse(await self.store.history(1))

    async def test_callbacks_fit_telegram_limit_and_arabic_menu(self):
        token = await self.prepare()
        keyboard = self.send.call_args.args[2]
        self.assertTrue(all(len(b.callback_data.encode()) <= 64 for row in keyboard.inline_keyboard for b in row))
        await self.controls.callback(update(), "shop:no:" + token, True)
        self.assertIn("أُلغي", self.send.call_args.args[1])

    async def test_audit_survives_forget_without_content_or_credentials(self):
        token = await self.prepare("order_note", "#1001 Private customer note")
        await self.confirm(token)
        await self.store.forget(1)
        rows = await self.store.shop_history()
        self.assertEqual(len(rows), 1)
        self.assertNotIn("Private customer", json.dumps(rows))
        self.assertNotIn("test-private-token", json.dumps(rows))


class WizardTests(unittest.TestCase):
    def test_shopify_wizard_uses_hidden_prompts_and_retains_existing_settings(self):
        import configure_shopify
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / ".env").write_text('TELEGRAM_BOT_TOKEN="preserved"\nALLOWED_USER_IDS="2"\n', encoding="utf-8")
            with patch.object(configure_shopify, "ROOT", root), patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["1", "2"]), patch("getpass.getpass", return_value="hidden-admin-token"), patch.object(configure_shopify, "protect_file") as protect, patch("builtins.print") as output:
                self.assertEqual(configure_shopify.main(), 0)
                self.assertNotIn("hidden-admin-token", str(output.call_args_list))
                protect.assert_called_once()
            conf = load_shopify_settings(root, {})
            self.assertEqual(conf.owners, frozenset({1}))
            self.assertEqual(conf.token, "hidden-admin-token")
            self.assertIn('TELEGRAM_BOT_TOKEN="preserved"', (root / ".env").read_text())
