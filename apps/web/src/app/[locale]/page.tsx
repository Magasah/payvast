import { useTranslations } from "next-intl";
import { setRequestLocale } from "next-intl/server";

export default function HomePage({ params: { locale } }: { params: { locale: string } }) {
  setRequestLocale(locale);
  const t = useTranslations("home");
  return (
    <main className="mx-auto max-w-5xl px-4 py-16">
      <h1 className="text-3xl font-bold">{t("title")}</h1>
      <p className="mt-2 text-slate-600">{t("subtitle")}</p>
    </main>
  );
}
