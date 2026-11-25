"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { ApiError, api, imageUrl } from "@/lib/api";
import { formatDate, formatSomoni } from "@/lib/format";
import type { AdminPayment, PaymentStatus } from "@/lib/types";

const TABS: PaymentStatus[] = ["pending_review", "awaiting_receipt", "confirmed", "rejected"];

export function AdminPayments() {
  const t = useTranslations("admin");
  const tc = useTranslations("cabinet");
  const te = useTranslations("errors");
  const locale = useLocale();

  const [tab, setTab] = useState<PaymentStatus>("pending_review");
  const [rows, setRows] = useState<AdminPayment[]>([]);
  const [receipt, setReceipt] = useState<{ id: string; url: string } | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRows(await api<AdminPayment[]>(`/api/admin/payments?status=${tab}`));
  }, [tab]);

  useEffect(() => {
    load().catch(() => setMessage(te("error")));
  }, [load, te]);

  useEffect(() => () => void (receipt && URL.revokeObjectURL(receipt.url)), [receipt]);

  async function act(id: string, action: "confirm" | "reject") {
    let body: string | undefined;
    if (action === "reject") {
      const reason = window.prompt(t("rejectReason"))?.trim();
      if (!reason || reason.length < 3) return;
      body = JSON.stringify({ reason });
    } else if (!window.confirm(t("confirmQuestion"))) {
      return;
    }
    setBusyId(id);
    setMessage(null);
    try {
      await api(`/api/admin/payments/${id}/${action}`, { method: "POST", body });
      setMessage(t(action === "confirm" ? "confirmed" : "rejected"));
      setReceipt(null);
      await load();
    } catch (err) {
      const code = err instanceof ApiError ? err.code : "error";
      setMessage(te.has(code) ? te(code) : te("error"));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-2xl font-bold">{t("title")}</h1>

      <div className="mt-6 flex flex-wrap gap-2 text-sm">
        {TABS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setTab(s)}
            className={`rounded-full border px-4 py-1.5 ${
              tab === s ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-300 bg-white"
            }`}
          >
            {tc(`paymentStatuses.${s}`)}
          </button>
        ))}
      </div>

      {message && <p className="mt-4 rounded-lg bg-slate-100 px-3 py-2 text-sm">{message}</p>}

      <div className="mt-6 overflow-x-auto rounded-xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-2">{t("date")}</th>
              <th className="px-4 py-2">{t("user")}</th>
              <th className="px-4 py-2">{t("plan")}</th>
              <th className="px-4 py-2">{t("amount")}</th>
              <th className="px-4 py-2">{t("method")}</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                  {t("empty")}
                </td>
              </tr>
            )}
            {rows.map((p) => (
              <tr key={p.id}>
                <td className="px-4 py-2">{formatDate(p.created_at, locale)}</td>
                <td className="px-4 py-2">{p.user_email}</td>
                <td className="px-4 py-2">
                  {p.plan_code} · {p.duration_days} {t("days")}
                </td>
                <td className="px-4 py-2 font-medium">{formatSomoni(p.amount_dirams, locale)}</td>
                <td className="px-4 py-2">{tc(`methods.${p.method}`)}</td>
                <td className="space-x-2 whitespace-nowrap px-4 py-2 text-right">
                  {p.has_receipt && (
                    <button
                      type="button"
                      className="text-brand-700 underline"
                      onClick={async () =>
                        setReceipt({
                          id: p.id,
                          url: await imageUrl(`/api/admin/payments/${p.id}/receipt`),
                        })
                      }
                    >
                      {t("receipt")}
                    </button>
                  )}
                  {(p.status === "pending_review" || p.status === "awaiting_receipt") && (
                    <>
                      {p.status === "pending_review" && (
                        <button
                          type="button"
                          disabled={busyId === p.id}
                          onClick={() => act(p.id, "confirm")}
                          className="rounded bg-brand-600 px-3 py-1 text-white disabled:opacity-60"
                        >
                          {t("confirm")}
                        </button>
                      )}
                      <button
                        type="button"
                        disabled={busyId === p.id}
                        onClick={() => act(p.id, "reject")}
                        className="rounded bg-red-600 px-3 py-1 text-white disabled:opacity-60"
                      >
                        {t("reject")}
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {receipt && (
        <div
          className="fixed inset-0 z-10 flex items-center justify-center bg-black/60 p-4"
          onClick={() => setReceipt(null)}
          role="dialog"
          aria-modal="true"
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={receipt.url} alt={t("receipt")} className="max-h-full max-w-full rounded-lg bg-white" />
        </div>
      )}
    </main>
  );
}
