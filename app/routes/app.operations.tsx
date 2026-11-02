import type { HeadersFunction, LoaderFunctionArgs } from "react-router";
import { boundary } from "@shopify/shopify-app-react-router/server";
import { authenticate } from "../shopify.server";

export async function loader({ request }: LoaderFunctionArgs) { await authenticate.admin(request); return null; }

export default function Operations() {
  return <s-page heading="Store operations">
    <s-section heading="Digital delivery">
      <s-ordered-list>
        <s-list-item>Choose the package version for the purchased product.</s-list-item>
        <s-list-item>Attach the ZIP through the store’s digital-delivery app and read back the saved filename.</s-list-item>
        <s-list-item>Check the product page, cart and checkout, then verify delivery with an authorized test order.</s-list-item>
      </s-ordered-list>
      <s-paragraph>Paid files belong in secure digital delivery. Keep customer download packages out of public theme assets.</s-paragraph>
    </s-section>
    <s-section heading="Whish manual payments">
      <s-paragraph>Confirm the received amount independently in Whish, match it to the correct order, then record the payment in Shopify Admin. A screenshot or bot command does not verify the transfer.</s-paragraph>
      <s-paragraph>راجع المبلغ المستلم في Whish وطابقه مع الطلب الصحيح قبل تأكيد الدفع وتسليم الملفات.</s-paragraph>
    </s-section>
    <s-section heading="Telegram integration">
      <s-paragraph>The repository includes the existing Telegram bot and its English/Arabic command guide. Configure the bot privately and check its identity and owner controls before activation.</s-paragraph>
    </s-section>
    <s-section slot="aside" heading="Shopify guides">
      <s-unordered-list>
        <s-list-item><s-link href="https://help.shopify.com/en/manual/products/digital-service-product" target="_blank">Digital products</s-link></s-list-item>
        <s-list-item><s-link href="https://help.shopify.com/en/manual/payments/manual-payments" target="_blank">Manual payments</s-link></s-list-item>
        <s-list-item><s-link href="https://help.shopify.com/en/manual/orders" target="_blank">Managing orders</s-link></s-list-item>
      </s-unordered-list>
    </s-section>
  </s-page>;
}

export const headers: HeadersFunction = (args) => boundary.headers(args);
