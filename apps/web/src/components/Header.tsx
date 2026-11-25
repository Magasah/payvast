"use client";

import { useLocale, useTranslations } from "next-intl";

import { useAuth } from "@/components/AuthProvider";
import { Link, usePathname, useRouter } from "@/i18n/routing";
import { logout } from "@/lib/api";

export function Header() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useAuth();

  const otherLocale = locale === "tg" ? "ru" : "tg";

  return (
    <header className="border-b border-slate-200 bg-white">
      <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 text-sm">
        <Link href="/" className="mr-auto text-lg font-bold text-brand-700">
          Payvast
        </Link>
        <Link href="/instructions" className="hover:text-brand-700">
          {t("instructions")}
        </Link>
        {user ? (
          <>
            <Link href="/cabinet" className="hover:text-brand-700">
              {t("cabinet")}
            </Link>
            {user.role === "admin" && (
              <Link href="/admin/payments" className="hover:text-brand-700">
                {t("admin")}
              </Link>
            )}
            <button
              type="button"
              className="hover:text-brand-700"
              onClick={async () => {
                await logout();
                router.push("/");
              }}
            >
              {t("logout")}
            </button>
          </>
        ) : (
          <>
            <Link href="/login" className="hover:text-brand-700">
              {t("login")}
            </Link>
            <Link
              href="/register"
              className="rounded-md bg-brand-600 px-3 py-1.5 font-medium text-white hover:bg-brand-700"
            >
              {t("register")}
            </Link>
          </>
        )}
        <button
          type="button"
          onClick={() => router.replace(pathname, { locale: otherLocale })}
          className="rounded border border-slate-300 px-2 py-1 text-xs uppercase"
          aria-label={t("language")}
        >
          {otherLocale}
        </button>
      </nav>
    </header>
  );
}
