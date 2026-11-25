"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { CopyButton } from "@/components/CopyButton";
import { Pass } from "@/components/Pass";
import { TariffRow } from "@/components/TariffRow";
import { Badge, Button, ButtonLink, Icon, Notice, Panel, cx, type IconName } from "@/components/ui";
import { Link, useRouter } from "@/i18n/routing";
import { ApiError, api, imageUrl } from "@/lib/api";
import { formatDate, formatSomoni, planName } from "@/lib/format";
import { PAYMENT_TONE, SUB_TONE } from "@/lib/status";
import type {
  Payment,
  PaymentMethod,
  PaymentMethodInfo,
  Plan,
  Subscription,
} from "@/lib/types";

const METHOD_ICON: Record<PaymentMethod, IconName> = {
  alif: "phone",
  dushanbe_city: "wallet",
  card: "card",
};

function newIdempotencyKey(): string {
  return crypto.randomUUID().replaceAll("-", "");
}

export function Cabinet() {
  const t = useTranslations("cabinet");
  const tp = useTranslations("plans");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();

  const [loaded, setLoaded] = useState(false);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [qr, setQr] = useState<string | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [methods, setMethods] = useState<PaymentMethodInfo[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [planId, setPlanId] = useState<number | null>(null);
  const [method, setMethod] = useState<PaymentMethod | null>(null);
  const [idemKey, setIdemKey] = useState(newIdempotencyKey);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const showError = useCallback(
    (err: unknown) => {
      const code = err instanceof ApiError ? err.code : "error";
      setError(te.has(code) ? te(code) : te("error"));
    },
    [te],
  );

  const load = useCallback(async () => {
    const [p, m, pay, s] = await Promise.all([
      api<Plan[]>("/api/plans"),
      api<PaymentMethodInfo[]>("/api/payments/methods"),
      api<Payment[]>("/api/payments"),
      api<Subscription>("/api/subscription").catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }),
    ]);
    setPlans(p);
    setMethods(m);
    setPayments(pay);
    setSub(s);
    setPlanId((cur) => cur ?? p[0]?.id ?? null);
    setMethod((cur) => cur ?? m[0]?.method ?? null);
    setLoaded(true);
    if (s?.subscription_url) {
      const url = await imageUrl("/api/subscription/qr");
      setQr((old) => {
        if (old) URL.revokeObjectURL(old);
        return url;
      });
    }
  }, []);

  useEffect(() => {
    load().catch(showError);
  }, [load, showError]);

  async function createPayment() {
    if (!planId || !method) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api<Payment>("/api/payments", {
        method: "POST",
        body: JSON.stringify({ plan_id: planId, method }),
        // Same key on retry or double tap: the server returns the same payment.
        headers: { "Idempotency-Key": idemKey },
      });
      setIdemKey(newIdempotencyKey());
      router.push(`/cabinet/pay/${created.id}`);
    } catch (err) {
      showError(err);
      setBusy(false);
    }
  }

  const open = payments.filter(
    (p) => p.status === "awaiting_receipt" || p.status === "pending_review",
  );
  const closed = payments.filter((p) => p.status === "confirmed" || p.status === "rejected");
  const planById = (id: number) => plans.find((p) => p.id === id);
  const labels = {
    perMonth: tp("perMonth"),
    devices: (n: number) => tp("devicesN", { n }),
    days: (n: number) => tp("daysN", { n }),
  };

  if (!loaded && !error) {
    return (
      <div className="mx-auto max-w-page px-4 py-12 sm:px-6" aria-busy="true">
        <div className="h-56 animate-pulse rounded-pass bg-lapis-tint" />
      </div>
    );
  }

  return (
    <main className="mx-auto max-w-page space-y-10 px-4 py-10 sm:px-6">
      <h1 className="text-3xl font-black tracking-display">{t("title")}</h1>

      {error && <Notice tone="error">{error}</Notice>}

      {sub ? (
        <Pass
          big={sub.days_left}
          bigLabel={t("daysLeft", { n: sub.days_left })}
          badge={<Badge tone={SUB_TONE[sub.status]}>{t(`statuses.${sub.status}`)}</Badge>}
          lines={[
            t("until", { date: formatDate(sub.expires_at, locale) }),
            tp("devicesN", { n: sub.device_limit }),
          ]}
          aside={
            qr && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={qr}
                alt={t("qrAlt")}
                width={176}
                height={176}
                className="h-40 w-40 rounded-md bg-white p-2 sm:h-44 sm:w-44"
              />
            )
          }
          footer={
            sub.subscription_url && (
              <div>
                <p className="mb-2 text-sm text-white/75">{t("link")}</p>
                <div className="flex gap-2">
                  <input
                    readOnly
                    value={sub.subscription_url}
                    aria-label={t("link")}
                    onFocus={(e) => e.currentTarget.select()}
                    className="h-9 min-w-0 flex-1 rounded-md bg-white/10 px-3 text-sm text-white outline-none ring-white/40 focus:ring-2"
                  />
                  <CopyButton value={sub.subscription_url} tone="inverse" />
                </div>
                <Link
                  href="/instructions"
                  className="mt-3 inline-block text-sm font-semibold text-white underline underline-offset-4"
                >
                  {t("howToConnect")}
                </Link>
              </div>
            )
          }
        />
      ) : (
        <Panel className="border-dashed">
          <h2 className="text-xl font-extrabold">{t("noSubscriptionTitle")}</h2>
          <p className="mt-1 text-ink-soft">{t("noSubscription")}</p>
        </Panel>
      )}

      {open.map((p) => {
        const plan = planById(p.plan_id);
        return (
          <Panel key={p.id} className="border-l-4 border-l-saffron">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-lg font-extrabold">
                  {plan ? planName(plan, locale) : t("paymentTitle")} ·{" "}
                  {formatSomoni(p.amount_dirams, locale)}
                </h2>
                <p className="mt-0.5 text-sm text-ink-soft">
                  {t(`methods.${p.method}`)} · {formatDate(p.created_at, locale)}
                </p>
              </div>
              <Badge tone={PAYMENT_TONE[p.status]}>{t(`paymentStatuses.${p.status}`)}</Badge>
            </div>
            <ButtonLink
              href={`/cabinet/pay/${p.id}`}
              tone={p.status === "awaiting_receipt" ? "primary" : "quiet"}
              className="mt-4 w-full sm:w-auto"
            >
              {p.status === "awaiting_receipt" ? t("continuePay") : t("viewPayment")}
              <Icon name="forward" size={18} />
            </ButtonLink>
          </Panel>
        );
      })}

      <section>
        <h2 className="text-2xl font-black tracking-display">{sub ? t("extend") : t("buy")}</h2>
        <fieldset className="mt-5 divide-y divide-line overflow-hidden rounded-lg border border-line bg-surface">
          <legend className="sr-only">{tp("title")}</legend>
          {plans.map((plan) => (
            <label key={plan.id} className="block cursor-pointer has-[:focus-visible]:ring-4 has-[:focus-visible]:ring-lapis/20">
              <input
                type="radio"
                name="plan"
                className="sr-only"
                checked={planId === plan.id}
                onChange={() => setPlanId(plan.id)}
              />
              <TariffRow
                plan={plan}
                locale={locale}
                labels={labels}
                selected={planId === plan.id}
                compactAction
                action={
                  <span
                    aria-hidden
                    className={cx(
                      "flex h-6 w-6 items-center justify-center rounded-full border-2",
                      planId === plan.id ? "border-lapis" : "border-line",
                    )}
                  >
                    {planId === plan.id && <span className="h-3 w-3 rounded-full bg-lapis" />}
                  </span>
                }
              />
            </label>
          ))}
        </fieldset>

        <fieldset className="mt-5">
          <legend className="mb-2 text-sm font-semibold text-ink-soft">{t("method")}</legend>
          <div className="grid gap-2 sm:grid-cols-3">
            {methods.map((m) => (
              <label
                key={m.method}
                className={cx(
                  "flex min-h-14 cursor-pointer items-center gap-3 rounded-md border px-4 py-3 text-sm font-semibold transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-lapis/40",
                  method === m.method
                    ? "border-lapis bg-lapis-tint text-lapis-deep"
                    : "border-line bg-surface text-ink hover:border-lapis",
                )}
              >
                <input
                  type="radio"
                  name="method"
                  className="sr-only"
                  checked={method === m.method}
                  onChange={() => setMethod(m.method)}
                />
                <Icon name={METHOD_ICON[m.method]} />
                <span className="min-w-0">
                  {t(`methods.${m.method}`)}
                  <span className="block text-xs font-normal text-ink-soft">
                    {t(`methodHints.${m.method}`)}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <Button
          size="lg"
          className="mt-6 w-full sm:w-auto"
          disabled={busy || !planId || !method}
          onClick={createPayment}
        >
          {t("pay")}
          <Icon name="forward" size={20} />
        </Button>
      </section>

      {closed.length > 0 && (
        <section>
          <h2 className="text-2xl font-black tracking-display">{t("history")}</h2>
          <ul className="mt-5 divide-y divide-line rounded-lg border border-line bg-surface">
            {closed.map((p) => {
              const plan = planById(p.plan_id);
              return (
                <li key={p.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
                  <div>
                    <p className="font-semibold">
                      {plan ? planName(plan, locale) : ""}, {formatSomoni(p.amount_dirams, locale)}
                    </p>
                    <p className="text-sm text-ink-soft">
                      {formatDate(p.created_at, locale)}
                      {p.reject_reason ? `. ${p.reject_reason}` : ""}
                    </p>
                  </div>
                  <Badge tone={PAYMENT_TONE[p.status]}>{t(`paymentStatuses.${p.status}`)}</Badge>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </main>
  );
}
