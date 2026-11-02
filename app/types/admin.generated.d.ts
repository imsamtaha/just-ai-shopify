/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable eslint-comments/no-unlimited-disable */
/* eslint-disable */
import type * as AdminTypes from './admin.types.js';

export type JustAiCatalogQueryVariables = AdminTypes.Exact<{
  first: AdminTypes.Scalars['Int']['input'];
  after?: AdminTypes.InputMaybe<AdminTypes.Scalars['String']['input']>;
  query?: AdminTypes.InputMaybe<AdminTypes.Scalars['String']['input']>;
}>;


export type JustAiCatalogQuery = { shop: Pick<AdminTypes.Shop, 'name' | 'myshopifyDomain' | 'currencyCode'>, products: { nodes: Array<(
      Pick<AdminTypes.Product, 'id' | 'title' | 'handle' | 'status' | 'vendor' | 'productType' | 'updatedAt'>
      & { variants: { nodes: Array<Pick<AdminTypes.ProductVariant, 'id' | 'price'>> } }
    )>, pageInfo: Pick<AdminTypes.PageInfo, 'hasNextPage' | 'endCursor'> } };

export type JustAiOverviewQueryVariables = AdminTypes.Exact<{ [key: string]: never; }>;


export type JustAiOverviewQuery = { shop: Pick<AdminTypes.Shop, 'name' | 'myshopifyDomain' | 'currencyCode'>, total?: AdminTypes.Maybe<Pick<AdminTypes.Count, 'count' | 'precision'>>, active?: AdminTypes.Maybe<Pick<AdminTypes.Count, 'count' | 'precision'>>, draft?: AdminTypes.Maybe<Pick<AdminTypes.Count, 'count' | 'precision'>>, archived?: AdminTypes.Maybe<Pick<AdminTypes.Count, 'count' | 'precision'>>, collectionsCount?: AdminTypes.Maybe<Pick<AdminTypes.Count, 'count' | 'precision'>> };

interface GeneratedQueryTypes {
  "#graphql\nquery JustAiCatalog($first: Int!, $after: String, $query: String) {\n  shop { name myshopifyDomain currencyCode }\n  products(first: $first, after: $after, query: $query, sortKey: UPDATED_AT, reverse: true) {\n    nodes { id title handle status vendor productType updatedAt variants(first: 1) { nodes { id price } } }\n    pageInfo { hasNextPage endCursor }\n  }\n}\n": {return: JustAiCatalogQuery, variables: JustAiCatalogQueryVariables},
  "#graphql\nquery JustAiOverview {\n  shop { name myshopifyDomain currencyCode }\n  total: productsCount { count precision }\n  active: productsCount(query: \"status:active\") { count precision }\n  draft: productsCount(query: \"status:draft\") { count precision }\n  archived: productsCount(query: \"status:archived\") { count precision }\n  collectionsCount { count precision }\n}\n": {return: JustAiOverviewQuery, variables: JustAiOverviewQueryVariables},
}

interface GeneratedMutationTypes {
}
declare module '@shopify/admin-api-client' {
  type InputMaybe<T> = AdminTypes.InputMaybe<T>;
  interface AdminQueries extends GeneratedQueryTypes {}
  interface AdminMutations extends GeneratedMutationTypes {}
}
