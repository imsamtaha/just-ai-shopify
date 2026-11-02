import { catalogParameters } from "../lib/catalog";
import type { Count } from "../lib/catalog";

export const CATALOG_QUERY = `#graphql
query JustAiCatalog($first: Int!, $after: String, $query: String) {
  shop { name myshopifyDomain currencyCode }
  products(first: $first, after: $after, query: $query, sortKey: UPDATED_AT, reverse: true) {
    nodes { id title handle status vendor productType updatedAt variants(first: 1) { nodes { id price } } }
    pageInfo { hasNextPage endCursor }
  }
}
`;

export const OVERVIEW_QUERY = `#graphql
query JustAiOverview {
  shop { name myshopifyDomain currencyCode }
  total: productsCount { count precision }
  active: productsCount(query: "status:active") { count precision }
  draft: productsCount(query: "status:draft") { count precision }
  archived: productsCount(query: "status:archived") { count precision }
  collectionsCount { count precision }
}
`;

type Shop = { name: string; myshopifyDomain: string; currencyCode: string };
export type Catalog = {
  shop: Shop;
  products: {
    nodes: { id: string; title: string; handle: string; status: string; vendor: string; productType: string; updatedAt: string; variants: { nodes: { id: string; price: string }[] } }[];
    pageInfo: { hasNextPage: boolean; endCursor: string | null };
  };
};
export type Overview = { shop: Shop; total: Count; active: Count; draft: Count; archived: Count; collectionsCount: Count };
export type AdminClient = { graphql: (query: string, options?: { variables?: Record<string, unknown> }) => Promise<Response> };

async function queryData<T>(admin: AdminClient, query: string, variables?: Record<string, unknown>): Promise<T> {
  const response = await admin.graphql(query, { variables });
  if (!response.ok) throw new Error("Shopify request failed");
  const body = await response.json();
  if (body.errors?.length || !body.data) throw new Error("Shopify returned incomplete data");
  return body.data as T;
}

const unavailable = "Shopify could not return the catalog. Refresh to retry. If this continues, check the app's read_products permission in Shopify Admin.";

export async function loadCatalog(admin: AdminClient, url: URL) {
  const params = catalogParameters(url);
  try {
    const catalog = await queryData<Catalog>(admin, CATALOG_QUERY, params.variables);
    return { catalog, error: null, search: params.search, status: params.status };
  } catch (error) {
    // Preserve Shopify authentication redirects and HTTP challenges.
    if (error instanceof Response) throw error;
    return { catalog: null, error: unavailable, search: params.search, status: params.status };
  }
}

export async function loadOverview(admin: AdminClient) {
  try {
    const overview = await queryData<Overview>(admin, OVERVIEW_QUERY);
    return { overview, error: null, fetchedAt: new Date().toISOString() };
  } catch (error) {
    if (error instanceof Response) throw error;
    return { overview: null, error: unavailable, fetchedAt: null };
  }
}
