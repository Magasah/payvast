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
    <main className="mx-auto max-w-page px-4 py-10 sm:px-6">
      <div className="max-w-prose">
        <h1 className="text-4xl font-black tracking-display">{t("title")}</h1>
        <p className="mt-3 text-lg text-ink-soft">{t("intro")}</p>
      </div>

      <nav aria-label={t("title")} className="mt-8 flex flex-wrap gap-2">
        {PLATFORMS.map((p) => (
          <a
            key={p}
            href={`#${p}`}
            className="rounded-md border border-line bg-surface px-4 py-2 text-sm font-semibold hover:border-lapis hover:text-lapis"
          >
            {t(`${p}.name`)}
          </a>
        ))}
      </nav>

      <div className="mt-10 grid gap-12 lg:grid-cols-3 lg:gap-10">
        {PLATFORMS.map((p) => (
          <section key={p} id={p} className="scroll-mt-20">
            <h2 className="border-b-2 border-lapis pb-3 text-2xl font-black tracking-display">
              {t(`${p}.name`)}
            </h2>
            <ol className="mt-5 space-y-5">
              {[
                t(`${p}.step1`),
                <>
                  {t("copyLink")}{" "}
                  <Link href="/cabinet" className="font-semibold text-lapis underline underline-offset-4">
                    {t("cabinetLink")}
                  </Link>
                  .
                </>,
                t(`${p}.step3`),
                t(`${p}.step4`),
              ].map((step, i) => (
                <li key={i} className="grid grid-cols-[2rem_1fr] gap-3">
                  <span className="tabular font-display text-xl font-black text-lapis">{i + 1}</span>
                  <p className="text-ink">{step}</p>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>

      <p className="mt-12 max-w-prose border-l-4 border-saffron bg-saffron-tint px-4 py-3 text-sm text-[#6b430a]">
        {t("devicesNote")}
      </p>
    </main>
  );
}
