import Link from "next/link";
import { contactName, formatDate } from "@/lib/format";
import { loadContacts } from "@/lib/data";

export default async function ContactsPage() {
  const contacts = await loadContacts();

  return (
    <div>
      <h1 className="text-2xl font-semibold">Contacts</h1>

      <div className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-surface text-left text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Company</th>
              <th className="px-4 py-2 font-medium">Kind</th>
              <th className="px-4 py-2 font-medium">Source</th>
              <th className="px-4 py-2 font-medium">Added</th>
            </tr>
          </thead>
          <tbody>
            {contacts.length === 0 ? (
              <tr>
                <td className="px-4 py-3 text-slate-400" colSpan={5}>
                  No contacts yet.
                </td>
              </tr>
            ) : (
              contacts.map((c) => (
                <tr key={c.id} className="border-t border-slate-100 hover:bg-surface">
                  <td className="px-4 py-2">
                    <Link href={`/contacts/${c.id}`} className="font-medium text-brand">
                      {contactName(c)}
                    </Link>
                  </td>
                  <td className="px-4 py-2">{c.company ?? "—"}</td>
                  <td className="px-4 py-2 capitalize">{c.kind}</td>
                  <td className="px-4 py-2">{c.source ?? "—"}</td>
                  <td className="px-4 py-2">{formatDate(c.created_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
