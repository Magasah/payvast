"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Badge, Button, Icon, Notice, cx, inputClass } from "@/components/ui";
import { Link } from "@/i18n/routing";
import { ApiError, api, imageUrl } from "@/lib/api";
import { formatDate, formatSomoni } from "@/lib/format";
import { PAYMENT_TONE } from "@/lib/status";
import type { AdminPayment, PaymentStatus } from "@/lib/types";

const TABS: PaymentStatus[] = ["pending_review", "awaiting_receipt", "confirmed", "rejected"];

type Pending = { id: string; action: "confirm" | "reject" } | null;

export function AdminPayments() {
  const t = useTranslations("admin");
  const tc = useTranslations("cabinet");
  const te = useTranslations("errors");
  const locale = useLocale();

  const [tab, setTab] = useState<PaymentStatus>("pending_review");
  const [rows, setRows] = useState<AdminPayment[] | null>(null);
  const [receipt, setReceipt] = useState<string | null>(null);
  const [pending, setPending] = useState<Pending>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const load = useCallback(async () => {
    setRows(await api<AdminPayment[]>(`/api/admin/payments?status=${tab}`));
  }, [tab]);

  useEffect(() => {
    setRows(null);
    load().catch(() => setNotice({ tone: "error", text: te("error") }));
  }, [load, te]);

  useEffect(() => {
    if (!receipt) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setReceipt(null);
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      URL.revokeObjectURL(receipt);
    };
  }, [receipt]);

  async function run(id: string, action: "confirm" | "reject") {
    setBusy(true);
    setNotice(null);
    try {
      await api(`/api/admin/payments/${id}/${action}`, {
        method: "POST",
        body: action === "reject" ? JSON.stringify({ reason: reason.trim() }) : undefined,
      });
      setNotice({ tone: "success", text: t(action === "confirm" ? "confirmed" : "rejected") });
      setPending(null);
      setReason("");
      await load();
    } catch (err) {
      const code = err instanceof ApiError ? err.code : "error";
      setNotice({ tone: "error", text: te.has(code) ? te(code) : te("error") });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-black tracking-display sm:text-3xl">{t("title")}</h1>

      <div role="tablist" className="-mx-4 mt-5 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0">
        {TABS.map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={tab === s}
            type="button"
            onClick={() => {
              setTab(s);
              setPending(null);
            }}
            className={cx(
              "shrink-0 whitespace-nowrap rounded-md px-4 py-2 text-sm font-semibold transition-colors",
              tab === s ? "bg-lapis text-white" : "border border-line bg-surface text-ink-soft hover:text-ink",
            )}
          >
            {tc(`paymentStatuses.${s}`)}
          </button>
        ))}
      </div>

      {notice && (
        <Notice tone={notice.tone} className="mt-5">
          {notice.text}
        </Notice>
      )}

      <div className="mt-6 divide-y divide-line rounded-lg border border-line bg-surface">
        {rows === null && <div className="h-24 animate-pulse bg-paper" />}
        {rows?.length === 0 && <p className="px-5 py-10 text-center text-ink-soft">{t("empty")}</p>}
        {rows?.map((p) => {
          const isPending = pending?.id === p.id;
          const open = p.status === "pending_review" || p.status === "awaiting_receipt";
          return (
            <div key={p.id} className="px-4 py-4 sm:px-5">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <div className="min-w-0 flex-1">
                  <Link
                    href={`/admin/users/${p.user_id}`}
                    className="block truncate font-semibold text-lapis-deep hover:underline"
                  >
                    {p.user_telegram ? `@${p.user_telegram}` : (p.user_email ?? t("noName"))}
                  </Link>
                  <p className="text-sm text-ink-soft">
                    {formatDate(p.created_at, locale)}, {tc(`methods.${p.method}`)},{" "}
                    {p.plan_code} ({p.duration_days} {t("days")})
                  </p>
                </div>
                <p className="tabular font-display text-xl font-black text-lapis-deep">
                  {formatSomoni(p.amount_dirams, locale)}
                </p>
                <Badge tone={PAYMENT_TONE[p.status]}>{tc(`paymentStatuses.${p.status}`)}</Badge>
                <div className="flex flex-wrap gap-2">
                  {p.has_receipt && (
                    <Button
                      size="sm"
                      tone="quiet"
                      onClick={async () =>
                        setReceipt(await imageUrl(`/api/admin/payments/${p.id}/receipt`))
                      }
                    >
                      <Icon name="eye" size={16} />
                      {t("receipt")}
                    </Button>
                  )}
                  {open && !isPending && (
                    <>
                      {p.status === "pending_review" && (
                        <Button size="sm" tone="success" onClick={() => setPending({ id: p.id, action: "confirm" })}>
                          <Icon name="check" size={16} />
                          {t("confirm")}
                        </Button>
                      )}
                      <Button size="sm" tone="quiet" onClick={() => setPending({ id: p.id, action: "reject" })}>
                        <Icon name="x" size={16} />
                        {t("reject")}
                      </Button>
                    </>
                  )}
                </div>
              </div>
              {p.reject_reason && <p className="mt-2 text-sm text-pomegranate">{p.reject_reason}</p>}

              {isPending && pending.action === "confirm" && (
                <div className="mt-4 flex flex-wrap items-center gap-3 rounded-md bg-pistachio-tint px-4 py-3">
                  <p className="flex-1 text-sm">{t("confirmQuestion", { amount: formatSomoni(p.amount_dirams, locale) })}</p>
                  <Button size="sm" tone="success" disabled={busy} onClick={() => run(p.id, "confirm")}>
                    {t("confirmYes")}
                  </Button>
                  <Button size="sm" tone="quiet" onClick={() => setPending(null)}>
                    {t("cancel")}
                  </Button>
                </div>
              )}
              {isPending && pending.action === "reject" && (
                <form
                  className="mt-4 flex flex-wrap items-end gap-3 rounded-md bg-pomegranate-tint px-4 py-3"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void run(p.id, "reject");
                  }}
                >
                  <div className="flex w-full flex-wrap gap-2">
                    {(["reasonAmount", "reasonUnreadable", "reasonNotFound"] as const).map((k) => (
                      <button
                        key={k}
                        type="button"
                        onClick={() => setReason(t(k))}
                        className="rounded-sm border border-pomegranate/30 bg-surface px-2.5 py-1 text-xs font-medium text-ink hover:border-pomegranate"
                      >
                        {t(k)}
                      </button>
                    ))}
                  </div>
                  <label className="min-w-0 flex-1 basis-56 text-sm font-medium">
                    {t("rejectReason")}
                    <input
                      autoFocus
                      required
                      minLength={3}
                      maxLength={500}
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      className={cx(inputClass, "mt-1 h-10")}
                    />
                  </label>
                  <Button size="sm" tone="danger" type="submit" disabled={busy || reason.trim().length < 3}>
                    {t("rejectYes")}
                  </Button>
                  <Button size="sm" tone="quiet" onClick={() => setPending(null)}>
                    {t("cancel")}
                  </Button>
                </form>
              )}
            </div>
          );
        })}
      </div>

      {receipt && (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-ink/70 p-4"
          onClick={() => setReceipt(null)}
          role="dialog"
          aria-modal="true"
          aria-label={t("receipt")}
        >
          <button
            type="button"
            onClick={() => setReceipt(null)}
            aria-label={t("close")}
            className="absolute right-3 top-3 inline-flex h-11 w-11 items-center justify-center rounded-full bg-white text-ink"
          >
            <Icon name="x" />
          </button>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={receipt} alt={t("receipt")} className="max-h-full max-w-full rounded-md bg-white" />
        </div>
      )}
    </div>
  );
}
