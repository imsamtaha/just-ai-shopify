# JUST AI Shopify

Private source repository for the JUST AI Shopify admin app, Telegram integration, digital-product packages, media, and operations documentation.

## App features

- Embedded Shopify admin interface built from Shopify's official React Router template.
- Live catalog overview: total, active, draft, archived products, and collections.
- Product title search, status filters, cursor pagination, currency-aware first-variant prices, and links to Shopify Admin.
- Shopify authentication, Prisma session storage, authenticated uninstall/scope webhooks.
- Operations guide for secure digital delivery and manual Whish payments.

The app requests only `read_products`. Product editing, order management, payment confirmation, and file attachment take place in Shopify Admin. This repository does not change the live store merely by being cloned or run.

## Start on Windows PowerShell

Requires Node.js 24 LTS, npm, a Shopify developer account, a registered app, and a development store.

```powershell
git clone https://github.com/imsamtaha/just-ai-shopify.git
Set-Location just-ai-shopify
npm.cmd ci
Copy-Item .env.example .env
npm.cmd run setup
npm.cmd run config:link
npm.cmd run dev
```

Keep credentials in the ignored `.env` file or your hosting provider's secret manager. Shopify CLI supplies credentials during development. Linking and installation require your Shopify browser login; the connected chat integration does not supply this app's credentials.

The committed `client_id` is intentionally blank and application URLs are placeholders until linking. Use a development store for first installation. See [setup](docs/SETUP.md) and [deployment](docs/DEPLOYMENT.md).

## Repository map

| Directory | Contents |
| --- | --- |
| `app/` | Embedded admin UI, authenticated server loaders, catalog queries |
| `prisma/` | Session schema and migration |
| `tests/` | Catalog logic, failure handling, authentication boundary tests |
| `integrations/telegram/` | Existing JUST AI bot source, setup tools, tests and guides |
| `products/packages/2026-11-02/` | BASIC, PRO and Sprint bilingual v3 ZIPs and expanded source |
| `products/packages/2026-11-01/` | v2 toolkit ZIPs and v2_1 service onboarding ZIPs |
| `products/media-and-listings/` | Product images, tutorial videos and bilingual listings |
| `catalog/history/` | Dated product and price snapshots |
| `archive/` | Original packages and historical build scripts |
| `docs/` | Setup, architecture, operations, Shopify reference links and import manifest |

[Product version map](products/README.md) · [Shopify guide](docs/SHOPIFY_GUIDE.md) · [Imported file inventory](docs/import-manifest.json) · [Validation](docs/VALIDATION.md)

## Checks

```powershell
npm.cmd run check
npm.cmd run graphql-codegen
```

The bot has a separate Python environment and test suite; see its README. Do not start a second poller for an already running bot.

## Status and provenance

Repository assembled on 2 November 2026. Historical readiness reports and price snapshots retain their original dates and are not proof of current checkout, payment, download delivery, or bot availability. Store identity was checked through the Shopify connector during preparation. The new app is not registered, installed, hosted, or published by this repository creation.

Upstream: [Shopify React Router template](https://github.com/Shopify/shopify-app-template-react-router), commit `81eb98b6ca095eb0b92657f6007939a418f61955`. See [rights and licensing](RIGHTS.md).
