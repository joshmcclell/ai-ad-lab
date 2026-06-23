// webhookServer.ts
// -----------------------------------------------------------------------------
// Receives Shopify webhooks (e.g. orders/create, products/create) and lets you
// trigger downstream automation — e.g. ask Claude to draft a thank-you email or
// kick off creative generation for a newly added product.
//
// Run:  npm run server   (then expose it with `ngrok http 3000` or cloudflared)
// Register the public URL in Shopify: Settings → Notifications → Webhooks,
// or via the Admin API webhookSubscriptionCreate mutation.
//
// SECURITY: Shopify signs every webhook with an HMAC. We verify it on the RAW
// body before trusting anything. Never act on an unverified webhook.
// -----------------------------------------------------------------------------

import express from "express";
import crypto from "node:crypto";
import "dotenv/config";
import { ask } from "./claudeClient.js";

const app = express();
const SECRET = process.env.SHOPIFY_WEBHOOK_SECRET!;

// We need the RAW body to verify the HMAC, so capture it as a Buffer.
app.use(express.raw({ type: "application/json" }));

/** Verify the X-Shopify-Hmac-Sha256 header against the raw request body. */
function verifyShopifyWebhook(rawBody: Buffer, hmacHeader: string): boolean {
  const digest = crypto
    .createHmac("sha256", SECRET)
    .update(rawBody)
    .digest("base64");
  // timingSafeEqual avoids leaking timing info; lengths must match first.
  const a = Buffer.from(digest);
  const b = Buffer.from(hmacHeader ?? "");
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

app.post("/webhooks/shopify", async (req, res) => {
  const hmac = req.get("X-Shopify-Hmac-Sha256") ?? "";
  if (!verifyShopifyWebhook(req.body, hmac)) {
    return res.status(401).send("Invalid HMAC");
  }

  const topic = req.get("X-Shopify-Topic"); // e.g. "orders/create"
  const payload = JSON.parse(req.body.toString("utf8"));

  // ACK fast (Shopify expects a 200 within ~5s); do slow work async.
  res.status(200).send("ok");

  // ---- Example downstream automation -------------------------------------
  if (topic === "orders/create") {
    // Draft a personalised thank-you email with Claude. In production you'd
    // queue this and send via Gmail/Klaviyo/Shopify Email rather than logging.
    const email = await ask(
      `Write a short, warm order-confirmation email for ${payload.customer?.first_name ?? "a customer"} ` +
        `who just bought: ${payload.line_items?.map((l: any) => l.title).join(", ")}. ` +
        `British English. No discounts promised. Include realistic dispatch expectations.`,
    );
    console.log(`\n[orders/create] Draft email:\n${email}\n`);
  }
});

const port = Number(process.env.PORT ?? 3000);
app.listen(port, () => console.log(`Webhook server listening on :${port}`));
