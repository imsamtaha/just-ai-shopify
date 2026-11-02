import type { HeadersFunction, LoaderFunctionArgs } from "react-router";
import { useLoaderData, useRevalidator } from "react-router";
import { boundary } from "@shopify/shopify-app-react-router/server";
import { authenticate } from "../shopify.server";
import { loadOverview } from "../services/catalog.server";
import { countLabel } from "../lib/catalog";

export async function loader({ request }: LoaderFunctionArgs) {
  const { admin } = await authenticate.admin(request);
  return loadOverview(admin);
}

export default function Dashboard() {
  const { overview, error, fetchedAt } = useLoaderData<typeof loader>();
  const revalidator = useRevalidator();
  return (
    <s-page heading="JUST AI · Store overview">
      <s-button slot="primary-action" onClick={() => revalidator.revalidate()} {...(revalidator.state !== "idle" ? { loading: true } : {})}>Refresh</s-button>
      {error && <s-banner tone="critical" heading="Store data unavailable">{error}</s-banner>}
      {overview && <>
        <s-section heading={overview.shop.name}>
          <s-paragraph>{overview.shop.myshopifyDomain} · {overview.shop.currencyCode}</s-paragraph>
          <s-paragraph>Review your catalog and open Shopify Admin to make changes.</s-paragraph>
          <s-stack direction="inline" gap="base">
            {([
              ["Total products", overview.total], ["Active", overview.active],
              ["Draft", overview.draft], ["Archived", overview.archived],
              ["Collections", overview.collectionsCount],
            ] as const).map(([label, count]) => (
              <s-box key={label} padding="base" borderWidth="base" borderRadius="base">
                <s-heading>{label}</s-heading><s-paragraph>{countLabel(count)}</s-paragraph>
              </s-box>
            ))}
          </s-stack>
          <s-paragraph>Fetched: {fetchedAt} (UTC)</s-paragraph>
        </s-section>
        <s-section heading="Your workspace">
          <s-stack direction="inline" gap="base">
            <s-button href="/app/products">Browse products</s-button>
            <s-button href="/app/operations">Operations guide</s-button>
            <s-button href={"https://" + overview.shop.myshopifyDomain + "/admin"} target="_blank">Open Shopify Admin</s-button>
          </s-stack>
        </s-section>
      </>}
      <s-section slot="aside" heading="Digital products">
        <s-paragraph>Check the downloadable file attached to each product before promising automatic delivery. Product status alone does not confirm payment or file delivery.</s-paragraph>
        <s-link href="/app/operations">View the payment and delivery guide</s-link>
      </s-section>
    </s-page>
  );
}

export const headers: HeadersFunction = (args) => boundary.headers(args);
