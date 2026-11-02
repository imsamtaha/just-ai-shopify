# Setup

1. Install Node.js 24 LTS and Git. Run `npm.cmd ci` from the repository root.
2. Copy `.env.example` to `.env` if it does not already exist. The example contains no credentials. Keep `DATABASE_URL=file:./dev.sqlite` for local development.
3. Run `npm.cmd run setup` to generate Prisma and apply migrations.
4. Create an app in the Shopify Dev Dashboard if needed. Choose custom distribution for your own store. The server uses `AppDistribution.SingleMerchant`.
5. Run `npm.cmd run config:link` and complete Shopify login in your browser. This fills the app identifier and links the local configuration.
6. Run `npm.cmd run dev` and select a development store. Open the preview URL from the CLI and install the app.
7. Confirm that the overview loads and compare product counts with Shopify Admin. Test search, filters, next page, refresh and product links.

The only app scope is `read_products`, which supports catalog and collection reads. No customer or order records are requested by this app. Its authentication state is kept in the local database, excluded from Git.

A valid app installation is required for `/app`, `/app/products` and `/app/operations`. A local HTTP response alone does not establish Shopify authentication.

On macOS/Linux replace `npm.cmd` with `npm` and use `cp .env.example .env`. Python dependencies for the Telegram integration are separate.
