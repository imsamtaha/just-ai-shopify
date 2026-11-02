# Validation — 2026-10-26

## Telegram integration continuation

- Existing implementation inspected in place; this folder is not a Git repository.
- Baseline: **39 passed in 26.34 seconds** with the existing Windows environment.
- Reproduced three failing regression cases for multiline command content and
  immediate language changes through commands and inline menu buttons.
- Fixed whitespace parsing so `/note`, `/task`, and `/prompt` preserve their complete
  multiline content, including when the command contains the bot username.
- Language changes now refresh the confirmation and navigation in the selected
  language immediately, including switching back to automatic language selection.
- Removed an unrelated bot label from the secure setup instructions.
- Final full offline suite: **42 passed in 26.48 seconds**, including the actual
  application lifecycle with offline Telegram and AI transports.
- Compilation and dependency compatibility checks passed. SQLite startup and
  integrity checks passed.
- The package-local Telegram token, OpenAI key, OpenAI model, and allowed user IDs
  were empty; no values for these were inherited from the process environment.
- `doctor.py --live` stopped at the missing Telegram token before any Telegram
  request. No live identity, model access, or real message delivery is verified.
- No matching local bot process was found during the inspection. This does not
  establish whether another device is polling the same bot.
- No credentials were copied from the referenced conversation or changed locally.
- GitHub and Sites connector calls were unavailable in this chat. No remote source
  update, site change, or deployment was performed.

Remaining activation step: run `configure.py` locally with hidden credential input,
then repeat the live identity/webhook check and start the intended bot. Telegram
features need its token and an allowed user ID; AI chat additionally needs an OpenAI
key and an enabled Responses-compatible model. Actual message delivery still needs
verification after the user sends a message to the running bot.

## Previous validation — 2026-10-09

## Finalization update

- Repaired the local Windows virtual environment: its previous base Python executable
  had been removed. It now uses the installed managed Python 3.13.15 runtime.
- Full offline pytest suite passed again; dependency compatibility check passed.
- Setup wizard now accepts the expected Telegram username explicitly. Its regression
  test verifies that the chosen identity is saved without exposing credentials.
- The live doctor stopped at the missing Telegram token before contacting Telegram.
  Telegram token, OpenAI key, model, and allowed-user settings are still empty locally.
- Rebuilt the public release ZIP from the validated source and regenerated checksums.
- No real Telegram message, AI request, polling worker, or Termux deployment was performed.

The code package is ready for local credential setup. The remaining live blocker is
configuration on the intended host, followed by identity, connectivity, and message
delivery checks. Windows validation does not establish the phone's current state.

## Previous validation — 2026-10-05

## Host and scope

- Windows, native Python 3.13.15 in the package's own `.venv`.
- Git 2.55.0.windows.5, Node 24.19.0, npm 12.0.2 detected.
- Neovim was not found on PATH; it is not required by the bot.
- WSL is installed with default version 2, but has no installed distributions.
  Ubuntu and a Linux runtime were not installed or tested. The existing native
  Windows project was completed instead of creating a second WSL project.
- This project is not currently a Git repository. `.gitignore` is provided.
- Synced `sources/` reference files and the unrelated old backup were left unchanged.

## Passed

- `python -m pytest -q`: **39 passed in 41.15 seconds**.
- Syntax: **14 Python files parsed**, plus compileall passed.
- Application imports: entry point, configuration, diagnostics, and all package modules passed.
- `python -m pip check`: no broken requirements.
- Actual `data/workspace.sqlite3` async initialization and `PRAGMA quick_check`: PASS.
- Both Windows launcher scripts passed PowerShell parsing.
- `.env` Windows ACL: inheritance disabled, two entries (current user and SYSTEM).
- Secure setup wizard test: hidden input, persisted settings, no credential echo,
  atomic replacement, no leftover temporary credential file.
- Starting `bot.py` without credentials: safely stops with exit 1 and a setting-name-only error.

## Offline smoke and regression coverage

The actual python-telegram-bot Application was initialized, started, given synthetic
updates, stopped and shut down using an in-memory Telegram transport. Coverage includes
`/start`, `/help`, notes/tasks creation and listing, completion, `/settings`, `/prompt`,
text chat, and conversation history. No chat message is sent at startup. No real
Telegram/AI calls are made by tests. Test credentials and AI responses are fabricated.

Additional coverage: all command/menu routes, private chat/allowlist enforcement,
stale-message rejection, identity mismatch, webhook refusal, polling conflict stop,
local instance locking, quotas/cooldowns, provider failure sanitization, reply splitting,
user isolation, chat isolation, persistence across reopening, old-schema migration,
transaction rollback, concurrent quota reservations and idempotent database lifecycle.

## Live verification status

`doctor.py --live` was run. Local SQLite checks passed, then the check stopped with
exit 1 because TELEGRAM_BOT_TOKEN is missing. No Telegram request, update consumption,
webhook change, unsolicited message or paid AI request occurred.

No usable Telegram token or OpenAI key was found in the current package, inspected
related backup/configuration locations, or process environment. A local `.env` was
created with empty credential fields and the requested `JustAI_chatbot` identity.
No worker was left running. Live Telegram identity, AI account/model access and real
message delivery remain unverified.

The remaining user action is local configuration through `configure.py`: existing
BotFather token, OpenAI key, an enabled Responses model, and numeric allowed user ID.
After configuration, run the read-only live doctor check and launch `bot.py` using
this package's Python. If the numeric ID is unknown, the documented `/whoami` setup
mode can retrieve it without enabling AI access.

## Release archive

`tools/package_release.py` creates a public-file allowlist ZIP and SHA256 manifest.
Private `.env`, local database, caches and virtual environment are excluded. Linux
and Termux execution, external polling ownership, and 24/7 hosting are not validated.


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
