"""Secure local setup for the optional Shopify control panel."""
import getpass
import json
import os
import subprocess
import sys
import tempfile

from dotenv import dotenv_values
from configure import protect_file
from just_ai.config import ROOT, ConfigError
from just_ai.shopify_config import SHOP_DOMAIN, SHOP_ID, load_shopify_settings


def main():
    if not sys.stdin.isatty():
        print("Run configure_shopify.py in an interactive terminal on the bot host.")
        return 1
    os.umask(0o077)
    target = ROOT / ".env"
    values = dict(dotenv_values(target, interpolate=False)) if target.exists() else {}
    print("JUST AI Shopify setup. Secrets are hidden and saved only on this device.")
    print("Store: " + SHOP_DOMAIN)
    print("Create/install your own Shopify app with read_orders, write_orders, read_products, write_products.")
    print("Use client credentials only for an app and store belonging to your own Shopify organization.")
    print("Do not paste credentials into Telegram or ChatGPT.")
    try:
        owners = input("Your numeric Telegram owner ID(s), comma separated [Enter keeps existing]: ").strip()
        if owners:
            values["SHOPIFY_OWNER_IDS"] = owners
        # These explicitly entered IDs authorize both the base bot and store controls.
        base = {x.strip() for x in str(values.get("ALLOWED_USER_IDS") or "").split(",") if x.strip()}
        base.update(x.strip() for x in str(values.get("SHOPIFY_OWNER_IDS") or "").split(",") if x.strip())
        values["ALLOWED_USER_IDS"] = ",".join(sorted(base))
        mode = input("Authentication: 1 = client ID/secret, 2 = existing Admin access token [1]: ").strip() or "1"
        if mode not in ("1", "2"):
            raise ConfigError("Choose authentication method 1 or 2.")
        names = ("SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET") if mode == "1" else ("SHOPIFY_ADMIN_ACCESS_TOKEN",)
        for name in names:
            value = getpass.getpass(name + (" [Enter keeps saved value]" if values.get(name) else "") + ": ").strip()
            if value:
                values[name] = value
        for name in ("SHOPIFY_ADMIN_ACCESS_TOKEN", "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET"):
            if name not in names:
                values[name] = ""
        values.update(SHOPIFY_ENABLED="true", SHOPIFY_SHOP_DOMAIN=SHOP_DOMAIN,
                      SHOPIFY_EXPECTED_SHOP_ID=SHOP_ID, SHOPIFY_API_VERSION="2026-10")
        load_shopify_settings(ROOT, environ=values)
        lines = [f"{key}={json.dumps(str(value), ensure_ascii=False)}" for key, value in values.items()
                 if value is not None and key.replace("_", "").isalnum()]
        descriptor, temporary = tempfile.mkstemp(prefix=".env-", dir=ROOT)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                protect_file(temporary)
                handle.write("\n".join(lines) + "\n")
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        print("Shopify configuration saved securely. Next: python shopify_doctor.py --live")
        print("Restart this bot after checks pass. No store changes were made by setup.")
        return 0
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled. Configuration was not changed.")
    except ConfigError as exc:
        print(str(exc))
    except (OSError, subprocess.SubprocessError, IndexError, StopIteration):
        print("Secure configuration could not be saved; details suppressed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
