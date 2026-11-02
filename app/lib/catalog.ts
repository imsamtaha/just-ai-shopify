export type Count = { count: number; precision: string } | null;

export function countLabel(value: Count): string {
  if (!value) return "Unavailable";
  return value.count.toLocaleString("en-US") + (value.precision === "AT_LEAST" ? "+" : "");
}

export function catalogParameters(url: URL) {
  const search = (url.searchParams.get("q") || "").trim().slice(0, 200);
  const rawStatus = url.searchParams.get("status") || "";
  const status = ["ACTIVE", "DRAFT", "ARCHIVED"].includes(rawStatus) ? rawStatus : "";
  const escaped = search.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  const phrase = search ? 'title:"' + escaped + '"' : "";
  const query = [phrase, status ? "status:" + status.toLowerCase() : ""].filter(Boolean).join(" AND ");
  return { search, status, variables: { first: 25, after: url.searchParams.get("after") || null, query: query || null } };
}

export function nextCatalogPage(search: string, status: string, cursor: string): string {
  return "/app/products?" + new URLSearchParams({ q: search, status, after: cursor });
}

export function productAdminUrl(shop: string, gid: string): string | null {
  if (!/^[a-z0-9][a-z0-9-]*\.myshopify\.com$/i.test(shop)) return null;
  const match = /^gid:\/\/shopify\/Product\/(\d+)$/.exec(gid);
  return match ? "https://" + shop + "/admin/products/" + match[1] : null;
}

export function formatPrice(price: string | undefined, currency: string): string {
  if (!price || !Number.isFinite(Number(price))) return "Unavailable";
  try { return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(Number(price)); }
  catch { return price + " " + currency; }
}
