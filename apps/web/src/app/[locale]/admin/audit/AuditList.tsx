"use client";

import { useLocale, useTranslations } from "next-intl";

import { Icon, cx, type IconName } from "@/components/ui";
import { Link } from "@/i18n/routing";
import { formatDate, formatDateTime, formatSomoni } from "@/lib/format";
import type { AuditEntry } from "@/lib/types";

const ICONS: Record<string, IconName> = {
  "payment.confirm": "check",
  "payment.reject": "x",
  "payment.view_receipt": "eye",
  "subscription.grant": "plus",
  "subscription.reduce": "minus",
  "subscription.revoke": "ban",
  "subscription.restore": "restore",
  "subscription.move": "forward",
  "user.block": "ban",
  "user.unblock": "restore",
  "server.create": "plus",
  "server.update": "info",
};

function str(v: unknown): string | null {
  return typeof v === "string" && v ? v : null;
}

export function AuditList({ items, className }: { items: AuditEntry[]; className?: string }) {
  const t = useTranslations("admin");
  const locale = useLocale();

  function summary(e: AuditEntry): string[] {
    const d = e.details;
    const out: string[] = [];
    if (typeof d.days === "number") out.push(t("detailDays", { n: d.days }));
    if (typeof d.amount_dirams === "number") out.push(formatSomoni(d.amount_dirams, locale));
    const until = str(d.new_expires_at);
    if (until) out.push(t("detailUntil", { date: formatDate(until, locale) }));
    const why = str(d.reason) ?? str(d.note);
    if (why) out.push(`«${why}»`);
    return out;
  }

  if (items.length === 0) {
    return (
      <p className={cx("rounded-lg border border-line bg-surface px-5 py-6 text-center text-ink-soft", className)}>
        {t("auditEmpty")}
      </p>
    );
  }

  return (
    <ol className={cx("divide-y divide-line rounded-lg border border-line bg-surface", className)}>
      {items.map((e) => (
        <li key={e.id} className="flex gap-3 px-4 py-3 sm:px-5">
          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-paper text-lapis-deep">
            <Icon name={ICONS[e.action] ?? "info"} size={16} />
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-semibold">
              {/* next-intl reads dots as nesting, so "payment.confirm" -> "payment_confirm" */}
              {t.has(`actions.${e.action.replaceAll(".", "_")}`)
                ? t(`actions.${e.action.replaceAll(".", "_")}`)
                : e.action}
            </p>
            {summary(e).length > 0 && (
              <p className="break-words text-sm text-ink">{summary(e).join(" · ")}</p>
            )}
            <p className="text-xs text-ink-soft">
              {formatDateTime(e.created_at, locale)}
              {e.admin ? ` · ${e.admin}` : ""}
              {e.target_type === "user" && (
                <>
                  {" · "}
                  <Link href={`/admin/users/${e.target_id}`} className="text-lapis hover:underline">
                    {t("openUser")}
                  </Link>
                </>
              )}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
}
