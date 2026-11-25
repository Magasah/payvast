"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Link } from "@/i18n/routing";
import { ApiError, api, imageUrl } from "@/lib/api";
import { formatDate, formatSomoni, planName } from "@/lib/format";
import type { Payment, PaymentMethod, PaymentMethodInfo, Plan, Subscription } from "@/lib/types";

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
  const [copied, setCopied] = useState(false);

  const showError = useCallback(
    (err: unknown) => {
      const code = err instanceof ApiError ? err.code : "error";
      setError(te.has(code) ? te(code) : te("error"));
    },
    [te],
  );

  const load = useCallback(async () => {
    const [p, m, pay] = await Promise.all([
      api<Plan[]>("/api/plans"),
      api<PaymentMethodInfo[]>("/api/payments/methods"),
      api<Payment[]>("/api/payments"),
    ]);
    setPlans(p);
    setMethods(m);
    setPayments(pay);
    setPlanId((cur) => cur ?? p[0]?.id ?? null);
    setMethod((cur) => cur ?? m[0]?.method ?? null);
    try {
      const s = await api<Subscription>("/api/subscription");
      setSub(s);
      if (s.subscription_url) setQr(await imageUrl("/api/subscription/qr"));
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) throw err;
      setSub(null);
    }
  }, []);

  useEffect(() => {
    load().catch(showError);
  }, [load, showError]);

  useEffect(() => () => void (qr && URL.revokeObjectURL(qr)), [qr]);

  async function createPayment() {
    if (!planId || !method) return;
    setBusy(true);
    setError(null);
    try {
      await api<Payment>("/api/payments", {
        method: "POST",
        body: JSON.stringify({ plan_id: planId, method }),
        // Same key on retry/double click -> the server returns the same payment.
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
  const open = payments.filter((p) => p.status === "awaiting_receipt" || p.status === "pending_review");
  const closed = payments.filter((p) => p.status === "confirmed" || p.status === "rejected");
  const planById = (id: number) => plans.find((p) => p.id === id);

  return (
    <main className="mx-auto max-w-3xl space-y-8 px-4 py-10">
      <h1 className="text-2xl font-bold">{t("title")}</h1>

      {error && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold">{t("subscription")}</h2>
        {!sub ? (
          <p className="mt-2 text-slate-600">{t("noSubscription")}</p>
        ) : (
          <div className="mt-4 grid gap-6 sm:grid-cols-[1fr_auto]">
            <div className="space-y-2 text-sm">
              <p>
                {t("status")}:{" "}
                <span
                  className={`rounded px-2 py-0.5 font-medium ${
                    sub.status === "active" ? "bg-brand-100 text-brand-700" : "bg-slate-200 text-slate-700"
                  }`}
                >
                  {t(`statuses.${sub.status}`)}
                </span>
              </p>
              <p>
                {t("expires")}: <b>{formatDate(sub.expires_at, locale)}</b> ({t("daysLeft", { n: sub.days_left })})
              </p>
              <p>
                {tp("devices")}: {sub.device_limit}
              </p>
              {sub.subscription_url && (
                <div className="pt-2">
                  <p className="font-medium">{t("link")}</p>
                  <div className="mt-1 flex gap-2">
                    <input
                      readOnly
                      value={sub.subscription_url}
                      className="w-full rounded-lg border border-slate-300 bg-slate-50 px-2 py-1 font-mono text-xs"
                      onFocus={(e) => e.currentTarget.select()}
                    />
                    <button
                      type="button"
                      className="rounded-lg bg-brand-600 px-3 py-1 text-white hover:bg-brand-700"
                      onClick={async () => {
                        await navigator.clipboard.writeText(sub.subscription_url ?? "");
                        setCopied(true);
                        setTimeout(() => setCopied(false), 2000);
                      }}
                    >
                      {copied ? t("copied") : t("copy")}
                    </button>
                  </div>
                  <Link href="/instructions" className="mt-2 inline-block text-brand-700 underline">
                    {t("howToConnect")}
                  </Link>
                </div>
              )}
            </div>
            {qr && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={qr} alt={t("qrAlt")} className="h-44 w-44 rounded-lg border border-slate-200 bg-white p-2" />
            )}
          </div>
        )}
      </section>

      {open.map((p) => (
        <section key={p.id} className="rounded-xl border border-amber-300 bg-amber-50 p-6 text-sm">
          <h2 className="text-lg font-semibold">{t("paymentTitle")}</h2>
          <p className="mt-2">
            {t("payInstruction", {
              amount: formatSomoni(p.amount_dirams, locale),
              method: t(`methods.${p.method}`),
            })}
          </p>
          <p className="mt-1 font-mono text-base font-bold">{wallet(p.method)}</p>
          {p.status === "awaiting_receipt" ? (
            <label className="mt-4 block">
              <span className="font-medium">{t("uploadReceipt")}</span>
              <input
                type="file"
                accept={RECEIPT_TYPES.join(",")}
                disabled={busy}
                onChange={(e) => uploadReceipt(p.id, e.target.files?.[0])}
                className="mt-1 block w-full text-sm"
              />
              <span className="text-xs text-slate-500">{t("receiptHint")}</span>
            </label>
          ) : (
            <p className="mt-4 font-medium text-amber-800">{t("waitingReview")}</p>
          )}
        </section>
      ))}

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold">{sub ? t("extend") : t("buy")}</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {plans.map((plan) => (
            <button
              key={plan.id}
              type="button"
              onClick={() => setPlanId(plan.id)}
              className={`rounded-lg border p-3 text-left text-sm ${
                planId === plan.id ? "border-brand-500 bg-brand-50" : "border-slate-200"
              }`}
            >
              <b>{planName(plan, locale)}</b>
              <br />
              {formatSomoni(plan.price_dirams, locale)}
            </button>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-sm">
          {methods.map((m) => (
            <label key={m.method} className="flex items-center gap-2">
              <input
                type="radio"
                name="method"
                checked={method === m.method}
                onChange={() => setMethod(m.method)}
              />
              {t(`methods.${m.method}`)}
            </label>
          ))}
        </div>
        <button
          type="button"
          disabled={busy || !planId || !method}
          onClick={createPayment}
          className="mt-4 rounded-lg bg-brand-600 px-5 py-2 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {t("pay")}
        </button>
      </section>

      {closed.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold">{t("history")}</h2>
          <ul className="mt-3 divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white text-sm">
            {closed.map((p) => (
              <li key={p.id} className="flex flex-wrap justify-between gap-2 px-4 py-3">
                <span>
                  {formatDate(p.created_at, locale)} ·{" "}
                  {planById(p.plan_id) ? planName(planById(p.plan_id)!, locale) : ""} ·{" "}
                  {formatSomoni(p.amount_dirams, locale)}
                </span>
                <span className={p.status === "confirmed" ? "text-brand-700" : "text-red-700"}>
                  {t(`paymentStatuses.${p.status}`)}
                  {p.reject_reason ? `: ${p.reject_reason}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
