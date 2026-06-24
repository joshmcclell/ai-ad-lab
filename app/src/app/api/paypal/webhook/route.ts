import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { extractWebhookHeaders, verifyWebhookSignature } from "@/lib/paypal";

// PayPal webhook receiver — workflows W5/W6 (docs/04, docs/07).
// Verifies the signature, then keeps each tenant's subscription/payment status
// in sync. Uses the service-role client because it writes across tenants.
//
// Subscribe this URL in the PayPal webhook config to:
//   BILLING.SUBSCRIPTION.ACTIVATED / CANCELLED / SUSPENDED
//   BILLING.SUBSCRIPTION.PAYMENT.FAILED
//   PAYMENT.SALE.COMPLETED

export async function POST(request: Request) {
  const raw = await request.text();

  const headers = extractWebhookHeaders(request.headers);
  if (!headers) {
    return NextResponse.json({ error: "missing signature headers" }, { status: 400 });
  }

  // Reject spoofed calls before touching any data.
  const verified = await verifyWebhookSignature(headers, raw);
  if (!verified) {
    return NextResponse.json({ error: "signature verification failed" }, { status: 401 });
  }

  let event: PayPalEvent;
  try {
    event = JSON.parse(raw) as PayPalEvent;
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const supabase = createAdminClient();

  try {
    switch (event.event_type) {
      case "BILLING.SUBSCRIPTION.ACTIVATED":
        await onSubscriptionActivated(supabase, event);
        break;
      case "BILLING.SUBSCRIPTION.SUSPENDED":
        await onSubscriptionStatus(supabase, event, "suspended", "paused");
        break;
      case "BILLING.SUBSCRIPTION.CANCELLED":
        await onSubscriptionStatus(supabase, event, "cancelled", "cancelled");
        break;
      case "BILLING.SUBSCRIPTION.PAYMENT.FAILED":
        await onSubscriptionStatus(supabase, event, "past_due", "past_due");
        break;
      case "PAYMENT.SALE.COMPLETED":
        await onPaymentCompleted(supabase, event);
        break;
      default:
        // Unhandled event — acknowledge so PayPal stops retrying.
        break;
    }
  } catch (err) {
    console.error("paypal webhook handler error", err);
    return NextResponse.json({ error: "handler error" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}

type SupabaseAdmin = ReturnType<typeof createAdminClient>;

interface PayPalEvent {
  event_type: string;
  resource: {
    id?: string;
    billing_agreement_id?: string; // present on PAYMENT.SALE.COMPLETED for subs
    custom_id?: string; // we set this to account_id at subscribe time
    status?: string;
    amount?: { total?: string; value?: string; currency_code?: string };
    billing_info?: { next_billing_time?: string };
    subscriber?: {
      email_address?: string;
      name?: { given_name?: string; surname?: string };
    };
  };
}

// Ensure an account exists for an activating subscription. If the operator
// pre-created the tenant, custom_id carries its account_id and we use it.
// Otherwise (pure self-serve signup) we provision a fresh tenant from the
// PayPal subscriber details — realising the "payment auto-provisions" flow
// (docs/09). Returns the account_id, or null if we can't determine one.
async function ensureAccountId(
  supabase: SupabaseAdmin,
  event: PayPalEvent
): Promise<string | null> {
  const customAccountId = event.resource.custom_id;
  if (customAccountId) {
    const { data } = await supabase
      .from("accounts")
      .select("id")
      .eq("id", customAccountId)
      .maybeSingle();
    if (data) return (data as { id: string }).id;
  }

  const sub = event.resource.subscriber;
  const email = sub?.email_address;
  if (!email) return customAccountId ?? null;

  const given = sub?.name?.given_name ?? "";
  const surname = sub?.name?.surname ?? "";
  const fullName = [given, surname].filter(Boolean).join(" ").trim() || null;
  const accountName = fullName ? `${fullName}'s workspace` : email;

  // Reuse an existing tenant if this owner email is already known, else create.
  const { data: existingUser } = await supabase
    .from("users")
    .select("account_id")
    .eq("email", email)
    .maybeSingle();
  if (existingUser && (existingUser as { account_id: string | null }).account_id) {
    return (existingUser as { account_id: string }).account_id;
  }

  const { data: newId, error } = await supabase.rpc("provision_account", {
    p_name: accountName,
    p_owner_email: email,
    p_owner_name: fullName,
  });
  if (error) {
    console.error("provision_account failed", error);
    return customAccountId ?? null;
  }
  return newId as string;
}

async function onSubscriptionActivated(
  supabase: SupabaseAdmin,
  event: PayPalEvent
) {
  const paypalSubId = event.resource.id;
  if (!paypalSubId) return;

  const accountId = await ensureAccountId(supabase, event);

  await supabase.from("subscriptions").upsert(
    {
      paypal_subscription_id: paypalSubId,
      account_id: accountId,
      status: "active",
      next_billing_at: event.resource.billing_info?.next_billing_time ?? null,
      updated_at: new Date().toISOString(),
    },
    { onConflict: "paypal_subscription_id" }
  );

  if (accountId) {
    await supabase.from("accounts").update({ status: "active" }).eq("id", accountId);
  }
}

// Resolve our subscription row + account from a PayPal subscription id.
async function findSubscription(supabase: SupabaseAdmin, paypalSubId: string) {
  const { data } = await supabase
    .from("subscriptions")
    .select("id, account_id")
    .eq("paypal_subscription_id", paypalSubId)
    .maybeSingle();
  return data as { id: string; account_id: string } | null;
}

async function onSubscriptionStatus(
  supabase: SupabaseAdmin,
  event: PayPalEvent,
  subStatus: string,
  accountStatus: string
) {
  const paypalSubId = event.resource.id;
  const customAccountId = event.resource.custom_id;
  if (!paypalSubId) return;

  // On ACTIVATED the row may not exist yet (subscription created client-side),
  // so upsert by paypal_subscription_id and attach the account via custom_id.
  await supabase
    .from("subscriptions")
    .upsert(
      {
        paypal_subscription_id: paypalSubId,
        account_id: customAccountId,
        status: subStatus,
        next_billing_at: event.resource.billing_info?.next_billing_time ?? null,
        updated_at: new Date().toISOString(),
      },
      { onConflict: "paypal_subscription_id" }
    );

  const accountId =
    customAccountId ?? (await findSubscription(supabase, paypalSubId))?.account_id;
  if (accountId) {
    await supabase
      .from("accounts")
      .update({ status: accountStatus })
      .eq("id", accountId);
  }
}

async function onPaymentCompleted(supabase: SupabaseAdmin, event: PayPalEvent) {
  const paypalSubId = event.resource.billing_agreement_id;
  const txnId = event.resource.id;
  const amount = event.resource.amount;
  const valueStr = amount?.total ?? amount?.value ?? "0";
  const pennies = Math.round(parseFloat(valueStr) * 100);
  const currency = amount?.currency_code ?? "GBP";
  if (!paypalSubId || !txnId) return;

  const sub = await findSubscription(supabase, paypalSubId);
  if (!sub) return;

  // Ledger row (idempotent on the PayPal txn id).
  await supabase.from("payments").upsert(
    {
      account_id: sub.account_id,
      subscription_id: sub.id,
      paypal_txn_id: txnId,
      amount_pennies: pennies,
      currency,
      status: "completed",
      paid_at: new Date().toISOString(),
      raw: event as unknown as Record<string, unknown>,
    },
    { onConflict: "paypal_txn_id" }
  );

  await supabase
    .from("subscriptions")
    .update({
      status: "active",
      last_payment_at: new Date().toISOString(),
      last_payment_pennies: pennies,
      updated_at: new Date().toISOString(),
    })
    .eq("id", sub.id);

  // A successful payment clears any past-due flag.
  await supabase.from("accounts").update({ status: "active" }).eq("id", sub.account_id);
}
