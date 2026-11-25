"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { CopyButton } from "@/components/CopyButton";
import { Pass } from "@/components/Pass";
import { TariffRow } from "@/components/TariffRow";
import { Badge, Button, Notice, Panel, cx } from "@/components/ui";
import { Link } from "@/i18n/routing";
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

const MAX_RECEIPT_BYTES = 5 * 1024 * 1024;
const RECEIPT_TYPES = ["image/jpeg", "image/png", "image/webp"];


function newIdempotencyKey(): string {
  return crypto.randomUUID().replaceAll("-", "");
}

export function Cabinet() {
  const t = useTranslations("cabinet");
  const tp = useTranslations("plans");
  const te = useTranslations("errors");
  const locale = useLocale();

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
      await api<Payment>("/api/payments", {
        method: "POST",
        body: JSON.stringify({ plan_id: planId, method }),
        // Same key on retry or double tap: the server returns the same payment.
        headers: { "Idempotency-Key": idemKey },
      });
      setIdemKey(newIdempotencyKey());
      await load();
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  async function uploadReceipt(paymentId: string, file: File | undefined) {
    setError(null);
    if (!file) return;
    if (!RECEIPT_TYPES.includes(file.type)) return setError(te("invalid_image"));
    if (file.size > MAX_RECEIPT_BYTES) return setError(te("file_too_large"));
    const body = new FormData();
    body.append("file", file);
    setBusy(true);
    try {
      await api<Payment>(`/api/payments/${paymentId}/receipt`, { method: "POST", body });
      await load();
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  const wallet = (m: PaymentMethod) => methods.find((x) => x.method === m)?.wallet ?? "";
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

      {open.map((p) => (
        <Panel key={p.id} className="border-l-4 border-l-saffron">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-extrabold">{t("paymentTitle")}</h2>
            <Badge tone={PAYMENT_TONE[p.status]}>{t(`paymentStatuses.${p.status}`)}</Badge>
          </div>
          {p.status === "awaiting_receipt" ? (
            <ol className="mt-5 grid gap-6 md:grid-cols-2">
              <li>
                <p className="text-sm font-semibold text-ink-soft">{t("step1")}</p>
                <p className="tabular mt-2 font-display text-3xl font-black text-lapis-deep">
                  {formatSomoni(p.amount_dirams, locale)}
                </p>
                <p className="mt-1 text-sm text-ink-soft">
                  {t("toWallet", { method: t(`methods.${p.method}`) })}
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <span className="tabular text-lg font-semibold">{wallet(p.method)}</span>
                  <CopyButton value={wallet(p.method)} />
                </div>
              </li>
              <li>
                <p className="text-sm font-semibold text-ink-soft">{t("step2")}</p>
                <label
                  className={cx(
                    "mt-2 flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed border-line bg-paper px-4 py-6 text-center transition-colors hover:border-lapis",
                    busy && "pointer-events-none opacity-60",
                  )}
                >
                  <span className="font-semibold text-lapis">{t("chooseFile")}</span>
                  <span className="mt-1 text-xs text-ink-soft">{t("receiptHint")}</span>
                  <input
                    type="file"
                    accept={RECEIPT_TYPES.join(",")}
                    disabled={busy}
                    onChange={(e) => uploadReceipt(p.id, e.target.files?.[0])}
                    className="sr-only"
                  />
                </label>
              </li>
            </ol>
          ) : (
            <p className="mt-3 text-ink-soft">
              {t("waitingReview", { amount: formatSomoni(p.amount_dirams, locale) })}
            </p>
          )}
        </Panel>
      ))}

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
          <div className="inline-flex rounded-md border border-line bg-surface p-1">
            {methods.map((m) => (
              <label
                key={m.method}
                className={cx(
                  "cursor-pointer rounded-[9px] px-4 py-2 text-sm font-semibold transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-lapis/40",
                  method === m.method ? "bg-lapis text-white" : "text-ink-soft hover:text-ink",
                )}
              >
                <input
                  type="radio"
                  name="method"
                  className="sr-only"
                  checked={method === m.method}
                  onChange={() => setMethod(m.method)}
                />
                {t(`methods.${m.method}`)}
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
