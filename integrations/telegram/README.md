# JUST AI Telegram Bot — @JustAI_chatbot

A modular personal assistant for Windows and Python 3.11+. Includes text AI chat,
async SQLite storage, notes, tasks, prompt generation, saved settings, Arabic/English
menus, and six recent successful conversation pairs per Telegram chat and user.

## Windows quick start

### Activate an installed Windows copy

Double-click `activate-windows.cmd`. It opens secure setup if credentials are
missing, checks the Telegram identity and webhook, then starts the bot in the
foreground. Enter your bot's exact username from BotFather in setup. The saved
default `JustAI_chatbot` must be changed if you are activating another bot.
Keep the terminal open and the computer awake while using Telegram on your phone.

To change saved credentials, bot identity, or your allowed user ID:

```powershell
.\.venv\Scripts\python.exe activate.py --configure
```

With no allowed user ID, use `/whoami` in Telegram, stop with Ctrl+C, then rerun
configuration to add that ID. Secret values are entered locally and stay hidden.

From this project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe configure.py
.\.venv\Scripts\python.exe doctor.py --live
.\.venv\Scripts\python.exe bot.py
```

The current Windows checkout already has its virtual environment and dependencies
installed. Run the configuration wizard once to enter the existing BotFather token,
OpenAI API key, an available Responses-compatible model, and your numeric Telegram
user ID. Credentials are typed locally without echoing; do not paste them into chats.
No OAuth flow is required. You do not need to create another Telegram bot.

`configure.py` saves only this project's `.env` atomically and restricts its Windows
ACL to the current user and SYSTEM. On Linux/Termux it uses mode 0600. Blank input
keeps an existing value. `.env` is excluded from Git and the release archive.
The expected Telegram username defaults to `JustAI_chatbot`. The setup wizard lets you
change it to the username confirmed in BotFather; startup rejects a mismatch. Pressing
Enter keeps the saved identity. A QR image alone does not verify ownership or a token.

`setup-windows.ps1` installs and tests the package; `start-windows.ps1` launches it
from the correct directory. Direct Python commands above also work when PowerShell
script execution is restricted. The bot runs in the foreground; Ctrl+C stops it.

WSL/Ubuntu, Node.js, Git, and Neovim are not runtime requirements. On the inspected
Windows host WSL has no installed Linux distribution, so this package uses native
Windows Python. No WSL project was created and no Linux readiness is claimed.

## Commands

| Command | Behavior / example |
| --- | --- |
| `/start`, `/menu` | Open the workspace and navigation buttons |
| `/help` | All commands and examples |
| `/settings` | Show preferences and controls |
| `/settings mode coding` | Change mode; also supports `skin minimal`, `language ar` |
| `/skills`, `/mode` | Select general, business, coding, marketing, writing, planning, prompt |
| `/skin` | Select classic, minimal, or friendly response style |
| `/language` | Select `auto`, `en`, or `ar` |
| Ordinary text, `/ask` | AI conversation with recent memory |
| `/prompt` | Generate a reusable prompt for the supplied request |
| `/note Customer prefers Arabic` | Save a note |
| `/notes`, `/notes 2` | List notes, five per page |
| `/note_delete 3` | Delete your note by ID |
| `/task Prepare proposal` | Save a task |
| `/tasks`, `/tasks 2` | List tasks, five per page |
| `/done 4` | Complete your task by ID |
| `/task_delete 4` | Delete your task by ID |
| `/history` | Show the recent conversation in this chat |
| `/reset` | Clear this chat's AI memory; keep notes and tasks |
| `/status` | Settings, configured AI status, and UTC daily quota |
| `/privacy` | Data handling explanation |
| `/forget` | Request deletion; `/forget confirm` within 60 seconds performs it |
| `/whoami` | Show your Telegram user ID |

Command text may start on the next line or after a tab; notes, tasks, and prompts
preserve the remaining line breaks. Changing language with `/language` or the menu
immediately uses that language for the confirmation and refreshed navigation.

With an empty `ALLOWED_USER_IDS`, the bot permits only `/whoami` and `/privacy`.
If your user ID is unknown, launch in this setup mode, send `/whoami` to the bot,
then stop it and enter that ID through the wizard. AI calls remain disabled until
an allowed user, API key, and model are configured. Additional IDs can be comma separated.

## Architecture

```text
bot.py                   guarded entry point and sanitized startup errors
configure.py             hidden credential entry, atomic .env writes, file permissions
doctor.py                SQLite integrity, configuration and opt-in connectivity checks
just_ai/config.py        package-local .env parsing and validation
just_ai/runtime.py       lifecycle, identity/webhook checks, polling, single-process lock
just_ai/handlers.py      commands, text messages, callbacks, authorization, errors
just_ai/provider.py      async OpenAI Responses client with sanitized provider failures
just_ai/store.py         aiosqlite transactions, schema migration, persistence, quotas
just_ai/catalog.py       commands and assistant role instructions
just_ai/ui.py            bilingual keyboards/help and Telegram-safe reply splitting
tests/test_bot.py        functional and failure-path tests
tests/test_async_smoke.py concurrency, migration and offline application lifecycle smoke
```

The runtime initializes SQLite asynchronously during startup and closes both the
provider and database on shutdown or startup failure. Storage operations serialize
transactions; history is keyed by both `chat_id` and `user_id`. An older v2 SQLite
schema is upgraded in place by mapping its private-chat history to `chat_id=user_id`.
Notes, tasks, preferences, and quotas remain scoped to their owner. Back up `data/`
privately while the bot is stopped before applying updates to an existing deployment.

The AI service supports the OpenAI and OpenRouter Responses endpoints. Select
`AI_PROVIDER=openai` with `OPENAI_API_KEY` / `OPENAI_MODEL`, or
`AI_PROVIDER=openrouter` with `OPENROUTER_API_KEY` / `OPENROUTER_MODEL`
(for example `openai/gpt-4.1-mini`). The setup wizard uses the selected provider.
OpenRouter receives AI prompts and routes them to the model provider; their
respective data policies apply. Credentials remain on the Windows host.
The service handles authentication, quota, timeout, incomplete and malformed responses.
It does not retry paid requests automatically. Notes and tasks are never automatically
included in AI prompts. Assistant modes do not execute code or external actions.

## WhatsApp and Messenger

Run `setup-meta-windows.cmd` for private Meta credentials, and
`start-meta-windows.cmd` for the separate localhost webhook bridge on port 4382.
Both channels reuse ATLAS references and training commands. They require a Meta
developer app, Page/phone API credentials, allowed sender IDs and a public HTTPS
webhook before live replies work. See [Meta setup](docs/META_CHANNELS.md).

## Validation and safe smoke tests

```powershell
.\.venv\Scripts\python.exe -m compileall -q bot.py configure.py doctor.py just_ai tests tools
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe doctor.py --live
```

The tests use temporary databases, fabricated credentials and offline Telegram/AI
transports. The lifecycle smoke starts the actual application, dispatches commands
and text, checks memory and replies, and shuts down; it never reaches Telegram.
`doctor.py --live` makes only `getMe`/`getWebhookInfo` calls, sends no messages,
does not consume updates, and does not change the webhook or commands. Missing
credentials stop the check before any Telegram request. `doctor.py` without flags
checks the local database and configuration only.

`doctor.py --check-ai` additionally makes one small potentially billable AI request.
This is optional and must use a model enabled for your API account. No real AI request
was made during this release validation. See `VALIDATION.md` for observed results.

## Operation and limitations

- Private chats and explicitly allowed users only.
- Default per-user limit: 30 AI attempts/day UTC, with a 3-second cooldown.
- Input capped at 2,000 characters; history retains six successful pairs.
- 100 notes and 100 tasks per user; AI output capped in tokens and characters.
- Errors and logs omit credentials, HTTP URLs, and conversation content.
- Conversation is saved only after a successful AI response and Telegram delivery.
- SQLite is local and unencrypted. Protect the host and private backups.
- `/forget` retains today's quota counter so deletion cannot bypass the spending cap.
- Requests set `store=false`; this does not guarantee zero provider retention.
- One local process lock prevents duplicate workers in this package. A Telegram
  polling conflict stops the worker; another device's poller cannot be discovered by
  `getMe`. Stop the specific old deployment before starting this one.
- Existing webhooks are not removed: startup refuses to switch them to polling.
- Startup registers bilingual command menus, but does not send welcome messages.
- Queued updates are retained; messages older than five minutes are ignored.
- Updates run sequentially; a slow AI request can delay commands for up to 60 seconds.
- No automatic boot service, voice/images, due-date reminders, website sync, or
  24/7 uptime guarantee is included. This is a personal single-worker deployment.

## Optional Linux / Termux use

Use a separate Linux virtual environment, never the Windows `.venv`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python configure.py
.venv/bin/python doctor.py --live
.venv/bin/python bot.py
```

Existing Termux `setup-termux.sh` and `start-termux.sh` remain available. Linux/Android
execution was not verified on this Windows host. The unrelated phone backup is not
modified or migrated into this project.

## References

- [python-telegram-bot application lifecycle](https://docs.python-telegram-bot.org/en/stable/telegram.ext.application.html)
- [aiosqlite async connections and transactions](https://aiosqlite.omnilib.dev/en/stable/)
- [Telegram Bot API](https://core.telegram.org/bots/api)


## Shopify control panel (optional)

Manage the JUST AI store from your authorized private Telegram chat with `/shop`. Orders, products, confirmed Whish payment records, kit previews and an audit log are supported. Advanced settings open Shopify Admin. Local implementation is complete; live use requires the bot token, numeric owner ID and Shopify app credentials. Open `activate-shopify-windows.cmd` for hidden credential entry and read-only preflight checks. See [the English/Arabic command guide](docs/SHOPIFY_TELEGRAM.md) for scope, examples and activation.
