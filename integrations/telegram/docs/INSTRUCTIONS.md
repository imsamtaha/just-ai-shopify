# Bot operator instructions

## What has and has not been verified

This package was built on Windows. The phone's existing bot is a different project;
we have its directory listing and a successful syntax-check screenshot, not its source.
No deployment, model access, bot ownership, or real Telegram/AI response is inferred.
Use the separate folder and verify the bot identity before switching pollers.

## Credential rules

Use `configure.py` to enter credentials locally. Never send credentials in Telegram,
in this task, in source files, in command-line arguments, or in an archive. The `.env`
is excluded by `.gitignore`, but Git ignore rules are not encryption or a secret vault.
No secrets are automatically imported from the old project. If modifying configuration
manually, stop the worker, edit `.env` locally, run `doctor.py`, then restart.

## Assistant instruction hierarchy

`just_ai/catalog.py` contains BASE instructions, seven curated skill prompts, and style
instructions. They are composed on each AI request with the user's language preference.
These are assistant roles, not executable plugins or external tools.

To add a new skill, add a lowercase key and `(English label, Arabic label, instructions)`
to SKILLS. The skill menu populates automatically. Keep callbacks under Telegram's
64-byte limit. Run the included checks and test the new skill in Telegram.

Recommended skill behavior:

- Business: distinguish assumptions, customer evidence, and action items.
- Coding: supply understandable code and identify dependencies; never claim it ran.
- Marketing: use known product facts and avoid invented claims/testimonials.
- Writing: preserve meaning and match audience, language, and tone.
- Planning: prioritize realistically; distinguish advice from saved tasks.
- Prompt: state objective, inputs, constraints, output, and quality criteria.
- General: answer directly, state uncertainty, and ask only necessary questions.

The AI client has no execution tools. User content, documents, or quoted instructions
cannot create shell access. Saved notes/tasks are managed only by explicit bot commands.
Connecting an executor, trading system, or browser would require a separate reviewed design.

## Rollback and maintenance

The old `~/just-ai-telegram-bot` folder is not modified by this package. To roll back,
stop v2 in its own session with Ctrl+C, then start the known old bot using its own
environment. Do not start both. Their data is separate. This release upgrades only its own older v2 message schema to add chat scope; it does not import the phone database.

For a local backup, stop v2 and privately back up its `data/` directory. It contains
personal conversation and notes. Do not attach it to this task or publish it. Avoid
placing credentials in code backup archives. Confirm the bot is stopped before any
restore; do not overwrite a live SQLite file.

For updates, use a new release folder, verify it offline, and explicitly plan data
migration. Do not blindly overwrite the existing `.env`, venv, or data directory.

## Release checks

Run `python -m unittest discover -s tests -v` using this package's environment.
The tests use temporary databases, fabricated credentials, and mock HTTP transport;
they do not call Telegram or OpenAI. Check that the release archive contains only
source, templates, instructions, tests, and its public validation report.

Then on the target Windows or Termux host, check identity with `doctor.py --live`, stop the old poller, start v2,
and try `/start`, `/note`, `/notes`, `/task`, `/tasks`, `/done`, `/skills`, `/skin`,
`/language ar`, a real AI question, `/reset`, and `/status` with the authorized user.
Only a real response proves live operation. No API/model functionality is guaranteed
by a compile check, menu registration, or the log line that polling is starting.
