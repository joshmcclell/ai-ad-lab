// Minimal PayPal REST helpers: OAuth token + webhook signature verification.
// Docs: docs/07-paypal-integration.md

const BASE =
  process.env.PAYPAL_ENV === "live"
    ? "https://api-m.paypal.com"
    : "https://api-m.sandbox.paypal.com";

export function paypalApiBase() {
  return BASE;
}

// Exchange client credentials for an OAuth2 access token.
export async function getAccessToken(): Promise<string> {
  const auth = Buffer.from(
    `${process.env.PAYPAL_CLIENT_ID}:${process.env.PAYPAL_CLIENT_SECRET}`
  ).toString("base64");

  const res = await fetch(`${BASE}/v1/oauth2/token`, {
    method: "POST",
    headers: {
      Authorization: `Basic ${auth}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: "grant_type=client_credentials",
  });

  if (!res.ok) {
    throw new Error(`PayPal token request failed: ${res.status}`);
  }
  const json = (await res.json()) as { access_token: string };
  return json.access_token;
}

// Headers PayPal sends with each webhook; needed to verify authenticity.
export interface PayPalWebhookHeaders {
  transmissionId: string;
  transmissionTime: string;
  certUrl: string;
  authAlgo: string;
  transmissionSig: string;
}

export function extractWebhookHeaders(headers: Headers): PayPalWebhookHeaders | null {
  const transmissionId = headers.get("paypal-transmission-id");
  const transmissionTime = headers.get("paypal-transmission-time");
  const certUrl = headers.get("paypal-cert-url");
  const authAlgo = headers.get("paypal-auth-algo");
  const transmissionSig = headers.get("paypal-transmission-sig");
  if (
    !transmissionId || !transmissionTime || !certUrl ||
    !authAlgo || !transmissionSig
  ) {
    return null;
  }
  return { transmissionId, transmissionTime, certUrl, authAlgo, transmissionSig };
}

// Verify a webhook against PayPal so spoofed "payment received" calls are
// rejected. Returns true only when PayPal reports verification_status SUCCESS.
export async function verifyWebhookSignature(
  h: PayPalWebhookHeaders,
  rawBody: string
): Promise<boolean> {
  const token = await getAccessToken();
  const res = await fetch(`${BASE}/v1/notifications/verify-webhook-signature`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      transmission_id: h.transmissionId,
      transmission_time: h.transmissionTime,
      cert_url: h.certUrl,
      auth_algo: h.authAlgo,
      transmission_sig: h.transmissionSig,
      webhook_id: process.env.PAYPAL_WEBHOOK_ID,
      webhook_event: JSON.parse(rawBody),
    }),
  });

  if (!res.ok) return false;
  const json = (await res.json()) as { verification_status: string };
  return json.verification_status === "SUCCESS";
}
