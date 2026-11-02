"""Interactive local setup; secret values are never printed or put in shell history."""
import getpass
import csv
import json
import os
import sys
import tempfile
import subprocess

from dotenv import dotenv_values
from just_ai.config import ROOT, ConfigError, load_settings


def protect_file(path):
    """Restrict credential access on both Windows and POSIX hosts."""
    if os.name == "nt":
        identity = subprocess.run(["whoami", "/user", "/fo", "csv", "/nh"],
                                  capture_output=True, text=True, check=True)
        sid = next(csv.reader(identity.stdout.strip().splitlines()))[1]
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r",
                        f"*{sid}:(F)", "*S-1-5-18:(F)"],
                       capture_output=True, check=True)
    else:
        os.chmod(path, 0o600)


def main():
    if not sys.stdin.isatty():
        print("Run this wizard in an interactive terminal on the bot host.")
        return 1
    os.umask(0o077)
    target = ROOT / ".env"
    values = dict(dotenv_values(target, interpolate=False)) if target.exists() else {}
    values.setdefault("BOT_USERNAME", "@JustAI_chatbot")
    values.setdefault("EXPECTED_BOT_USERNAME", "JustAI_chatbot")
    print("JUST AI setup. Enter keeps an existing value. Credentials stay on this device.")
    print("Use the token and exact username for your existing bot from BotFather.")
    print("The bot token belongs to the bot; the allowed user ID is your personal Telegram ID.")
    try:
        saved_provider = values.get("AI_PROVIDER") or "openai"
        provider = (input(f"AI provider: openai or openrouter [{saved_provider}]: ").strip() or saved_provider).lower()
        if provider not in {"openai", "openrouter"}:
            raise ConfigError("AI provider must be openai or openrouter.")
        values["AI_PROVIDER"] = provider
        prefix = "OPENROUTER" if provider == "openrouter" else "OPENAI"
        model_hint = "openai/gpt-4.1-mini" if provider == "openrouter" else "gpt-4.1-mini"
        for name, label, hidden in (
            ("TELEGRAM_BOT_TOKEN", "Telegram bot token", True),
            (prefix + "_API_KEY", provider + " API key (optional for notes/tasks)", True),
            (prefix + "_MODEL", "Model ID available to your account, e.g. " + model_hint, False),
            ("ALLOWED_USER_IDS", "Your numeric Telegram user ID (blank = setup mode)", False),
            ("EXPECTED_BOT_USERNAME", "Expected bot username without @ (Enter keeps the saved identity)", False),
        ):
            prompt = label + (" [already set]" if values.get(name) else "") + ": "
            if name == "EXPECTED_BOT_USERNAME":
                print("Saved expected username: " + str(values.get(name, "unset")))
            value = (getpass.getpass(prompt) if hidden else input(prompt)).strip()
            if value:
                values[name] = value
        values.setdefault("DAILY_AI_LIMIT", "30")
        values.setdefault("COOLDOWN_SECONDS", "3")
        values.setdefault("MAX_OUTPUT_TOKENS", "1600")
        # Validate without loading credentials from the inherited shell environment.
        load_settings(ROOT, environ=values)
        allowed_keys = {
            "TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY", "OPENAI_MODEL", "ALLOWED_USER_IDS",
            "BOT_USERNAME", "EXPECTED_BOT_USERNAME", "DAILY_AI_LIMIT", "COOLDOWN_SECONDS", "MAX_OUTPUT_TOKENS",
        }
        # Retain unknown settings when updating an existing local file.
        lines = []
        for key, value in values.items():
            if key not in allowed_keys and not key.replace("_", "").isalnum():
                continue
            if value is not None:
                lines.append(f"{key}={json.dumps(str(value), ensure_ascii=False)}")
        fd, temp = tempfile.mkstemp(prefix=".env-", dir=ROOT)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                protect_file(temp)
                handle.write("\n".join(lines) + "\n")
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        print("Saved local .env. Next: python doctor.py --live")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nSetup cancelled; settings were not saved.")
    except ConfigError as exc:
        print(str(exc))
    except (OSError, subprocess.SubprocessError, IndexError, StopIteration):
        print("Could not securely save configuration. Check local file permissions; details suppressed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
