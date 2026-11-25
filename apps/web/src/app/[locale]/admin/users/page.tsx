import { setRequestLocale } from "next-intl/server";

import { AdminUsers } from "./AdminUsers";

export default function AdminUsersPage({ params: { locale } }: { params: { locale: string } }) {
  setRequestLocale(locale);
  return <AdminUsers />;
}
