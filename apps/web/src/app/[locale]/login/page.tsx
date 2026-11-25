import { setRequestLocale } from "next-intl/server";

import { AuthForm } from "@/components/AuthForm";

export default function LoginPage({ params: { locale } }: { params: { locale: string } }) {
  setRequestLocale(locale);
  return <AuthForm mode="login" />;
}
