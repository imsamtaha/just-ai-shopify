# Deployment

Repository creation does not deploy the app. Shopify configuration deployment and web-server hosting are separate steps.

1. Run local checks and complete a real development-store installation.
2. Choose a Node.js/container host with HTTPS and persistent storage.
3. Configure `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`, `SHOPIFY_APP_URL`, `SCOPES=read_products`, and `DATABASE_URL` privately.
4. For the provided SQLite schema, use a persistent disk and a single app instance. For multiple instances, migrate the schema and migrations to a managed shared database before deploying.
5. Build the container or run `npm ci`, `npm run setup`, `npm run build`, `npm start`.
6. Update the linked TOML application and redirect URLs to the host's HTTPS URL.
7. After authorizing release, deploy Shopify configuration with `npm run deploy`. This does not host the Node server.
8. Verify installation, authentication, embedded navigation, product queries, refresh, and signed uninstall/scopes webhooks on the actual host.

No public App Store submission is prepared. Public distribution would require privacy/compliance webhook handling, review requirements and a separate distribution decision.

Official reference: https://shopify.dev/docs/apps/launch/deployment/deploy-to-hosting-service
