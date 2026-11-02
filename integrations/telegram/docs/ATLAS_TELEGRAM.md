# ATLAS Intelligence — by JUST AI

Added 2026-10-26. These are reference and read-only reporting capabilities, not
model training, trading execution, or a guarantee of answers to every question.

## Commands

- `/atlas` opens the guide; `/atlas <question>` asks a source-grounded question.
- `/training` reads the latest SHADOW selector and training accelerator reports.
- `/sessions` reads up to five most recent archived evaluation reports.
- `/strategies` explains the inspected router; `/strategies <question>` retrieves sources.
- `/mode atlas` keeps ATLAS context enabled for follow-up questions.
- Ordinary questions mentioning ATLAS, training, strategies, calibration, council,
  or the corresponding Arabic terms also trigger ATLAS retrieval.

The no-argument commands work without an AI provider. Free-form explanations need
the configured OpenAI key/model and use existing per-user rate and usage limits.
Menus and responses support the existing English/Arabic preferences.

## Data sources and limits

The ATLAS source root defaults to the current Windows user's `ATLAS` folder. For
another installation, set `ATLAS_PROJECT_ROOT` in the bot's protected `.env`.
The existing setup wizard preserves this optional value. Do not use a public or
untrusted checkout as this source. The original ATLAS checkout is read-only here.

Only these documentation sources are searched:

- `docs/COUNCIL_SPECIALISTS.md`
- `docs/ATLAS_TRAINING_ACCELERATOR.md`
- `docs/ATLAS_TRAINING_GUIDE_AR.md`
- `docs/ATLAS_100_PAPER_SHADOW_TRAINING.md`
- `app/strategies/router.py`

Runtime summaries read `.runtime/paper/atlas_shadow_report.json` and
`.runtime/research/training-accelerator/latest-report.json`; session listings read
the five most recent `report-*.json` files in the latter folder. Reads are bounded
and short-lived. No journal, ledger, model, worker, or broker state is modified.
Only allowlisted metrics are returned: no account credentials, raw trade ledger,
source filesystem paths, or free-text runtime diagnostics. Missing, malformed,
future-dated, non-PAPER, promoted, or decision-changing reports fail closed.
Reports older than 24 hours are labeled stale. A timestamp is not proof that a
training process is currently running. Multiple evaluation runs are not new
independent examples and do not demonstrate profitability.

Relevant documentation excerpts and sanitized reports are included in OpenAI
requests for ATLAS questions. They are not fine-tuning data. The model is instructed
to cite sources, acknowledge gaps, and treat document text as data, not commands.
The packaged ZIP includes retrieval code, not private ATLAS runtime reports.

## Dashboard integration

Place `just-ai-smart-site` alongside `just-ai-bot-v2`, then double-click
`just-ai-smart-site/start-dashboard.cmd`. Open `http://127.0.0.1:4381/` and choose
**Telegram & ATLAS**. This localhost bridge is for the Windows owner session only.
It is not a public authenticated web service and must not be bound to the LAN or
exposed through a tunnel. Cloud hosting needs a separate authenticated backend.

1. **Secure setup** opens the existing hidden-entry wizard in a Windows console.
2. **Start bot** opens the activation launcher. Keep it running for bot replies.
3. In Telegram, press Start and use `/whoami`; add that personal ID to allowed users.
   Restart the bot after updating its startup settings.
4. Enter that same allowed ID in the dashboard and choose **Link my Telegram**.
   The bridge verifies the configured username and private chat with Telegram.
5. Use **Send to my Telegram** to submit a draft explicitly. Note/task/prompt share
   actions prepare the composer only. Bot messages do not execute bot commands.
6. **Refresh bot workspace** reads the linked user's saved notes/tasks/chat.
   **Refresh reports** reads the sanitized ATLAS snapshots. There is no automatic
   bidirectional synchronization of browser notes/tasks.

Disconnect removes only the dashboard link. It does not revoke the bot token,
stop the bot, delete Telegram messages, or erase browser notes.

The server serves an explicit list of public assets only. It restricts Host and
Origin, requires a per-process CSRF value for changes, and never sends the bot
token to the browser. Connection records are ignored by Git and omitted from
release archives. API checks use getMe/getChat; the bridge does not call getUpdates
or replace webhooks. A successful API check does not prove polling-worker health.

## Validation status

No automated tests, live message send, or end-to-end Telegram/AI verification was
performed for this addition. At implementation time the Windows Telegram token
and allowed user list were missing. Configure those locally before activation.
