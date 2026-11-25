"use client";

import { useTranslations } from "next-intl";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/components/AuthProvider";
import { useRouter } from "@/i18n/routing";

/** Client-side guard for UX only. The API enforces auth and roles on every request. */
export function RequireAuth({ admin, children }: { admin?: boolean; children: ReactNode }) {
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
  if (admin && !user.is_admin) {
    // Same as a missing page: the admin area does not reveal itself.
    return <p className="mx-auto max-w-page px-4 py-12 text-ink-soft sm:px-6">{t("notFound")}</p>;
  }
  return <>{children}</>;
}
