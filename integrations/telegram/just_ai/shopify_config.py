"""Optional, host-only Shopify configuration. Never expose secret values."""
from dataclasses import dataclass, field
import os
import re

from dotenv import dotenv_values
from .config import ROOT, ConfigError

SHOP_DOMAIN = "just-ai-store.myshopify.com"
SHOP_ID = "gid://shopify/Shop/103597179156"


@dataclass(frozen=True)
class ShopifySettings:
    enabled: bool = False
    domain: str = SHOP_DOMAIN
    shop_id: str = SHOP_ID
    api_version: str = "2026-10"
    owners: frozenset[int] = frozenset()
    token: str = field(default="", repr=False)
    client_id: str = field(default="", repr=False)
    client_secret: str = field(default="", repr=False)

    @property
    def ready(self):
        return self.enabled and bool(self.owners) and bool(self.token or (self.client_id and self.client_secret))


def load_shopify_settings(root=ROOT, environ=None):
    values = dict(dotenv_values(root / ".env", interpolate=False))
    values.update(os.environ if environ is None else environ)
    get = lambda key, default="": str(values.get(key) or default).strip()
    enabled = get("SHOPIFY_ENABLED", "false").lower()
    if enabled not in ("true", "false"):
        raise ConfigError("SHOPIFY_ENABLED must be true or false.")
    # An unused integration must never break the existing AI/ATLAS bot.
    if enabled == "false":
        return ShopifySettings()
    domain = get("SHOPIFY_SHOP_DOMAIN", SHOP_DOMAIN).lower()
    if domain != SHOP_DOMAIN:
        raise ConfigError("SHOPIFY_SHOP_DOMAIN must match the configured JUST AI store.")
    if get("SHOPIFY_EXPECTED_SHOP_ID", SHOP_ID) != SHOP_ID:
        raise ConfigError("SHOPIFY_EXPECTED_SHOP_ID does not match the configured store.")
    version = get("SHOPIFY_API_VERSION", "2026-10")
    if not re.fullmatch(r"20\d{2}-(01|04|07|10)", version):
        raise ConfigError("SHOPIFY_API_VERSION must be a stable quarterly version.")
    try:
        owners = frozenset(int(x.strip()) for x in get("SHOPIFY_OWNER_IDS").split(",") if x.strip())
        allowed = frozenset(int(x.strip()) for x in get("ALLOWED_USER_IDS").split(",") if x.strip())
        if not owners or any(x <= 0 for x in owners) or not owners <= allowed:
            raise ValueError
    except ValueError:
        raise ConfigError("SHOPIFY_OWNER_IDS must be positive numeric IDs also present in ALLOWED_USER_IDS.") from None
    token, client_id, secret = (get(x) for x in ("SHOPIFY_ADMIN_ACCESS_TOKEN", "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET"))
    if not token and not (client_id and secret):
        raise ConfigError("Configure Shopify credentials locally with configure_shopify.py.")
    if token and (client_id or secret):
        raise ConfigError("Configure one Shopify authentication method only.")
    if any(any(c.isspace() for c in v) for v in (token, client_id, secret)):
        raise ConfigError("Shopify credentials cannot contain whitespace.")
    return ShopifySettings(True, domain, SHOP_ID, version, owners, token, client_id, secret)
