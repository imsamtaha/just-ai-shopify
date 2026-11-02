# Shopify development and store guide

This is a practical index for this repository, not a copy of Shopify's documentation. Verify platform details against the linked official pages when changing the app.

| Topic | Repository implementation / next step | Official documentation |
| --- | --- | --- |
| App setup | React Router + TypeScript starter, CLI link/dev commands | https://shopify.dev/docs/apps/build/scaffold-app |
| Embedded interface | Polaris web components + App Bridge | https://shopify.dev/docs/api/app-home |
| Authentication | Official Shopify React Router package, Prisma sessions | https://shopify.dev/docs/api/shopify-app-react-router |
| Catalog | Overview and paginated title/status search | https://shopify.dev/docs/api/admin-graphql/2026-10/queries/products |
| Access scopes | App requests read_products only | https://shopify.dev/docs/api/usage/access-scopes |
| Pagination | Cursor from pageInfo, 25 products per page | https://shopify.dev/docs/api/usage/pagination-graphql |
| API limits | Errors displayed; explicit refresh to retry | https://shopify.dev/docs/api/usage/limits |
| Webhooks | Authenticated uninstall and scopes-update routes | https://shopify.dev/docs/apps/build/webhooks |
| Digital products | Versioned private ZIPs and delivery guide | https://help.shopify.com/en/manual/products/digital-service-product |
| Manual payments | Whish operating instructions | https://help.shopify.com/en/manual/payments/manual-payments |
| Orders | Managed through Shopify Admin; no order database exported | https://help.shopify.com/en/manual/orders |
| Collections | Count shown; manage via Shopify Admin | https://help.shopify.com/en/manual/products/collections |
| Theme | Existing live theme is separate from this admin app | https://shopify.dev/docs/storefronts/themes |
| Discounts | Historical discount snapshot, manage in Shopify Admin | https://help.shopify.com/en/manual/discounts |
| Deployment | HTTPS server + persistent database + Shopify config | https://shopify.dev/docs/apps/launch/deployment/deploy-to-hosting-service |

The existing store is Just AI, `just-ai-store.myshopify.com`, using USD. This identity was checked on 2 November 2026. This repository contains no full theme export, customer database, order export, payment credentials or store backup.
