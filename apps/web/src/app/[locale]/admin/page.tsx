import { redirect } from "@/i18n/routing";

export default function AdminIndex({ params: { locale } }: { params: { locale: string } }) {
  redirect({ href: "/admin/payments", locale });
}
