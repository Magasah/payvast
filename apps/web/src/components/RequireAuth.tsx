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

  if (!ready || !user) return <p className="p-8 text-center text-slate-500">{t("loading")}</p>;
  if (role && user.role !== role)
    return <p className="p-8 text-center text-slate-500">{t("forbidden")}</p>;
  return <>{children}</>;
}
