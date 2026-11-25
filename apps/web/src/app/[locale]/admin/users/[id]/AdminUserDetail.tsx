"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { CopyButton } from "@/components/CopyButton";
import { Badge, Button, Icon, Notice, Panel, cx, inputClass } from "@/components/ui";
import { Link } from "@/i18n/routing";
import { ApiError, api } from "@/lib/api";
import { formatDate, formatDateTime, formatSomoni, userTitle } from "@/lib/format";
import { PAYMENT_TONE, SUB_TONE } from "@/lib/status";
import type { AdminUserDetail as Detail, AuditEntry } from "@/lib/types";

import { AuditList } from "../../audit/AuditList";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const QUICK_DAYS = [7, 30, 90, 365];

type Confirm = { kind: "revoke" } | { kind: "block" } | { kind: "days"; days: number } | null;

export function AdminUserDetail({ userId }: { userId: string }) {
  const t = useTranslations("admin");
  const tc = useTranslations("cabinet");
  const te = useTranslations("errors");
  const locale = useLocale();

  const [data, setData] = useState<Detail | null>(null);
  const [log, setLog] = useState<AuditEntry[]>([]);
  const [missing, setMissing] = useState(!UUID_RE.test(userId));
  const [days, setDays] = useState("30");
  const [devices, setDevices] = useState("");
  const [note, setNote] = useState("");
  const [confirm, setConfirm] = useState<Confirm>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const loadLog = useCallback(async () => {
    const page = await api<{ items: AuditEntry[] }>(
      `/api/admin/audit?limit=20&target_id=${encodeURIComponent(userId)}`,
    );
    setLog(page.items);
  }, [userId]);

  useEffect(() => {
    if (missing) return;
    api<Detail>(`/api/admin/users/${userId}`)
      .then((d) => {
        setData(d);
        if (d.subscription) setDevices(String(d.subscription.device_limit));
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) setMissing(true);
        else setNotice({ tone: "error", text: te("error") });
      });
    void loadLog().catch(() => undefined);
  }, [userId, missing, te, loadLog]);

  async function act(path: string, body: unknown, okText: string) {
    setBusy(true);
    setNotice(null);
    try {
      const d = await api<Detail>(`/api/admin/users/${userId}/${path}`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setData(d);
      setConfirm(null);
      setNote("");
      setNotice({ tone: "success", text: okText });
      await loadLog();
    } catch (err) {
      const code = err instanceof ApiError ? err.code : "error";
      setNotice({ tone: "error", text: te.has(code) ? te(code) : te("error") });
    } finally {
      setBusy(false);
    }
  }

  function applyDays(n: number) {
    const limit = Number(devices);
    void act(
      "subscription/days",
      {
        days: n,
        device_limit: Number.isInteger(limit) && limit >= 1 && limit <= 10 ? limit : null,
        note: note.trim() || null,
      },
      n > 0 ? t("daysAdded", { n }) : t("daysRemoved", { n: -n }),
    );
  }

  if (missing) {
    return (
      <div>
        <Notice tone="error">{t("userNotFound")}</Notice>
        <Link href="/admin/users" className="mt-4 inline-flex min-h-11 items-center gap-1.5 font-semibold text-lapis">
          <Icon name="back" size={18} />
          {t("backToUsers")}
        </Link>
      </div>
    );
  }
  if (!data) {
    return <div className="h-64 animate-pulse rounded-lg bg-lapis-tint" aria-busy="true" />;
  }

  const { user, subscription: sub, payments } = data;
  const customDays = Number(days);
  const customValid = Number.isInteger(customDays) && customDays !== 0 && Math.abs(customDays) <= 3650;

  return (
    <div className="space-y-6">
      <Link
        href="/admin/users"
        className="inline-flex min-h-11 items-center gap-1.5 text-sm font-semibold text-ink-soft hover:text-lapis"
      >
        <Icon name="back" size={18} />
        {t("backToUsers")}
      </Link>

      <header className="flex flex-wrap items-center gap-3">
        <h1 className="min-w-0 break-all text-2xl font-black tracking-display sm:text-3xl">
          {userTitle(user, t("noName"))}
        </h1>
        {user.is_admin && <Badge tone="lapis">{t("adminBadge")}</Badge>}
        {!user.is_active && <Badge tone="pomegranate">{t("blocked")}</Badge>}
      </header>

      <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
        {user.email && (
          <div className="flex gap-2">
            <dt className="text-ink-soft">Email:</dt>
            <dd className="break-all font-medium">{user.email}</dd>
          </div>
        )}
        {user.telegram_id && (
          <div className="flex gap-2">
            <dt className="text-ink-soft">Telegram ID:</dt>
            <dd className="tabular font-medium">{user.telegram_id}</dd>
          </div>
        )}
        <div className="flex gap-2">
          <dt className="text-ink-soft">{t("registered")}:</dt>
          <dd className="font-medium">{formatDate(user.created_at, locale)}</dd>
        </div>
        <div className="flex gap-2">
          <dt className="text-ink-soft">{t("language")}:</dt>
          <dd className="font-medium">{user.locale === "ru" ? "Русский" : "Тоҷикӣ"}</dd>
        </div>
      </dl>

      {notice && <Notice tone={notice.tone}>{notice.text}</Notice>}

      <Panel>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-extrabold">{t("subscription")}</h2>
          {sub && <Badge tone={SUB_TONE[sub.status]}>{tc(`statuses.${sub.status}`)}</Badge>}
        </div>
        {sub ? (
          <div className="mt-3 grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-sm text-ink-soft">{t("expires")}</p>
              <p className="font-semibold">{formatDateTime(sub.expires_at, locale)}</p>
            </div>
            <div>
              <p className="text-sm text-ink-soft">{t("daysLeftLabel")}</p>
              <p className="tabular font-display text-2xl font-black text-lapis-deep">{sub.days_left}</p>
            </div>
            <div>
              <p className="text-sm text-ink-soft">{t("devices")}</p>
              <p className="font-semibold">{sub.device_limit}</p>
            </div>
            <div className="flex min-w-0 items-center gap-2 sm:col-span-3">
              <input
                readOnly
                value={sub.subscription_url}
                aria-label={tc("link")}
                className={cx(inputClass, "h-9 min-w-0 flex-1 text-sm")}
                onFocus={(e) => e.currentTarget.select()}
              />
              <CopyButton value={sub.subscription_url} />
            </div>
          </div>
        ) : (
          <p className="mt-2 text-ink-soft">{t("noSubscription")}</p>
        )}
      </Panel>

      <Panel>
        <h2 className="text-lg font-extrabold">{t("manageTerm")}</h2>
        <p className="mt-1 text-sm text-ink-soft">{t("manageHint")}</p>

        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {QUICK_DAYS.map((n) => (
            <Button key={n} tone="quiet" disabled={busy} onClick={() => setConfirm({ kind: "days", days: n })}>
              <Icon name="plus" size={16} />
              {t("plusDays", { n })}
            </Button>
          ))}
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_2fr]">
          <label className="text-sm font-medium">
            {t("customDays")}
            <input
              type="number"
              inputMode="numeric"
              min={-3650}
              max={3650}
              step={1}
              value={days}
              onChange={(e) => setDays(e.target.value)}
              className={cx(inputClass, "mt-1")}
            />
          </label>
          <label className="text-sm font-medium">
            {t("devices")}
            <input
              type="number"
              inputMode="numeric"
              min={1}
              max={10}
              value={devices}
              placeholder="1"
              onChange={(e) => setDevices(e.target.value)}
              className={cx(inputClass, "mt-1")}
            />
          </label>
          <label className="text-sm font-medium">
            {t("note")}
            <input
              value={note}
              maxLength={300}
              onChange={(e) => setNote(e.target.value)}
              placeholder={t("notePlaceholder")}
              className={cx(inputClass, "mt-1")}
            />
          </label>
        </div>
        <p className="mt-2 text-xs text-ink-soft">{t("customDaysHint")}</p>
        <Button
          className="mt-3 w-full sm:w-auto"
          disabled={busy || !customValid}
          onClick={() => setConfirm({ kind: "days", days: customDays })}
        >
          {customDays < 0 ? <Icon name="minus" size={18} /> : <Icon name="plus" size={18} />}
          {t("applyDays")}
        </Button>

        {confirm?.kind === "days" && (
          <div className="mt-4 flex flex-col gap-3 rounded-md bg-lapis-tint px-4 py-3 sm:flex-row sm:items-center">
            <p className="flex-1 text-sm">
              {confirm.days > 0
                ? t("confirmAdd", { n: confirm.days })
                : t("confirmRemove", { n: -confirm.days })}
            </p>
            <div className="flex gap-2">
              <Button size="sm" disabled={busy} onClick={() => applyDays(confirm.days)}>
                {t("yes")}
              </Button>
              <Button size="sm" tone="quiet" onClick={() => setConfirm(null)}>
                {t("cancel")}
              </Button>
            </div>
          </div>
        )}

        <div className="mt-6 flex flex-col gap-2 border-t border-line pt-5 sm:flex-row sm:flex-wrap">
          {sub && sub.status !== "disabled" && (
            <Button tone="danger" disabled={busy} onClick={() => setConfirm({ kind: "revoke" })}>
              <Icon name="ban" size={18} />
              {t("revoke")}
            </Button>
          )}
          {sub?.status === "disabled" && (
            <Button
              tone="success"
              disabled={busy}
              onClick={() => void act("subscription/restore", undefined, t("restored"))}
            >
              <Icon name="restore" size={18} />
              {t("restore")}
            </Button>
          )}
          {!user.is_admin && (
            <Button
              tone="quiet"
              disabled={busy}
              onClick={() =>
                user.is_active
                  ? setConfirm({ kind: "block" })
                  : void act("active", { is_active: true }, t("unblocked"))
              }
            >
              <Icon name={user.is_active ? "ban" : "restore"} size={18} />
              {user.is_active ? t("block") : t("unblock")}
            </Button>
          )}
        </div>

        {(confirm?.kind === "revoke" || confirm?.kind === "block") && (
          <div className="mt-4 flex flex-col gap-3 rounded-md bg-pomegranate-tint px-4 py-3 sm:flex-row sm:items-center">
            <p className="flex-1 text-sm">
              {confirm.kind === "revoke" ? t("confirmRevoke") : t("confirmBlock")}
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                tone="danger"
                disabled={busy}
                onClick={() =>
                  confirm.kind === "revoke"
                    ? void act("subscription/revoke", { note: note.trim() || null }, t("revoked"))
                    : void act("active", { is_active: false }, t("blockedDone"))
                }
              >
                {t("yes")}
              </Button>
              <Button size="sm" tone="quiet" onClick={() => setConfirm(null)}>
                {t("cancel")}
              </Button>
            </div>
          </div>
        )}
      </Panel>

      <section>
        <h2 className="text-lg font-extrabold">{t("userPayments")}</h2>
        <ul className="mt-3 divide-y divide-line rounded-lg border border-line bg-surface">
          {payments.length === 0 && <li className="px-5 py-6 text-center text-ink-soft">{t("empty")}</li>}
          {payments.map((p) => (
            <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 sm:px-5">
              <div className="min-w-0">
                <p className="font-semibold">
                  {formatSomoni(p.amount_dirams, locale)} · {p.plan_code}
                </p>
                <p className="text-sm text-ink-soft">
                  {formatDate(p.created_at, locale)} · {tc(`methods.${p.method}`)}
                  {p.reject_reason ? ` · ${p.reject_reason}` : ""}
                </p>
              </div>
              <Badge tone={PAYMENT_TONE[p.status]}>{tc(`paymentStatuses.${p.status}`)}</Badge>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="text-lg font-extrabold">{t("userActivity")}</h2>
        <AuditList items={log} className="mt-3" />
      </section>
    </div>
  );
}
