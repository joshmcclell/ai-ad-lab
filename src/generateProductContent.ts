// generateProductContent.ts
// -----------------------------------------------------------------------------
// Workflow: raw product idea  →  Claude writes structured, conversion-focused
// copy  →  we create a DRAFT product in Shopify for human review.
//
// Run:  npm run product -- "Adjustable laptop stand, aluminium, foldable"
//
// Uses STRUCTURED OUTPUTS (output_config.format via messages.parse) so Claude
// returns valid, typed JSON every time — no fragile string parsing.
// -----------------------------------------------------------------------------

import { z } from "zod";
import { zodOutputFormat } from "@anthropic-ai/sdk/helpers/zod";
import { claude, MODEL } from "./claudeClient.js";
import { createDraftProduct, type ProductContent } from "./shopifyClient.js";

// The exact shape we want back. Zod both validates and types the result.
const ProductSchema = z.object({
  title: z.string().describe("Punchy, benefit-led product title, <70 chars"),
  descriptionHtml: z
    .string()
    .describe("HTML body: hook, 3-5 benefit bullets, short spec list, CTA"),
  seoTitle: z.string().describe("SEO title tag, <60 chars, includes keyword"),
  seoDescription: z.string().describe("Meta description, <155 chars"),
  tags: z.array(z.string()).describe("5-8 lowercase tags for filtering/collections"),
});

const SYSTEM = `You are a senior DTC e-commerce copywriter for a UK/EU dropshipping store.
Write honest, benefit-led copy that converts WITHOUT making prohibited claims.
Hard rules (UK ASA/CAP + EU consumer law):
- No unverifiable health, medical, or "cure" claims.
- No fake scarcity, fake reviews, or invented endorsements.
- No absolute superlatives you cannot substantiate ("the best", "#1").
- Be specific about what the product does; never imply guaranteed results.
Tone: clear, warm, confident. Brytish English spelling.`;

export async function generateProductContent(idea: string): Promise<ProductContent> {
  const response = await claude.messages.parse({
    model: MODEL,
    max_tokens: 4000,
    system: SYSTEM,
    messages: [
      {
        role: "user",
        content: `Write store copy for this product idea:\n\n"${idea}"\n\nReturn the structured fields.`,
      },
    ],
    output_config: { format: zodOutputFormat(ProductSchema) },
  });

  // parsed_output is the validated object (or null if the model refused).
  const parsed = response.parsed_output;
  if (!parsed) throw new Error("Claude did not return valid product content.");
  return parsed;
}

// --- CLI entrypoint ---------------------------------------------------------
const idea = process.argv.slice(2).join(" ");
if (!idea) {
  console.error('Usage: npm run product -- "your product idea"');
  process.exit(1);
}

const content = await generateProductContent(idea);
console.log("Generated copy:\n", JSON.stringify(content, null, 2));

// Comment this out if you only want to preview without touching Shopify.
const productId = await createDraftProduct(content);
console.log(`\n✅ Created DRAFT product in Shopify: ${productId}`);
console.log("Review and publish it manually in the Shopify admin.");
