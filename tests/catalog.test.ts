import { describe, expect, it, vi } from "vitest";
import { catalogParameters, countLabel, formatPrice, nextCatalogPage, productAdminUrl } from "../app/lib/catalog";
import { loadCatalog, loadOverview } from "../app/services/catalog.server";

describe("catalog search and navigation", () => {
  it("uses a bounded first page and no filter by default", () => {
    expect(catalogParameters(new URL("https://app.example/app/products")).variables).toEqual({ first: 25, after: null, query: null });
  });
  it("quotes user input so it cannot replace the status filter", () => {
    const url = new URL("https://app.example/app/products");
    url.searchParams.set("q", 'x" OR status:active');
    url.searchParams.set("status", "DRAFT");
    const result = catalogParameters(url);
    expect(result.variables.query).toBe('title:"x\\" OR status:active" AND status:draft');
  });
  it("rejects unknown statuses and limits search length", () => {
    const result = catalogParameters(new URL("https://app.example/?status=delete&q=" + "x".repeat(250)));
    expect(result.status).toBe("");
    expect(result.search).toHaveLength(200);
  });
  it("preserves Arabic, filters and the opaque cursor during pagination", () => {
    const url = new URL(nextCatalogPage("قوالب", "ACTIVE", "a+b/=="), "https://app.example");
    const parsed = catalogParameters(url);
    expect(parsed.search).toBe("قوالب");
    expect(parsed.status).toBe("ACTIVE");
    expect(parsed.variables.after).toBe("a+b/==");
  });
  it("limits product links to valid Shopify hosts and product GIDs", () => {
    expect(productAdminUrl("just-ai-store.myshopify.com", "gid://shopify/Product/123")).toBe("https://just-ai-store.myshopify.com/admin/products/123");
    expect(productAdminUrl("shop.myshopify.com.evil.example", "gid://shopify/Product/123")).toBeNull();
    expect(productAdminUrl("shop.myshopify.com", "gid://shopify/Order/123")).toBeNull();
  });
  it("distinguishes unavailable counts, zero, and lower bounds", () => {
    expect(countLabel(null)).toBe("Unavailable");
    expect(countLabel({ count: 0, precision: "EXACT" })).toBe("0");
    expect(countLabel({ count: 10000, precision: "AT_LEAST" })).toBe("10,000+");
    expect(formatPrice("0.00", "USD")).toBe("$0.00");
    expect(formatPrice(undefined, "USD")).toBe("Unavailable");
  });
});

describe("Shopify failures and results", () => {
  it("returns a real empty catalog distinctly from a failure", async () => {
    const catalog = { shop: { name: "Test", myshopifyDomain: "test.myshopify.com", currencyCode: "USD" }, products: { nodes: [], pageInfo: { hasNextPage: false, endCursor: null } } };
    const admin = { graphql: vi.fn().mockResolvedValue(Response.json({ data: catalog })) };
    const result = await loadCatalog(admin, new URL("https://app.example/"));
    expect(result.catalog).toEqual(catalog);
    expect(result.error).toBeNull();
  });
  it.each([
    [500, {}], [200, { errors: [{ message: "private-provider-detail" }], data: { shop: {} } }], [200, {}],
  ])("does not show partial or failed HTTP %s data as an empty catalog", async (status, body) => {
    const admin = { graphql: vi.fn().mockResolvedValue(Response.json(body, { status })) };
    const result = await loadCatalog(admin, new URL("https://app.example/"));
    expect(result.catalog).toBeNull();
    expect(result.error).toContain("could not return");
    expect(result.error).not.toContain("private-provider-detail");
  });
  it("hides raw transport errors", async () => {
    const admin = { graphql: vi.fn().mockRejectedValue(new Error("token=private")) };
    const result = await loadOverview(admin);
    expect(result.overview).toBeNull();
    expect(result.fetchedAt).toBeNull();
    expect(result.error).not.toContain("private");
  });
  it("preserves Shopify redirects instead of replacing them with error text", async () => {
    const response = new Response(null, { status: 302, headers: { Location: "/auth/login" } });
    const admin = { graphql: vi.fn().mockRejectedValue(response) };
    await expect(loadOverview(admin)).rejects.toBe(response);
  });
});
