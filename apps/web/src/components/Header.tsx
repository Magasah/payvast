"use client";

import { useLocale, useTranslations } from "next-intl";

import { useAuth } from "@/components/AuthProvider";
import { ButtonLink } from "@/components/ui";
import { Link, usePathname, useRouter } from "@/i18n/routing";
import { logout } from "@/lib/api";

const navLink = "rounded-md px-2 py-1.5 text-sm font-medium text-ink-soft hover:text-lapis";

export function Header() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const { user, ready } = useAuth();
  const other = locale === "tg" ? "ru" : "tg";

  return (
    <header className="border-b border-line bg-surface/90 backdrop-blur supports-[backdrop-filter]:bg-surface/75">
      <nav className="mx-auto flex h-16 max-w-page items-center gap-1 px-4 sm:gap-3 sm:px-6">
        <Link
          href="/"
          className="mr-auto font-display text-xl font-black tracking-display text-lapis-deep"
        >
          Payvast
        </Link>
        <Link href="/instructions" className={`${navLink} hidden sm:inline`}>
          {t("instructions")}
        </Link>
        {user?.role === "admin" && (
          <Link href="/admin/payments" className={navLink}>
            {t("admin")}
          </Link>
        )}
        {user ? (
          <>
            <Link href="/cabinet" className={navLink}>
              {t("cabinet")}
            </Link>
            <button
              type="button"
              className={navLink}
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
            <Link href="/login" className={navLink} aria-disabled={!ready}>
              {t("login")}
            </Link>
            <ButtonLink href="/register" size="sm" className="hidden sm:inline-flex">
              {t("register")}
            </ButtonLink>
          </>
        )}
        <button
          type="button"
          lang={other}
          onClick={() => router.replace(pathname, { locale: other })}
          className="ml-1 rounded-md border border-line px-2.5 py-1 text-xs font-semibold text-ink-soft hover:border-lapis hover:text-lapis"
        >
          {t("switchTo")}
        </button>
      </nav>
    </header>
  );
}
