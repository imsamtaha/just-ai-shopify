"""Presence checks; --live verifies Meta identities without sending messages."""
import argparse
import logging
import sys

import httpx
from dotenv import dotenv_values
from just_ai.config import ROOT
from just_ai.meta_config import load_meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    config = load_meta()
    ready = config.enabled("whatsapp") and config.enabled("messenger")
    for channel in ("whatsapp", "messenger"):
        print(channel + " credentials: " + ("configured" if config.enabled(channel) else "missing settings"))
    print("Public HTTPS origin: " + ("configured" if config.public_url else "missing"))
    print("WhatsApp authorized senders: " + str(len(config.whatsapp_users)))
    print("Messenger authorized senders: " + str(len(config.messenger_users)))
    print("Subscriptions and real message delivery: not verified")
    if not args.live:
        return 0 if ready else 1
    with httpx.Client(timeout=15) as client:
        for channel, identity, token, fields in (
            ("whatsapp", config.phone_id, config.whatsapp_token, "id,display_phone_number"),
            ("messenger", config.page_id, config.page_token, "id,name"),
        ):
            if not config.enabled(channel):
                continue
            try:
                # /me verifies that the Messenger token itself belongs to the intended Page.
                node = "me" if channel == "messenger" else identity
                response = client.get(f"https://graph.facebook.com/{config.version}/{node}",
                                      params={"fields": fields}, headers={"Authorization": "Bearer " + token})
                passed = response.status_code == 200 and response.json().get("id") == identity
                if passed and channel == "whatsapp":
                    expected = dotenv_values(ROOT / ".env", interpolate=False).get("META_BUSINESS_PHONE", "")
                    if expected:
                        digits = lambda text: "".join(c for c in text if c.isdigit())
                        passed = digits(response.json().get("display_phone_number", "")) == digits(expected)
                print(channel + " identity: " + ("PASS" if passed else "FAIL") + " (HTTP " + str(response.status_code) + ")")
                ready = ready and passed
            except Exception as exc:
                print(channel + " check failed (" + type(exc).__name__ + "); details hidden.")
                ready = False
    return 0 if ready else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print("Meta checks failed (" + type(exc).__name__ + "); details hidden.")
        sys.exit(1)
