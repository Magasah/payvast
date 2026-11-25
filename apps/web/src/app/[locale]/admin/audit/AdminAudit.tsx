"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { Button, Notice } from "@/components/ui";
import { api } from "@/lib/api";
import type { AuditEntry } from "@/lib/types";

import { AuditList } from "./AuditList";

type Page = { items: AuditEntry[]; next_before: number | null };

export function AdminAudit() {
  const t = useTranslations("admin");
  const te = useTranslations("errors");
  const [items, setItems] = useState<AuditEntry[] | null>(null);
  const [next, setNext] = useState<number | null>(null);
  const [error, setError] = useState(false);

  const load = useCallback(async (before: number | null) => {
    const page = await api<Page>(`/api/admin/audit?limit=50${before ? `&before=${before}` : ""}`);
    setItems((cur) => (before ? [...(cur ?? []), ...page.items] : page.items));
    setNext(page.next_before);
  }, []);

  useEffect(() => {
    load(null).catch(() => setError(true));
  }, [load]);

  return (
    <div>
      <h1 className="text-2xl font-black tracking-display sm:text-3xl">{t("auditTitle")}</h1>
      <p className="mt-1 text-sm text-ink-soft">{t("auditLead")}</p>
      {error && (
        <Notice tone="error" className="mt-5">
          {te("error")}
        </Notice>
      )}
      {items === null && !error ? (
        <div className="mt-5 h-40 animate-pulse rounded-lg bg-paper" />
      ) : (
        <AuditList items={items ?? []} className="mt-5" />
      )}
      {next && (
        <Button tone="quiet" className="mt-4 w-full sm:w-auto" onClick={() => void load(next)}>
          {t("showMore")}
        </Button>
      )}
    </div>
  );
}
