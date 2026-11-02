# WhatsApp and Messenger — ATLAS Intelligence by JUST AI

This is a local implementation for one Meta developer app with both WhatsApp
Cloud API and Messenger. It is not a connected or published Meta app until
credentials, subscriptions, an HTTPS callback and real delivery are verified.
The existing Telegram bot and dashboard use separate processes and ports.

## Private setup on Windows

Run `setup-meta-windows.cmd` from this package. Secrets are hidden during entry;
the existing protected `.env` is updated atomically and other settings retained.
Meta access tokens and the App Secret are distinct from AI-provider keys.
Enter the Graph API version supported by your app; no version is silently guessed.

Required for both: Meta App Secret, generated verification token, Graph API
version. For WhatsApp: Cloud API access token and **phone-number ID**, not the
business phone number. For Messenger: Facebook Page ID and its Page access token.
The business number is only used to check the expected identity in `meta_doctor.py`.
It is not automatically authorized as a sender and is not migrated or deregistered.

Use `META_WHATSAPP_ALLOWED_IDS` for personal sender numbers with country code,
digits only. Messenger uses Page-scoped sender IDs, not Telegram IDs or ordinary
Facebook profile IDs. Once webhooks are connected, `/whoami` returns the sender's
channel ID. Add that ID in local setup and restart the service. Empty allowlists
permit only `/whoami` and `/privacy`; project reports stay private.

Run `start-meta-windows.cmd`, then inspect `http://127.0.0.1:4382/health` locally.
Run `.venv\Scripts\python.exe meta_doctor.py --live` for read-only token/identity
checks. No test message is sent by that command.

## Meta account and HTTPS activation

Open https://developers.facebook.com/apps/ and select or create the intended
business app. Configure the WhatsApp and Messenger products for the business
number and Page. Follow the app's current onboarding, permissions and review
requirements; a personal WhatsApp installation alone is not Cloud API setup.

Host this service behind an HTTPS reverse proxy at an owned origin, forwarding
**only `/meta/webhook`** to `127.0.0.1:4382`. Set body/request-rate/concurrency
limits at that proxy. Do not expose the localhost dashboard or private files.
The included Python HTTP server is a local bridge and needs that production
proxy, process supervision and a private persistent data directory for deployment.
No tunnel, DNS change, public deployment or Meta subscription is made by setup.

Use `https://YOUR-ORIGIN/meta/webhook` as the callback. Copy `META_VERIFY_TOKEN`
privately from the host configuration into Meta's verification form. Subscribe
WhatsApp to messages and the intended Messenger Page to messages, using the
current Meta console instructions. A successful challenge verifies only the
callback handshake, not signatures, access permissions, replies or AI availability.

Send `/whoami` from your own accounts, allow those IDs, restart, then send `/atlas`
on each channel. Confirm replies in both apps. Do not mark production activation
complete until this end-to-end check and required Meta approvals pass.

## Commands and behavior

`/start`, `/help`, `/atlas`, `/training`, `/sessions`, `/strategies`, `/whoami`,
`/privacy`. Arabic questions are supported when the configured AI is available.
The source-grounded ATLAS documentation and PAPER/SHADOW summaries are reused.
No trades, training jobs, promotions or store changes can be executed here.
Notes/tasks and Telegram conversation history are not copied between identities.

WhatsApp/Messenger provide the messaging transport, not the AI model. OpenRouter
credentials were removed at the owner's request. AI answers remain paused until
valid AI credentials and a model are configured separately. Static commands work
without a paid AI request once Meta is connected.

## Delivery and data handling

POST bodies require a valid HMAC SHA-256 signature using the Meta App Secret.
The service checks the configured destination Page/phone, ignores echoes/status
events and accepts only text received in the last five minutes. Replies are
immediate responses to inbound messages; no broadcasts, marketing templates or
automated follow-ups are implemented. Message IDs are deduplicated in SQLite.

The durable inbox permits up to 30 accepted incoming messages per sender/channel
in a rolling 24 hours, and 1,000 pending messages globally. A single worker bounds
AI concurrency. Messages delayed beyond five minutes are skipped. Failed or
interrupted sends are marked uncertain and never automatically resent; inspect
the recipient app before any manual recovery. An API acceptance is not proof of
delivery. Outbound replies are shortened to stay within text limits.

Raw queued text is cleared after handling. Sender/message IDs and state are kept
up to seven days and pruned during ingestion. No cross-channel AI history is
stored. Credentials and HTTP/provider bodies are not logged. AI prompts may
include selected local ATLAS documents/reports for allowlisted senders only.

Official implementation references:
- https://github.com/fbsamples/whatsapp-api-examples
- https://github.com/fbsamples/messenger-platform-samples/tree/main/quick-start
- https://developers.facebook.com/docs/graph-api/webhooks/getting-started
