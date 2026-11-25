import { getTranslations, setRequestLocale } from "next-intl/server";

import { Pass } from "@/components/Pass";
import { TariffRow } from "@/components/TariffRow";
import { ButtonLink } from "@/components/ui";
import { fetchPlans } from "@/lib/server-api";

export default async function HomePage({ params: { locale } }: { params: { locale: string } }) {
  setRequestLocale(locale);
  const t = await getTranslations("home");
  const tp = await getTranslations("plans");
  const plans = await fetchPlans();

  const labels = {
    perMonth: tp("perMonth"),
    devices: (n: number) => tp("devicesN", { n }),
    days: (n: number) => tp("daysN", { n }),
  };

  return (
    <main>
      <section className="mx-auto grid max-w-page grid-cols-[minmax(0,1fr)] items-center gap-10 px-4 pb-14 pt-10 sm:px-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-16 lg:pb-20 lg:pt-16">
        <div className="min-w-0 max-w-prose">
          <h1 className="hyphens-auto break-words text-[2rem] font-black leading-[1.08] tracking-display min-[360px]:text-4xl sm:text-5xl">
            {t("title")}
          </h1>
          <p className="mt-5 text-lg text-ink-soft">{t("subtitle")}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink href="/register" size="lg">
              {t("cta")}
            </ButtonLink>
            <ButtonLink href="/instructions" size="lg" tone="quiet">
              {t("ctaSecondary")}
            </ButtonLink>
          </div>
          <p className="mt-6 text-sm text-ink-soft">{t("payWith")}</p>
        </div>
        <Pass
          animate
          className="lg:rotate-[1.5deg]"
          big="30"
          bigLabel={t("passDays")}
          lines={[t("passLine1"), t("passLine2")]}
        />
      </section>

      <section id="plans" className="mx-auto max-w-page scroll-mt-20 px-4 sm:px-6">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <h2 className="text-3xl font-black tracking-display">{tp("title")}</h2>
          <p className="text-sm text-ink-soft">{tp("note")}</p>
        </div>
        {plans.length === 0 ? (
          <p className="mt-6 text-ink-soft">{tp("empty")}</p>
        ) : (
          <div className="mt-6 divide-y divide-line overflow-hidden rounded-lg border border-line bg-surface">
            {plans.map((plan) => (
              <TariffRow
                key={plan.id}
                plan={plan}
                locale={locale}
                labels={labels}
                action={
                  <ButtonLink href="/cabinet" tone="quiet" className="w-full sm:w-auto">
                    {tp("choose")}
                  </ButtonLink>
                }
              />
            ))}
          </div>
        )}
      </section>

      <section className="mx-auto max-w-page px-4 pt-16 sm:px-6">
        <h2 className="text-3xl font-black tracking-display">{t("howTitle")}</h2>
        <ol className="mt-8 grid gap-8 sm:grid-cols-3 sm:gap-10">
          {(["step1", "step2", "step3"] as const).map((key, i) => (
            <li key={key} className="border-t-2 border-lapis pt-4">
              <span className="tabular font-display text-3xl font-black text-lapis">{i + 1}</span>
              <h3 className="mt-2 text-lg font-extrabold">{t(`${key}Title`)}</h3>
              <p className="mt-1 text-ink-soft">{t(key)}</p>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
