import { getTranslations, setRequestLocale } from "next-intl/server";

import { PlanCard } from "@/components/PlanCard";
import { Link } from "@/i18n/routing";
import { fetchPlans } from "@/lib/server-api";

export default async function HomePage({ params: { locale } }: { params: { locale: string } }) {
  setRequestLocale(locale);
  const t = await getTranslations("home");
  const tp = await getTranslations("plans");
  const plans = await fetchPlans();

  return (
    <main>
      <section className="bg-gradient-to-b from-brand-50 to-slate-50">
        <div className="mx-auto max-w-5xl px-4 py-16 text-center">
          <h1 className="text-3xl font-bold sm:text-4xl">{t("title")}</h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-600">{t("subtitle")}</p>
          <Link
            href="/register"
            className="mt-8 inline-block rounded-lg bg-brand-600 px-6 py-3 font-medium text-white hover:bg-brand-700"
          >
            {t("cta")}
          </Link>
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 py-12">
        <h2 className="text-2xl font-bold">{tp("title")}</h2>
        {plans.length === 0 ? (
          <p className="mt-4 text-slate-500">{tp("empty")}</p>
        ) : (
          <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {plans.map((plan, i) => (
              <PlanCard
                key={plan.id}
                plan={plan}
                locale={locale}
                highlighted={i === 1}
                labels={{ days: tp("days"), devices: tp("devices") }}
                action={
                  <Link
                    href="/cabinet"
                    className="block rounded-lg bg-brand-600 px-4 py-2 text-center font-medium text-white hover:bg-brand-700"
                  >
                    {tp("choose")}
                  </Link>
                }
              />
            ))}
          </div>
        )}
      </section>

      <section className="mx-auto max-w-5xl px-4 pb-16">
        <h2 className="text-2xl font-bold">{t("howTitle")}</h2>
        <ol className="mt-6 grid gap-4 sm:grid-cols-3">
          {(["step1", "step2", "step3"] as const).map((key, i) => (
            <li key={key} className="rounded-xl border border-slate-200 bg-white p-5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 font-bold text-brand-700">
                {i + 1}
              </span>
              <p className="mt-3 text-slate-700">{t(key)}</p>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
