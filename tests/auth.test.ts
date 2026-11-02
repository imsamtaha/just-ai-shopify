import { beforeEach, describe, expect, it, vi } from "vitest";
const mocks = vi.hoisted(() => ({ admin: vi.fn(), catalog: vi.fn(), overview: vi.fn() }));
vi.mock("../app/shopify.server", () => ({ authenticate: { admin: mocks.admin } }));
vi.mock("../app/services/catalog.server", () => ({ loadCatalog: mocks.catalog, loadOverview: mocks.overview }));
vi.mock("@shopify/shopify-app-react-router/server", () => ({ boundary: { headers: vi.fn() } }));
import { loader as products } from "../app/routes/app.products";
import { loader as overview } from "../app/routes/app._index";
import { loader as operations } from "../app/routes/app.operations";

describe("protected route loaders", () => {
  beforeEach(() => vi.clearAllMocks());
  it.each([products, overview, operations])("rejects an unauthenticated request before reading store data", async (loader) => {
    const rejection = new Response("Unauthorized", { status: 401 });
    mocks.admin.mockRejectedValue(rejection);
    await expect(loader({ request: new Request("https://app.example/app"), params: {}, context: {} })).rejects.toBe(rejection);
    expect(mocks.catalog).not.toHaveBeenCalled();
    expect(mocks.overview).not.toHaveBeenCalled();
  });
  it("passes only the authenticated API client to the catalog service", async () => {
    const client = { graphql: vi.fn() };
    mocks.admin.mockResolvedValue({ admin: client, session: { accessToken: "private" } });
    mocks.catalog.mockResolvedValue({ catalog: null, error: "offline" });
    const result = await products({ request: new Request("https://app.example/app/products?q=basic"), params: {}, context: {} });
    expect(mocks.catalog).toHaveBeenCalledWith(client, new URL("https://app.example/app/products?q=basic"));
    expect(JSON.stringify(result)).not.toContain("private");
  });
});
