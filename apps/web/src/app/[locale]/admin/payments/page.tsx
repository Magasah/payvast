import { setRequestLocale } from "next-intl/server";

import { RequireAuth } from "@/components/RequireAuth";

import { AdminPayments } from "./AdminPayments";

export default function AdminPaymentsPage({ params: { locale } }: { params: { locale: string } }) {
  setRequestLocale(locale);
  return (
    <RequireAuth role="admin">
      <AdminPayments />
    </RequireAuth>
  );
}
