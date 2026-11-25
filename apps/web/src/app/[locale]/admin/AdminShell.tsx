"use client";

import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Icon, cx, type IconName } from "@/components/ui";
import { Link, usePathname } from "@/i18n/routing";

const TABS: { href: string; key: string; icon: IconName }[] = [
  { href: "/admin/payments", key: "tabPayments", icon: "receipt" },
  { href: "/admin/users", key: "tabUsers", icon: "users" },
  { href: "/admin/audit", key: "tabAudit", icon: "list" },
];

export function AdminShell({ children }: { children: ReactNode }) {
  const t = useTranslations("admin");
  const pathname = usePathname();
  return (
    <main className="mx-auto max-w-page px-4 py-6 sm:px-6 sm:py-10">
      <nav
        aria-label={t("navLabel")}
        className="mb-6 grid grid-cols-3 gap-1 rounded-md border border-line bg-surface p-1 sm:inline-grid sm:w-auto"
      >
        {TABS.map((tab) => {
          const active = pathname.startsWith(tab.href);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={active ? "page" : undefined}
              className={cx(
                "flex min-h-11 items-center justify-center gap-2 rounded-[9px] px-3 text-sm font-semibold transition-colors sm:px-5",
                active ? "bg-lapis text-white" : "text-ink-soft hover:text-ink",
              )}
            >
              <Icon name={tab.icon} size={18} />
              <span className="truncate">{t(tab.key)}</span>
            </Link>
          );
        })}
      </nav>
      {children}
    </main>
  );
}
