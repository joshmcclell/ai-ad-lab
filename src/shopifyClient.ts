// shopifyClient.ts
// -----------------------------------------------------------------------------
// Minimal Shopify Admin GraphQL API client using the built-in fetch (Node 18+).
// We use GraphQL because it is Shopify's primary, future-proof Admin API; the
// older REST Admin API is being wound down.
//
// Auth: a custom app's Admin API access token, sent as X-Shopify-Access-Token.
// Docs: https://shopify.dev/docs/api/admin-graphql
// -----------------------------------------------------------------------------

import "dotenv/config";

const DOMAIN = process.env.SHOPIFY_STORE_DOMAIN!;
const TOKEN = process.env.SHOPIFY_ADMIN_TOKEN!;
const VERSION = process.env.SHOPIFY_API_VERSION ?? "2025-01";

const ENDPOINT = `https://${DOMAIN}/admin/api/${VERSION}/graphql.json`;

/** Run a GraphQL query/mutation against the Shopify Admin API. */
export async function shopifyGraphQL<T = unknown>(
  query: string,
  variables: Record<string, unknown> = {},
): Promise<T> {
  const res = await fetch(ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Shopify-Access-Token": TOKEN,
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!res.ok) {
    throw new Error(`Shopify HTTP ${res.status}: ${await res.text()}`);
  }

  const json = (await res.json()) as { data: T; errors?: unknown };
  if (json.errors) {
    throw new Error(`Shopify GraphQL error: ${JSON.stringify(json.errors)}`);
  }
  return json.data;
}

/** Structured product content we'll create. Mirrors Claude's output schema. */
export interface ProductContent {
  title: string;
  descriptionHtml: string;
  seoTitle: string;
  seoDescription: string;
  tags: string[];
}

/**
 * Create a DRAFT product in Shopify. We default to DRAFT so nothing goes live
 * without a human reviewing AI-generated copy first (safer + compliance-friendly).
 */
export async function createDraftProduct(c: ProductContent): Promise<string> {
  const mutation = `
    mutation productCreate($input: ProductInput!) {
      productCreate(input: $input) {
        product { id title status }
        userErrors { field message }
      }
    }`;

  const data = await shopifyGraphQL<{
    productCreate: {
      product: { id: string } | null;
      userErrors: { field: string[]; message: string }[];
    };
  }>(mutation, {
    input: {
      title: c.title,
      descriptionHtml: c.descriptionHtml,
      tags: c.tags,
      status: "DRAFT",
      seo: { title: c.seoTitle, description: c.seoDescription },
    },
  });

  const errs = data.productCreate.userErrors;
  if (errs.length) throw new Error(`productCreate: ${JSON.stringify(errs)}`);
  return data.productCreate.product!.id;
}
