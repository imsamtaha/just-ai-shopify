"""Presence-only local checks; --live reads identity/scopes without changing data."""
import argparse
import asyncio
import sys

from just_ai.config import ConfigError
from just_ai.runtime import safe_logging
from just_ai.shopify_config import load_shopify_settings
from just_ai.shopify_api import ShopifyClient, ShopifyError


async def remote(settings):
    client = ShopifyClient(settings)
    try:
        shop = await client.identity(force=True)
        print("Shop identity: verified against the pinned JUST AI shop ID")
        print("Shop currency: " + shop["currencyCode"])
        missing = {"write_orders", "write_products"} - client.scopes
        print("Required write scopes: " + ("PASS" if not missing else "missing " + ", ".join(sorted(missing))))
        print("Older orders: " + ("read_all_orders granted" if "read_all_orders" in client.scopes else "app is limited to Shopify's standard recent-order access"))
        print("No orders, products, payments or messages changed.")
        return not missing
    except ShopifyError as exc:
        print("Shopify preflight failed: " + exc.code + ". Secret values and response bodies are hidden.")
        return False
    finally:
        await client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    safe_logging()
    try:
        settings = load_shopify_settings()
    except ConfigError as exc:
        print(str(exc))
        return 1
    print("Shopify enabled: " + str(settings.enabled))
    print("Owner accounts configured: " + str(len(settings.owners)))
    print("Credentials configured: " + str(settings.ready))
    if not settings.ready:
        print("Run configure_shopify.py locally. No network request made.")
        return 1
    return 0 if not args.live or asyncio.run(remote(settings)) else 1


if __name__ == "__main__":
    sys.exit(main())
