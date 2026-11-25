import { setRequestLocale } from "next-intl/server";

import { AdminPayments } from "./AdminPayments";

export default function AdminPaymentsPage({ params: { locale } }: { params: { locale: string } }) {
  setRequestLocale(locale);
  return <AdminPayments />;
}
