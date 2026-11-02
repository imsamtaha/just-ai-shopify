"""Private Meta configuration; distinct from Telegram and AI credentials."""
from dataclasses import dataclass, field
import re
from urllib.parse import urlsplit

from dotenv import dotenv_values
from .config import ROOT, ConfigError


@dataclass(frozen=True)
class MetaSettings:
    app_secret: str = field(default="", repr=False)
    verify_token: str = field(default="", repr=False)
    whatsapp_token: str = field(default="", repr=False)
    page_token: str = field(default="", repr=False)
    phone_id: str = ""
    page_id: str = ""
    version: str = ""
    public_url: str = ""
    whatsapp_users: frozenset[str] = frozenset()
    messenger_users: frozenset[str] = frozenset()

    @property
    def webhook_ready(self):
        return bool(self.app_secret and len(self.verify_token) >= 24 and self.version)

    def enabled(self, channel):
        if channel == "whatsapp":
            return self.webhook_ready and bool(self.phone_id and self.whatsapp_token)
        if channel == "messenger":
            return self.webhook_ready and bool(self.page_id and self.page_token)
        return False


def load_meta(root=ROOT, values=None):
    data = dict(dotenv_values(root / ".env", interpolate=False)) if values is None else values
    def get(key):
        return str(data.get(key) or "").strip()
    def identifier(key):
        value = get(key)
        if value and not re.fullmatch(r"[0-9]{1,30}", value):
            raise ConfigError(key + " must contain digits only.")
        return value
    def users(key):
        items = frozenset(x.strip() for x in get(key).split(",") if x.strip())
        if any(not re.fullmatch(r"[0-9]{1,30}", x) for x in items):
            raise ConfigError(key + " must contain comma-separated numeric sender IDs.")
        return items
    version = get("META_GRAPH_VERSION")
    if version and not re.fullmatch(r"v[0-9]{1,3}\.0", version):
        raise ConfigError("META_GRAPH_VERSION must match the supported version in your Meta app, e.g. vXX.0.")
    url = get("META_PUBLIC_URL").rstrip("/")
    if url:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise ConfigError("META_PUBLIC_URL must be an HTTPS origin without a path, credentials or query.")
    verify = get("META_VERIFY_TOKEN")
    if verify and len(verify) < 24:
        raise ConfigError("META_VERIFY_TOKEN must contain at least 24 characters.")
    return MetaSettings(get("META_APP_SECRET"), verify, get("META_WHATSAPP_ACCESS_TOKEN"),
                        get("META_PAGE_ACCESS_TOKEN"), identifier("META_PHONE_NUMBER_ID"),
                        identifier("META_PAGE_ID"), version, url,
                        users("META_WHATSAPP_ALLOWED_IDS"), users("META_MESSENGER_ALLOWED_IDS"))
