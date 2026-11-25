import { getTranslations, setRequestLocale } from "next-intl/server";

import { Link } from "@/i18n/routing";

const PLATFORMS = ["android", "ios", "windows"] as const;

export default async function InstructionsPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);
  const t = await getTranslations("instructions");

  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <p className="mt-2 text-slate-600">{t("intro")}</p>

      <nav className="mt-6 flex gap-2 text-sm">
        {PLATFORMS.map((p) => (
          <a
            key={p}
            href={`#${p}`}
            className="rounded-full border border-slate-300 bg-white px-4 py-1.5 hover:border-brand-500"
          >
            {t(`${p}.name`)}
          </a>
        ))}
      </nav>

      {PLATFORMS.map((p) => (
        <section
          key={p}
          id={p}
          className="mt-8 scroll-mt-6 rounded-xl border border-slate-200 bg-white p-6"
        >
          <h2 className="text-xl font-semibold">{t(`${p}.name`)}</h2>
          <ol className="mt-4 list-decimal space-y-2 pl-5 text-slate-700">
            <li>{t(`${p}.step1`)}</li>
            <li>
              {t("copyLink")}{" "}
              <Link href="/cabinet" className="text-brand-700 underline">
                {t("cabinetLink")}
              </Link>
              .
            </li>
            <li>{t(`${p}.step3`)}</li>
            <li>{t(`${p}.step4`)}</li>
          </ol>
        </section>
      ))}

      <p className="mt-8 rounded-lg bg-brand-50 p-4 text-sm text-brand-900">{t("devicesNote")}</p>
    </main>
  );
}
