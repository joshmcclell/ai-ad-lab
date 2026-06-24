import { NextResponse } from "next/server";
import crypto from "crypto";
import { createAdminClient } from "@/lib/supabase/admin";

// Cal.com calendar-sync webhook — workflow W4 (docs/04).
// Each tenant configures their Cal.com webhook to point here with their
// account_id in the query string and the shared secret set in Cal.com:
//   https://<domain>/api/calcom/webhook?account_id=<uuid>
// On booking create/reschedule we upsert a calendar_events row and log it to the
// contact's activity timeline; on cancel we remove the event. The signature is
// verified before any DB write. Service-role client (writes for a named tenant).

export async function POST(request: Request) {
  const url = new URL(request.url);
  const accountId = url.searchParams.get("account_id");
  if (!accountId) {
    return NextResponse.json({ error: "missing account_id" }, { status: 400 });
  }

  const raw = await request.text();

  // Verify Cal.com's HMAC-SHA256 signature over the raw body.
  const secret = process.env.CALCOM_WEBHOOK_SECRET;
  const sig = request.headers.get("x-cal-signature-256");
  if (!secret || !sig || !verifySignature(secret, raw, sig)) {
    return NextResponse.json({ error: "signature verification failed" }, { status: 401 });
  }

  let event: CalcomEvent;
  try {
    event = JSON.parse(raw) as CalcomEvent;
  } catch {
    return NextResponse.json({ error: "invalid json" }, { status: 400 });
  }

  const supabase = createAdminClient();
  const p = event.payload ?? {};
  const uid = p.uid;
  if (!uid) return NextResponse.json({ ok: true }); // nothing to key on

  try {
    if (event.triggerEvent === "BOOKING_CANCELLED") {
      await supabase
        .from("calendar_events")
        .delete()
        .eq("account_id", accountId)
        .eq("external_id", uid);
      return NextResponse.json({ ok: true });
    }

    // CREATED or RESCHEDULED -> upsert. Link to a contact by attendee email.
    const attendeeEmail = p.attendees?.[0]?.email ?? null;
    let contactId: string | null = null;
    if (attendeeEmail) {
      const { data: contact } = await supabase
        .from("contacts")
        .select("id")
        .eq("account_id", accountId)
        .eq("email", attendeeEmail)
        .is("deleted_at", null)
        .maybeSingle();
      contactId = (contact as { id: string } | null)?.id ?? null;
    }

    await supabase.from("calendar_events").upsert(
      {
        account_id: accountId,
        external_id: uid,
        contact_id: contactId,
        title: p.title ?? "Booking",
        starts_at: p.startTime ?? null,
        ends_at: p.endTime ?? null,
      },
      { onConflict: "account_id,external_id" }
    );

    // Surface the meeting on the contact's timeline.
    if (contactId) {
      await supabase.from("activities").insert({
        account_id: accountId,
        contact_id: contactId,
        type: "meeting",
        direction: "inbound",
        subject: p.title ?? "Booking",
        body: `Booked via Cal.com for ${p.startTime ?? "an upcoming time"}.`,
        occurred_at: new Date().toISOString(),
      });
    }
  } catch (err) {
    console.error("calcom webhook handler error", err);
    return NextResponse.json({ error: "handler error" }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}

function verifySignature(secret: string, body: string, signature: string): boolean {
  const expected = crypto.createHmac("sha256", secret).update(body).digest("hex");
  const a = Buffer.from(expected);
  const b = Buffer.from(signature);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

interface CalcomEvent {
  triggerEvent: string;
  payload?: {
    uid?: string;
    title?: string;
    startTime?: string;
    endTime?: string;
    attendees?: { email?: string; name?: string }[];
  };
}
