from dataclasses import dataclass, field
from pathlib import Path
import os
import re

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent


class ConfigError(Exception):
    """Messages contain setting names only, never values."""


@dataclass(frozen=True)
class Settings:
    token: str = field(repr=False)
    api_key: str = field(repr=False)
    model: str = ""
    allowed: frozenset[int] = frozenset()
    expected_username: str = "justai_chatbot"
    daily_limit: int = 30
    cooldown: int = 3
    max_output: int = 1600
    provider: str = "openai"

    @property
    def ai_ready(self):
        return bool(self.api_key and self.model)


def load_settings(root=ROOT, environ=None, require_telegram=True):
    # Read only this project's file: no parent search and no shell execution.
    values = dict(dotenv_values(root / ".env", interpolate=False))
    values.update(os.environ if environ is None else environ)

    def get(name, default=""):
        return str(values.get(name) or default).strip()

    def number(name, default, minimum, maximum):
        try:
            result = int(get(name, str(default)))
        except ValueError:
            raise ConfigError(f"{name} must be a whole number.") from None
        if not minimum <= result <= maximum:
            raise ConfigError(f"{name} must be between {minimum} and {maximum}.")
        return result

    token = get("TELEGRAM_BOT_TOKEN")
    if require_telegram and not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]{20,}", token):
        raise ConfigError("Set a valid TELEGRAM_BOT_TOKEN with python configure.py.")
    try:
        allowed = frozenset(int(x.strip()) for x in get("ALLOWED_USER_IDS").split(",") if x.strip())
        if any(x <= 0 for x in allowed):
            raise ValueError
    except ValueError:
        raise ConfigError("ALLOWED_USER_IDS must contain positive numeric IDs.") from None
    provider = get("AI_PROVIDER", "openai").lower()
    if provider not in {"openai", "openrouter"}:
        raise ConfigError("AI_PROVIDER must be openai or openrouter.")
    prefix = "OPENROUTER" if provider == "openrouter" else "OPENAI"
    return Settings(
        token, get(prefix + "_API_KEY"), get(prefix + "_MODEL"), allowed,
        get("EXPECTED_BOT_USERNAME", get("BOT_USERNAME", "JustAI_chatbot")).lstrip("@").lower(),
        number("DAILY_AI_LIMIT", 30, 1, 500),
        number("COOLDOWN_SECONDS", 3, 1, 60),
        number("MAX_OUTPUT_TOKENS", 1600, 128, 8000),
        provider,
    )
