# Telegram Shopify controls — validation, 26 October 2026

Status: implemented and tested locally; live activation is blocked by missing local credentials.

- Existing package: just-ai-bot-v2; expected bot username JustAI_chatbot. The owner was asked to confirm this username; no response was available during implementation.
- Public source backup: work/telegram-shopify-before in the Shopify task workspace. Existing ATLAS/AI functionality was retained. No .env credentials were changed.
- Baseline: 42 tests ran; 40 passed and 2 existing menu-language tests failed because they assumed the Skills button was first after the ATLAS menu had already been added. These assertions now select the button by callback action, preserving the language checks.
- Final: 67 tests passed in 37.873 seconds, including the existing offline application lifecycle and 25 new Shopify tests. Tests use mocked Telegram/Shopify responses and temporary databases; they did not change live Shopify records or send Telegram messages.
- Shopify GraphQL: all 12 operations were accepted by the bundled official validator, resolved API version 2026-10, artifact telegram-shopify-operations revision 1. The connector validator returned skipped, so the bundled validator was used to obtain an actual success result. No production mutation was used as a test.
- Source compilation passed. pip check: No broken requirements found. SQLite startup/integrity: PASS.
- Security checks include explicit numeric owner IDs, private-chat and base allowlist enforcement, stale command blocking, fixed Shopify host and shop-ID verification, credential refresh, secret-safe errors, no redirects, no mutation retries, two-minute owner/chat-bound confirmations, replay prevention, changed-record detection, readback verification and persistent blocks on uncertain outcomes.
- Payment test coverage: only eligible Whish orders can be marked paid, after explicit confirmation that funds were independently verified. This records payment only; it cannot check Whish or transfer funds.
- shopify_doctor.py --live: Shopify enabled False, owner accounts 0, credentials False; stopped without a network request.
- doctor.py --live: database PASS, then stopped because TELEGRAM_BOT_TOKEN is not configured. No live Telegram identity or message delivery has been verified.
- Portable release uses the existing explicit public-file allowlist plus the integration files. It excludes .env, databases, caches, virtual environments and credentials. ZIP CRC and SHA-256 manifest verified.

Known limits: refunds, cancellations, fulfillment, product creation, inventory, discounts, media uploads, payment setup and themes open Shopify Admin from the bot. They are not bot-executed actions. Only first 20 variants/line items appear in detail views; Admin links expose the rest. Pagination is available for order/product lists. Shopify's default order-access restrictions apply unless the app receives read_all_orders. There is no atomic compare-and-swap between pre-confirmation read and mutation, so simultaneous administrator edits remain possible. No background service was installed; the computer must remain awake with the bot running.

Activation: use activate-shopify-windows.cmd, which requests secrets only in hidden local terminal prompts, performs read-only identity checks, and starts the bot only if they pass. See docs/SHOPIFY_TELEGRAM.md for Arabic/English instructions.

Related store task: the TinyFish retry completed at Shopify/Cloudflare verification without an authenticated admin session. Whish payment instructions remain prepared but unsaved. Existing published kit descriptions, sample images and videos remain as previously verified.
