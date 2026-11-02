# Dependency maintenance

The lockfile was generated with npm 11.17.0 and Node.js 24.19.0. Use `npm ci` for repeatable installs.

The project declares runtime and tooling dependencies explicitly. `.npmrc` uses `legacy-peer-deps=true` to avoid auto-installing unrelated optional framework adapters. Keep this setting when running `npm ci`; linting, type checks, tests, code generation and the production build validate the dependencies used by this app.

## Runtime audit fixes applied on 2 November 2026

- Express 4 uses body-parser 1.20.9 or newer through a scoped override, addressing [GHSA-27r3-jxmh-p828](https://github.com/advisories/GHSA-27r3-jxmh-p828).
- Prisma's configuration loader uses deepmerge-ts 8 through a scoped override, addressing [GHSA-ggr8-5vv4-36mx](https://github.com/advisories/GHSA-ggr8-5vv4-36mx). Prisma generation and migration passed with this version.
- Routes are declared explicitly in `app/routes.ts`. The unused filesystem route-discovery dependency was removed, eliminating its older minimatch dependency affected by [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249).

The final `npm audit --omit=dev` reported zero vulnerabilities. This is a dated runtime-dependency audit, not a full security certification or a clean audit claim for development tooling. Recheck before production deployment.

Generated files in `app/types/` are produced by Shopify GraphQL codegen and excluded from ESLint; they are still available to TypeScript.
