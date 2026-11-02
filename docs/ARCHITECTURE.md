# Architecture

Browser in Shopify Admin → App Bridge and Polaris web components → React Router loaders → `authenticate.admin(request)` → Shopify Admin GraphQL API.

- `app/shopify.server.ts` retains Shopify's official authentication and response-header helpers.
- `app/services/catalog.server.ts` contains read-only queries and handles HTTP failures, GraphQL errors and missing data. Auth responses are rethrown so redirects/challenges still work.
- `app/lib/catalog.ts` builds literal title searches, validates product links, formats counts and prices, and preserves filters during pagination.
- Each protected route authenticates independently before reading data.
- Counts retain Shopify's precision; lower-bound results display a plus sign.
- Product prices represent the first variant, explicitly labelled in the interface.
- Prisma stores sessions in SQLite. On uninstall the authenticated webhook removes sessions for that shop.
- Existing Telegram source is preserved as a separate integration; it is not started by the web app.

API version is pinned to `2026-10` in server configuration, code generation and webhook configuration. Update these together after schema validation.
