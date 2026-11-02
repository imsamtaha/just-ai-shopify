# Validation record

Date: 2 November 2026 (Asia/Beirut).

## Passed locally

- `npm run setup`: Prisma client generation and SQLite migration completed.
- `npm run check`: ESLint, TypeScript, 16 Vitest tests, client build and server build all passed.
- Existing Telegram integration: 79 tests passed on Python 3.13.15.
- Both app GraphQL operations validated against Shopify's 2026-10 schema; required scope is `read_products`.
- `npm run graphql-codegen` completed and generated the versioned schema and operation types.
- `npm audit --omit=dev`: zero reported vulnerabilities after the documented dependency fixes.
- All 184 imported files match the checksums in `import-manifest.json` (51,627,442 bytes).
- Archive CRC checks passed for 61 ZIP/Office archives containing 925 entries.
- Credential-pattern scan found no matches in the initial 253 files. The scan checks common Shopify, OpenAI, GitHub and Telegram token patterns and private keys, including inside supported archives. It is not a guarantee that every possible sensitive value is recognized.

## Local runtime smoke check

The built server was launched temporarily on loopback with synthetic app credentials. The home page returned 200 and rendered JUST AI Shopify. Unauthenticated admin routes returned Shopify's App Bridge authentication response, without the protected app UI or catalog. An unsigned uninstall webhook was rejected with HTTP 400. The test server was stopped.

An authentication response can use HTTP 200; this does not prove installation or live catalog access.

## Remaining live checks

- Register/link the app and fill the blank `client_id` through Shopify login. Shopify CLI 5.0.0 is installed in the project; `app config validate --json` currently requires that link and cannot complete non-interactively with a blank client ID.
- Install in a development store and verify embedded browser navigation, real product data and signed webhooks.
- Choose a host and persistent database; validate actual production deployment separately.
- Docker image execution was not tested.
- Historical payment, delivery and bot reports were imported, not revalidated against current live operations.

Shopify's standalone TSX validator had a broken dependency/type environment (missing TypeScript and JSX/Preact declarations). The app's own installed Polaris types, TypeScript compiler and production build passed. GraphQL validation succeeded through the toolkit's local validator.

No order, payment, customer message, Shopify installation or store mutation was performed as part of creating this repository.
