import { redirect } from "next/navigation";

export default function Home() {
  // Middleware handles auth; land users on the dashboard.
  redirect("/dashboard");
}
