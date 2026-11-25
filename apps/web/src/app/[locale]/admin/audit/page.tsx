import { setRequestLocale } from "next-intl/server";

import { AdminAudit } from "./AdminAudit";

export default function AdminAuditPage({ params: { locale } }: { params: { locale: string } }) {
  setRequestLocale(locale);
  return <AdminAudit />;
}
