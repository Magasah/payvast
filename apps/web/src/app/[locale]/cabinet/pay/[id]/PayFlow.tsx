"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useRef, useState } from "react";

import { CopyButton } from "@/components/CopyButton";
import { Badge, Button, ButtonLink, Icon, Notice, Panel, buttonClass, cx } from "@/components/ui";
import { Link } from "@/i18n/routing";
import { ApiError, api } from "@/lib/api";
import { formatSomoni, planName } from "@/lib/format";
import { PAYMENT_TONE } from "@/lib/status";
import type { Payment, PaymentMethodInfo, Plan } from "@/lib/types";

const MAX_RECEIPT_BYTES = 5 * 1024 * 1024;
const RECEIPT_TYPES = ["image/jpeg", "image/png", "image/webp"];
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const POLL_MS = 15_000;

/** Plain number for banking apps: 5000 dirams -> "50", 5050 -> "50.50". */
function amountForBank(dirams: number): string {
  return (dirams / 100).toFixed(dirams % 100 === 0 ? 0 : 2);
}

export function PayFlow({ paymentId }: { paymentId: string }) {
  const t = useTranslations("pay");
  const tc = useTranslations("cabinet");
  const te = useTranslations("errors");
  const locale = useLocale();

  const [payment, setPayment] = useState<Payment | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [info, setInfo] = useState<PaymentMethodInfo | null>(null);
  const [missing, setMissing] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [replacing, setReplacing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const showError = useCallback(
    (err: unknown) => {
      const code = err instanceof ApiError ? err.code : "error";
      setError(te.has(code) ? te(code) : te("error"));
    },
    [te],
  );

  const load = useCallback(async () => {
    if (!UUID_RE.test(paymentId)) {
      setMissing(true);
      return;
    }
    try {
      const [p, plans, methods] = await Promise.all([
        api<Payment>(`/api/payments/${paymentId}`),
        api<Plan[]>("/api/plans"),
        api<PaymentMethodInfo[]>("/api/payments/methods"),
      ]);
      setPayment(p);
      setPlan(plans.find((x) => x.id === p.plan_id) ?? null);
      setInfo(methods.find((m) => m.method === p.method) ?? null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setMissing(true);
      else showError(err);
    }
  }, [paymentId, showError]);

  useEffect(() => {
    void load();
  }, [load]);

  // While the receipt is being reviewed, check for the admin's answer now and then.
  useEffect(() => {
    if (payment?.status !== "pending_review") return;
    const id = setInterval(() => {
      if (document.visibilityState === "visible") void load();
    }, POLL_MS);
    return () => clearInterval(id);
  }, [payment?.status, load]);

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function pick(f: File | undefined) {
    setError(null);
    if (!f) return;
    if (!RECEIPT_TYPES.includes(f.type)) return setError(te("invalid_image"));
    if (f.size > MAX_RECEIPT_BYTES) return setError(te("file_too_large"));
    setFile(f);
  }

  async function send() {
    if (!file || !payment) return;
    const body = new FormData();
    body.append("file", file);
    setBusy(true);
    setError(null);
    try {
      setPayment(
        await api<Payment>(`/api/payments/${payment.id}/receipt`, { method: "POST", body }),
      );
      setFile(null);
      setPreview(null);
      setReplacing(false);
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  if (missing) {
    return (
      <main className="mx-auto max-w-prose px-4 py-12 sm:px-6">
        <Notice tone="error">{t("notFound")}</Notice>
        <ButtonLink href="/cabinet" tone="quiet" className="mt-6">
          <Icon name="back" size={18} />
          {t("backToCabinet")}
        </ButtonLink>
      </main>
    );
  }

  if (!payment) {
    return (
      <div className="mx-auto max-w-prose px-4 py-12 sm:px-6" aria-busy="true">
        {error ? <Notice tone="error">{error}</Notice> : (
          <div className="h-72 animate-pulse rounded-lg bg-lapis-tint" />
        )}
      </div>
    );
  }

  const amount = formatSomoni(payment.amount_dirams, locale);
  const isCard = info?.account_kind === "card";
  const canUpload =
    payment.status === "awaiting_receipt" || (payment.status === "pending_review" && replacing);

  return (
    <main className="mx-auto max-w-prose space-y-6 px-4 py-8 sm:px-6 sm:py-10">
      <Link
        href="/cabinet"
        className="inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-ink-soft hover:text-lapis"
      >
        <Icon name="back" size={18} />
        {t("backToCabinet")}
      </Link>

      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black tracking-display sm:text-3xl">{t("title")}</h1>
          <p className="mt-1 text-ink-soft">
            {plan ? planName(plan, locale) : ""} · {tc(`methods.${payment.method}`)}
          </p>
        </div>
        <Badge tone={PAYMENT_TONE[payment.status]}>
          {tc(`paymentStatuses.${payment.status}`)}
        </Badge>
      </header>

      {error && <Notice tone="error">{error}</Notice>}

      {payment.status === "confirmed" && (
        <Panel className="border-l-4 border-l-pistachio">
          <div className="flex items-start gap-3">
            <Icon name="check" className="mt-0.5 shrink-0 text-pistachio" size={24} />
            <div>
              <h2 className="text-lg font-extrabold">{t("confirmedTitle")}</h2>
              <p className="mt-1 text-ink-soft">{t("confirmedText")}</p>
              <ButtonLink href="/cabinet" className="mt-4">
                {t("openSubscription")}
              </ButtonLink>
            </div>
          </div>
        </Panel>
      )}

      {payment.status === "rejected" && (
        <Panel className="border-l-4 border-l-pomegranate">
          <div className="flex items-start gap-3">
            <Icon name="alert" className="mt-0.5 shrink-0 text-pomegranate" size={24} />
            <div className="min-w-0">
              <h2 className="text-lg font-extrabold">{t("rejectedTitle")}</h2>
              {payment.reject_reason && (
                <p className="mt-1 break-words text-ink">
                  <span className="text-ink-soft">{t("reason")}: </span>
                  {payment.reject_reason}
                </p>
              )}
              <ButtonLink href="/cabinet" className="mt-4">
                {t("payAgain")}
              </ButtonLink>
            </div>
          </div>
        </Panel>
      )}

      {payment.status === "pending_review" && !replacing && (
        <Panel className="border-l-4 border-l-lapis">
          <div className="flex items-start gap-3">
            <Icon name="clock" className="mt-0.5 shrink-0 text-lapis" size={24} />
            <div>
              <h2 className="text-lg font-extrabold">{t("pendingTitle")}</h2>
              <p className="mt-1 text-ink-soft">{t("pendingText", { amount })}</p>
              <Button tone="quiet" size="sm" className="mt-4" onClick={() => setReplacing(true)}>
                <Icon name="image" size={16} />
                {t("replaceReceipt")}
              </Button>
            </div>
          </div>
        </Panel>
      )}

      {payment.status === "awaiting_receipt" && (
        <>
          <ol className="grid grid-cols-3 gap-2 text-center text-xs font-semibold text-ink-soft sm:text-sm">
            {(["step1", "step2", "step3"] as const).map((key, i) => (
              <li key={key} className="flex flex-col items-center gap-1.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-lapis text-sm font-black text-white">
                  {i + 1}
                </span>
                <span className="leading-snug">{t(key)}</span>
              </li>
            ))}
          </ol>

          <Panel>
            <p className="text-sm font-semibold text-ink-soft">{t("amountLabel")}</p>
            <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
              <p className="tabular font-display text-4xl font-black tracking-display text-lapis-deep">
                {amount}
              </p>
              <CopyButton value={amountForBank(payment.amount_dirams)} label={t("copyAmount")} />
            </div>
            <p className="mt-3 flex items-start gap-2 text-sm text-ink-soft">
              <Icon name="info" size={18} className="mt-px shrink-0 text-lapis" />
              {t("exactAmount")}
            </p>
            {info && info.fee_percent > 0 && (
              <p className="mt-2 flex items-start gap-2 text-sm text-saffron-ink">
                <Icon name="alert" size={18} className="mt-px shrink-0" />
                {t("fee", { percent: info.fee_percent })}
              </p>
            )}
          </Panel>

          {info ? (
            <Panel>
              <p className="flex items-center gap-2 text-sm font-semibold text-ink-soft">
                <Icon name={isCard ? "card" : "phone"} size={18} />
                {isCard ? t("cardNumber") : t("walletNumber", { method: tc(`methods.${info.method}`) })}
              </p>
              <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
                <p className="tabular whitespace-nowrap font-display text-[1.3rem] font-extrabold min-[380px]:text-2xl sm:text-3xl">
                  {info.account}
                </p>
                <CopyButton
                  value={info.account.replace(/\s+/g, "")}
                  label={isCard ? t("copyCard") : t("copyWallet")}
                />
              </div>
              {info.recipient && (
                <p className="mt-3 text-sm">
                  <span className="text-ink-soft">{t("recipient")}: </span>
                  <span className="font-semibold">{info.recipient}</span>
                </p>
              )}

              {info.banks.length > 0 && (
                <div className="mt-5 border-t border-line pt-5">
                  {isCard && <p className="mb-3 text-sm text-ink-soft">{t("fromRussia")}</p>}
                  <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                    {info.banks.map((b) => (
                      <a
                        key={b.code}
                        href={b.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={buttonClass(isCard ? "quiet" : "primary", "md", "w-full sm:w-auto")}
                      >
                        <Icon name="bank" size={18} />
                        {t(`openBank.${b.code}`)}
                        <Icon name="external" size={16} />
                      </a>
                    ))}
                  </div>
                  <p className="mt-2 text-xs text-ink-soft">{t("appHint")}</p>
                </div>
              )}
            </Panel>
          ) : (
            <Notice tone="error">{te("method_unavailable")}</Notice>
          )}
        </>
      )}

      {canUpload && (
        <Panel>
          <h2 className="flex items-center gap-2 text-lg font-extrabold">
            <Icon name="receipt" />
            {t("uploadTitle")}
          </h2>
          <p className="mt-1 text-sm text-ink-soft">{t("uploadText")}</p>

          {preview ? (
            <div className="mt-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={preview}
                alt={t("previewAlt")}
                className="max-h-80 w-full rounded-md border border-line bg-paper object-contain"
              />
              <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                <Button size="lg" className="w-full sm:w-auto" disabled={busy} onClick={send}>
                  <Icon name="send" size={18} />
                  {busy ? t("sending") : t("send")}
                </Button>
                <Button
                  tone="quiet"
                  size="lg"
                  className="w-full sm:w-auto"
                  disabled={busy}
                  onClick={() => inputRef.current?.click()}
                >
                  {t("chooseOther")}
                </Button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className={cx(
                "mt-4 flex min-h-40 w-full flex-col items-center justify-center gap-2 rounded-md border-2 border-dashed border-line bg-paper px-4 py-6 text-center transition-colors hover:border-lapis focus-visible:border-lapis focus-visible:outline-none",
                busy && "pointer-events-none opacity-60",
              )}
            >
              <Icon name="upload" size={28} className="text-lapis" />
              <span className="font-semibold text-lapis">{tc("chooseFile")}</span>
              <span className="text-xs text-ink-soft">{tc("receiptHint")}</span>
            </button>
          )}
          <input
            ref={inputRef}
            type="file"
            accept={RECEIPT_TYPES.join(",")}
            className="sr-only"
            tabIndex={-1}
            aria-hidden
            onChange={(e) => {
              pick(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          {replacing && (
            <Button
              tone="quiet"
              size="sm"
              className="mt-3"
              onClick={() => {
                setReplacing(false);
                setFile(null);
                setPreview(null);
              }}
            >
              <Icon name="x" size={16} />
              {t("cancel")}
            </Button>
          )}
        </Panel>
      )}
    </main>
  );
}
