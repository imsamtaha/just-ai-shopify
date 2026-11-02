"""Small GraphQL client with fixed host, verified shop identity, and no retries."""
import time
import httpx

from .shopify_config import SHOP_DOMAIN, SHOP_ID

IDENTITY = """query BotIdentity {
  shop { id name myshopifyDomain currencyCode }
  currentAppInstallation { accessScopes { handle } }
}"""
ORDER_FIELDS = """id name updatedAt createdAt note closed cancelledAt test canMarkAsPaid
  paymentGatewayNames displayFinancialStatus displayFulfillmentStatus
  totalPriceSet { shopMoney { amount currencyCode } }
  totalOutstandingSet { shopMoney { amount currencyCode } }"""
PRODUCT_FIELDS = "id title status descriptionHtml updatedAt"
OPERATIONS = {
    "identity": IDENTITY,
    "orders": "query BotOrders($query:String,$after:String) { orders(first:10,after:$after,query:$query,sortKey:CREATED_AT,reverse:true) { nodes { " + ORDER_FIELDS + " } pageInfo { endCursor hasNextPage } } }",
    "order": "query BotOrder($id:ID!) { order(id:$id) { " + ORDER_FIELDS + " lineItems(first:20) { nodes { name quantity } pageInfo { hasNextPage } } } }",
    "products": "query BotProducts($query:String,$after:String) { products(first:10,after:$after,query:$query) { nodes { id title status } pageInfo { endCursor hasNextPage } } }",
    "product": "query BotProduct($id:ID!) { product(id:$id) { " + PRODUCT_FIELDS + " variants(first:20) { nodes { id title price } pageInfo { hasNextPage } } } }",
    "variant": "query BotVariant($id:ID!) { node(id:$id) { ... on ProductVariant { id title price product { id title updatedAt } } } }",
    "product_update": "mutation BotProductUpdate($product:ProductUpdateInput!) { productUpdate(product:$product) { product { id } userErrors { field message } } }",
    "price": "mutation BotPrice($productId:ID!,$variants:[ProductVariantsBulkInput!]!) { productVariantsBulkUpdate(productId:$productId,variants:$variants,allowPartialUpdates:false) { productVariants { id price } userErrors { field message } } }",
    "order_note": "mutation BotOrderNote($input:OrderInput!) { orderUpdate(input:$input) { order { id } userErrors { field message } } }",
    "mark_paid": "mutation BotMarkPaid($input:OrderMarkAsPaidInput!) { orderMarkAsPaid(input:$input) { order { id } userErrors { field message } } }",
    "archive_order": "mutation BotArchive($input:OrderCloseInput!) { orderClose(input:$input) { order { id } userErrors { field message } } }",
    "reopen_order": "mutation BotReopen($input:OrderOpenInput!) { orderOpen(input:$input) { order { id } userErrors { field message } } }",
}
MUTATIONS = {
    "product_update": ("productUpdate", "write_products"),
    "price": ("productVariantsBulkUpdate", "write_products"),
    "order_note": ("orderUpdate", "write_orders"),
    "mark_paid": ("orderMarkAsPaid", "write_orders"),
    "archive_order": ("orderClose", "write_orders"),
    "reopen_order": ("orderOpen", "write_orders"),
}


class ShopifyError(Exception):
    """Only stable codes escape this module; never upstream response bodies."""
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class ShopifyClient:
    def __init__(self, settings, transport=None, clock=time.monotonic):
        self.settings = settings
        self.clock = clock
        self._token, self._expires = "", 0
        self._identity, self._identity_until, self.scopes = None, 0, set()
        self._transport = transport
        self._http = None

    @property
    def http(self):
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False, transport=self._transport)
        return self._http

    async def close(self):
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        self._token, self._expires = "", 0
        self._identity, self._identity_until, self.scopes = None, 0, set()

    def check_config(self):
        if not self.settings.ready:
            raise ShopifyError("not_configured")
        if self.settings.domain != SHOP_DOMAIN or self.settings.shop_id != SHOP_ID:
            raise ShopifyError("wrong_shop")

    async def access_token(self):
        self.check_config()
        if self.settings.token:
            return self.settings.token
        if self._token and self.clock() < self._expires:
            return self._token
        try:
            response = await self.http.post(f"https://{SHOP_DOMAIN}/admin/oauth/access_token", data={
                "grant_type": "client_credentials", "client_id": self.settings.client_id,
                "client_secret": self.settings.client_secret,
            })
            if response.status_code != 200:
                raise ShopifyError("authentication")
            body = response.json()
            token = body.get("access_token")
            expires = int(body.get("expires_in", 0))
            if not isinstance(token, str) or not token or expires <= 60:
                raise ShopifyError("authentication")
            self._token, self._expires = token, self.clock() + expires - 60
            # Recheck store identity and scopes after refreshing credentials.
            self._identity_until = 0
            return token
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            raise ShopifyError("authentication") from None

    async def _request(self, operation, variables=None, mutation=False):
        token = await self.access_token()
        try:
            response = await self.http.post(
                f"https://{SHOP_DOMAIN}/admin/api/{self.settings.api_version}/graphql.json",
                headers={"X-Shopify-Access-Token": token},
                json={"query": OPERATIONS[operation], "variables": variables or {}},
            )
            if response.status_code in (401, 403):
                self._token, self._expires, self._identity_until = "", 0, 0
                raise ShopifyError("access_denied")
            if response.status_code != 200:
                raise ShopifyError("outcome_unknown" if mutation else "unavailable")
            body = response.json()
            if not isinstance(body, dict) or body.get("errors") or not isinstance(body.get("data"), dict):
                raise ShopifyError("outcome_unknown" if mutation else "query_failed")
            return body["data"]
        except (httpx.HTTPError, ValueError, TypeError, AttributeError):
            raise ShopifyError("outcome_unknown" if mutation else "unavailable") from None

    async def identity(self, force=False):
        self.check_config()
        # Acquire/refresh first so cached identity never outlives its credentials.
        await self.access_token()
        if not force and self._identity and self.clock() < self._identity_until:
            return self._identity
        data = await self._request("identity")
        shop = data.get("shop") or {}
        if shop.get("id") != SHOP_ID:
            self._identity, self._identity_until = None, 0
            raise ShopifyError("wrong_shop")
        try:
            self.scopes = {item["handle"] for item in data["currentAppInstallation"]["accessScopes"]}
        except (KeyError, TypeError):
            raise ShopifyError("query_failed") from None
        self._identity, self._identity_until = shop, self.clock() + 60
        return shop

    async def query(self, operation, variables=None):
        if operation not in ("orders", "order", "products", "product", "variant"):
            raise ShopifyError("unsupported")
        await self.identity()
        family = "orders" if operation in ("orders", "order") else "products"
        if not ({"read_" + family, "write_" + family} & self.scopes):
            raise ShopifyError("missing_scope")
        return await self._request(operation, variables)

    async def mutate(self, operation, variables):
        if operation not in MUTATIONS:
            raise ShopifyError("unsupported")
        await self.identity(force=True)
        root, scope = MUTATIONS[operation]
        if scope not in self.scopes:
            raise ShopifyError("missing_scope")
        data = await self._request(operation, variables, mutation=True)
        payload = data.get(root)
        if not isinstance(payload, dict) or "userErrors" not in payload:
            raise ShopifyError("outcome_unknown")
        if payload["userErrors"]:
            raise ShopifyError("rejected")
        key = "productVariants" if operation == "price" else "product" if operation == "product_update" else "order"
        if not payload.get(key):
            raise ShopifyError("outcome_unknown")
        return payload
