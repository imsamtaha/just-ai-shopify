"""Interactive, secret-safe setup for Meta WhatsApp and Messenger."""
import getpass
import json
import os
import secrets
import sys
import tempfile

from dotenv import dotenv_values
from configure import protect_file
from just_ai.config import ROOT, ConfigError
from just_ai.meta_config import load_meta


def main():
    if not sys.stdin.isatty():
        print("Open this wizard in a local interactive terminal.")
        return 1
    target = ROOT / ".env"
    values = dict(dotenv_values(target, interpolate=False))
    print("JUST AI - WhatsApp and Messenger setup")
    print("Use one Meta developer app with both products. Enter keeps a saved value.")
    print("Meta tokens differ from Telegram, OpenAI and OpenRouter keys.")
    print("Missing values may be saved for later; a channel stays disabled until configured.")
    try:
        fields = (
            ("META_APP_ID", "Meta App ID", False),
            ("META_GRAPH_VERSION", "Supported Graph API version shown in your Meta app (vNN.0)", False),
            ("META_PUBLIC_URL", "Public HTTPS origin for this bridge (not the local dashboard)", False),
            ("META_APP_SECRET", "Meta App Secret", True),
            ("META_PHONE_NUMBER_ID", "WhatsApp phone-number ID from Meta API Setup (not your phone number)", False),
            ("META_WHATSAPP_ACCESS_TOKEN", "WhatsApp Cloud API access token", True),
            ("META_PAGE_ID", "Facebook Page numeric ID", False),
            ("META_PAGE_ACCESS_TOKEN", "Messenger Page access token", True),
            ("META_WHATSAPP_ALLOWED_IDS", "Allowed WhatsApp sender IDs, country code + digits, no plus sign", False),
            ("META_MESSENGER_ALLOWED_IDS", "Allowed Messenger page-scoped sender IDs (use /whoami after connecting)", False),
        )
        for key, label, hidden in fields:
            prompt = label + (" [saved]" if values.get(key) else "") + ": "
            value = (getpass.getpass(prompt) if hidden else input(prompt)).strip()
            if value:
                values[key] = value
        values.setdefault("META_VERIFY_TOKEN", secrets.token_urlsafe(32))
        config = load_meta(values=values)
        fd, name = tempfile.mkstemp(prefix=".env-", dir=ROOT)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                protect_file(name)
                for key, value in values.items():
                    if value is not None and key.replace("_", "").isalnum():
                        handle.write(key + "=" + json.dumps(str(value), ensure_ascii=False) + "\n")
            os.replace(name, target)
        finally:
            if os.path.exists(name):
                os.unlink(name)
        print("Saved protected settings. Restart start-meta-windows.cmd after changing settings.")
        print("WhatsApp configured: " + str(config.enabled("whatsapp")))
        print("Messenger configured: " + str(config.enabled("messenger")))
        if config.public_url:
            print("Meta webhook callback: " + config.public_url + "/meta/webhook")
        print("Copy META_VERIFY_TOKEN privately from the local .env into Meta's webhook form.")
        print("Do not paste credentials into chat. Run meta_doctor.py --live to check identities.")
        input("Press Enter to close setup.")
        return 0
    except (KeyboardInterrupt, EOFError):
        print("Setup closed. Only a completed save changes configuration.")
    except ConfigError as exc:
        print(str(exc))
    except Exception as exc:
        print("Setup could not complete (" + type(exc).__name__ + "); details hidden.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
