"use client";

import { useTranslations } from "next-intl";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/components/AuthProvider";
import { useRouter } from "@/i18n/routing";
import type { Role } from "@/lib/types";

/** Client-side guard for UX only. The API enforces auth and roles on every request. */
export function RequireAuth({ role, children }: { role?: Role; children: ReactNode }) {
  const { user, ready } = useAuth();
  const router = useRouter();
  const t = useTranslations("common");

  useEffect(() => {
    if (ready && !user) router.replace("/login");
  }, [ready, user, router]);

  if (!ready || !user) {
    return (
      <div className="mx-auto max-w-page px-4 py-12 sm:px-6" aria-busy="true">
        <div className="h-56 animate-pulse rounded-pass bg-lapis-tint" />
        <span className="sr-only">{t("loading")}</span>
      </div>
    );
  }
  if (role && user.role !== role) {
    return <p className="mx-auto max-w-page px-4 py-12 text-ink-soft sm:px-6">{t("forbidden")}</p>;
  }
  return <>{children}</>;
}
