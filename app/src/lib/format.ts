// Money is stored as integer pennies in the DB (see db/schema.sql).
export function formatMoney(pennies: number, currency = "GBP"): string {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency,
  }).format((pennies ?? 0) / 100);
}

export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function contactName(c: {
  first_name: string | null;
  last_name: string | null;
  email: string | null;
}): string {
  const name = [c.first_name, c.last_name].filter(Boolean).join(" ").trim();
  return name || c.email || "Unnamed contact";
}
