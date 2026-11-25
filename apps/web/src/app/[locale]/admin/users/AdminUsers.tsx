"use client";

import { useLocale, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Badge, Button, Icon, Notice, cx, inputClass } from "@/components/ui";
import { Link } from "@/i18n/routing";
import { api } from "@/lib/api";
import { formatDate, userTitle } from "@/lib/format";
import { SUB_TONE } from "@/lib/status";
import type { AdminUserRow, SubStatus } from "@/lib/types";

const PAGE = 30;
const FILTERS: (SubStatus | "all")[] = ["all", "active", "expired", "disabled"];

export function AdminUsers() {
  const t = useTranslations("admin");
  const tc = useTranslations("cabinet");
  const te = useTranslations("errors");
  const locale = useLocale();

  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [filter, setFilter] = useState<SubStatus | "all">("all");
  const [items, setItems] = useState<AdminUserRow[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState(false);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(query.trim()), 300);
    return () => clearTimeout(id);
  }, [query]);

  const fetchPage = useCallback(
    async (offset: number) => {
      const params = new URLSearchParams({ limit: String(PAGE), offset: String(offset) });
      if (debounced) params.set("q", debounced);
      if (filter !== "all") params.set("status", filter);
      return api<{ items: AdminUserRow[]; total: number }>(`/api/admin/users?${params}`);
    },
    [debounced, filter],
  );

  useEffect(() => {
    let live = true;
    setItems(null);
    setError(false);
    fetchPage(0)
      .then((page) => {
        if (!live) return;
        setItems(page.items);
        setTotal(page.total);
      })
      .catch(() => live && setError(true));
    return () => {
      live = false;
    };
  }, [fetchPage]);

  async function more() {
    const page = await fetchPage(items?.length ?? 0);
    setItems((cur) => [...(cur ?? []), ...page.items]);
    setTotal(page.total);
  }

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-black tracking-display sm:text-3xl">{t("usersTitle")}</h1>
        <p className="text-sm text-ink-soft">{t("usersTotal", { n: total })}</p>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
        <label className="relative block flex-1">
          <span className="sr-only">{t("search")}</span>
          <Icon
            name="search"
            size={18}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-soft"
          />
          <input
            type="search"
            value={query}
            maxLength={64}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("searchPlaceholder")}
            className={cx(inputClass, "pl-10")}
          />
        </label>
        <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0 sm:pb-0">
          {FILTERS.map((f) => (
            <button
              key={f}
              type="button"
              aria-pressed={filter === f}
              onClick={() => setFilter(f)}
              className={cx(
                "h-10 shrink-0 whitespace-nowrap rounded-md px-3 text-sm font-semibold",
                filter === f ? "bg-lapis text-white" : "border border-line bg-surface text-ink-soft",
              )}
            >
              {f === "all" ? t("filterAll") : tc(`statuses.${f}`)}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <Notice tone="error" className="mt-5">
          {te("error")}
        </Notice>
      )}

      <ul className="mt-5 divide-y divide-line overflow-hidden rounded-lg border border-line bg-surface">
        {items === null && !error && <li className="h-24 animate-pulse bg-paper" />}
        {items?.length === 0 && (
          <li className="px-5 py-10 text-center text-ink-soft">{t("usersEmpty")}</li>
        )}
        {items?.map((u) => (
          <li key={u.id}>
            <Link
              href={`/admin/users/${u.id}`}
              className="flex items-center gap-3 px-4 py-3 hover:bg-paper sm:px-5"
            >
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-lapis-tint text-lapis-deep">
                <Icon name="user" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="truncate font-semibold">{userTitle(u, t("noName"))}</span>
                  {u.is_admin && <Badge tone="lapis">{t("adminBadge")}</Badge>}
                  {!u.is_active && <Badge tone="pomegranate">{t("blocked")}</Badge>}
                </span>
                <span className="block truncate text-sm text-ink-soft">
                  {u.expires_at
                    ? tc("until", { date: formatDate(u.expires_at, locale) })
                    : t("noSubscription")}
                </span>
              </span>
              {u.subscription_status && (
                <span className="hidden sm:block">
                  <Badge tone={SUB_TONE[u.subscription_status]}>
                    {tc(`statuses.${u.subscription_status}`)}
                  </Badge>
                </span>
              )}
              <Icon name="forward" size={18} className="shrink-0 text-ink-soft" />
            </Link>
          </li>
        ))}
      </ul>

      {items && items.length < total && (
        <Button tone="quiet" className="mt-4 w-full sm:w-auto" onClick={() => void more()}>
          {t("showMore")}
        </Button>
      )}
    </div>
  );
}
