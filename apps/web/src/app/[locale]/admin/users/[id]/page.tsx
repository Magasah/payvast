import { setRequestLocale } from "next-intl/server";

import { AdminUserDetail } from "./AdminUserDetail";

export default function AdminUserPage({ params }: { params: { locale: string; id: string } }) {
  setRequestLocale(params.locale);
  return <AdminUserDetail userId={params.id} />;
}
