import type { HeadersFunction, LoaderFunctionArgs } from "react-router";
import { Form, useLoaderData, useNavigation } from "react-router";
import { boundary } from "@shopify/shopify-app-react-router/server";
import { authenticate } from "../shopify.server";
import { loadCatalog } from "../services/catalog.server";
import { formatPrice, nextCatalogPage, productAdminUrl } from "../lib/catalog";

export async function loader({ request }: LoaderFunctionArgs) {
  const { admin } = await authenticate.admin(request);
  return loadCatalog(admin, new URL(request.url));
}

export default function Products() {
  const { catalog, error, search, status } = useLoaderData<typeof loader>();
  const busy = useNavigation().state !== "idle";
  return (
    <s-page heading="Products">
      <s-section heading="Find a product">
        <Form method="get" key={search + ":" + status}>
          <s-grid gridTemplateColumns="repeat(auto-fit, minmax(180px, 1fr))" gap="base" alignItems="end">
            <s-text-field label="Product title" name="q" defaultValue={search} maxLength={200} placeholder="Search your catalog" />
            <s-select label="Status" name="status">
              {[["", "All statuses"], ["ACTIVE", "Active"], ["DRAFT", "Draft"], ["ARCHIVED", "Archived"]].map(([value, label]) => (
                <s-option key={value} value={value} {...(status === value ? { defaultSelected: true } : {})}>{label}</s-option>
              ))}
            </s-select>
            <s-button type="submit" variant="primary" {...(busy ? { loading: true } : {})}>Search</s-button>
            <s-button href="/app/products">Clear</s-button>
          </s-grid>
        </Form>
      </s-section>
      {error && <s-banner tone="critical" heading="Products unavailable">{error}</s-banner>}
      {catalog && <s-section heading="Catalog">
        <s-paragraph>Prices show the first variant in {catalog.shop.currencyCode}. Open a product to review all variants.</s-paragraph>
        {catalog.products.nodes.length === 0 ? <s-paragraph>No products match this search. Try another title or clear the filters.</s-paragraph> : (
          <s-table>
            <s-table-header-row><s-table-header>Product</s-table-header><s-table-header>Status</s-table-header><s-table-header>First variant price</s-table-header><s-table-header>Vendor</s-table-header></s-table-header-row>
            <s-table-body>{catalog.products.nodes.map((product) => {
              const href = productAdminUrl(catalog.shop.myshopifyDomain, product.id);
              return <s-table-row key={product.id}>
                <s-table-cell>{href ? <s-link href={href} target="_blank">{product.title}</s-link> : product.title}</s-table-cell>
                <s-table-cell><s-badge tone={product.status === "ACTIVE" ? "success" : "neutral"}>{product.status}</s-badge></s-table-cell>
                <s-table-cell>{formatPrice(product.variants.nodes[0]?.price, catalog.shop.currencyCode)}</s-table-cell>
                <s-table-cell>{product.vendor || "—"}</s-table-cell>
              </s-table-row>;
            })}</s-table-body>
          </s-table>
        )}
        <s-stack direction="inline" gap="base">
          <s-button href={"/app/products?" + new URLSearchParams({ q: search, status })}>First page</s-button>
          {catalog.products.pageInfo.hasNextPage && catalog.products.pageInfo.endCursor && <s-button href={nextCatalogPage(search, status, catalog.products.pageInfo.endCursor)}>Next page</s-button>}
        </s-stack>
      </s-section>}
    </s-page>
  );
}

export const headers: HeadersFunction = (args) => boundary.headers(args);
