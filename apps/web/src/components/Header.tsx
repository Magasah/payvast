"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { ButtonLink, Icon, cx, type IconName } from "@/components/ui";
import { Link, usePathname, useRouter } from "@/i18n/routing";
import { logout } from "@/lib/api";

const navLink =
  "inline-flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm font-medium text-ink-soft hover:text-lapis";

type Item = { href: string; label: string; icon: IconName };

export function Header() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const router = useRouter();
  const { user, ready } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const other = locale === "tg" ? "ru" : "tg";

  // Close the phone menu on navigation and on Escape.
  useEffect(() => setMenuOpen(false), [pathname]);
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMenuOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  const items: Item[] = [{ href: "/instructions", label: t("instructions"), icon: "info" }];
  if (user) items.push({ href: "/cabinet", label: t("cabinet"), icon: "user" });
  if (user?.is_admin) items.push({ href: "/admin/payments", label: t("admin"), icon: "shield" });

  async function signOut() {
    await logout();
    router.push("/");
  }

  const switchLang = (
    <button
      type="button"
      lang={other}
      onClick={() => router.replace(pathname, { locale: other })}
      className="inline-flex h-9 items-center gap-1.5 rounded-md border border-line px-2.5 text-xs font-semibold text-ink-soft hover:border-lapis hover:text-lapis"
    >
      <Icon name="globe" size={16} />
      {t("switchTo")}
    </button>
  );

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur supports-[backdrop-filter]:bg-surface/75">
      <nav className="mx-auto flex h-16 max-w-page items-center gap-1 px-4 sm:gap-2 sm:px-6">
        <Link
          href="/"
          className="mr-auto font-display text-xl font-black tracking-display text-lapis-deep"
        >
          Payvast
        </Link>

        {/* Tablet and desktop */}
        <div className="hidden items-center gap-1 md:flex">
          {items.map((it) => (
            <Link key={it.href} href={it.href} className={navLink}>
              <Icon name={it.icon} size={16} />
              {it.label}
            </Link>
          ))}
          {user ? (
            <button type="button" className={navLink} onClick={signOut}>
              <Icon name="logout" size={16} />
              {t("logout")}
            </button>
          ) : (
            <>
              <Link href="/login" className={navLink} aria-disabled={!ready}>
                {t("login")}
              </Link>
              <ButtonLink href="/register" size="sm">
                {t("register")}
              </ButtonLink>
            </>
          )}
        </div>

        {switchLang}

        {/* Phones */}
        <button
          type="button"
          className="ml-1 inline-flex h-9 w-9 items-center justify-center rounded-md border border-line text-ink md:hidden"
          aria-expanded={menuOpen}
          aria-controls="mobile-menu"
          aria-label={menuOpen ? t("closeMenu") : t("openMenu")}
          onClick={() => setMenuOpen((v) => !v)}
        >
          <Icon name={menuOpen ? "x" : "menu"} />
        </button>
      </nav>

      <div
        id="mobile-menu"
        hidden={!menuOpen}
        className="border-t border-line bg-surface md:hidden"
      >
        <ul className="mx-auto max-w-page px-2 py-2">
          {items.map((it) => (
            <li key={it.href}>
              <Link
                href={it.href}
                className={cx(
                  "flex min-h-12 items-center gap-3 rounded-md px-3 text-base font-medium",
                  pathname.startsWith(it.href) ? "bg-lapis-tint text-lapis-deep" : "text-ink",
                )}
              >
                <Icon name={it.icon} />
                {it.label}
              </Link>
            </li>
          ))}
          <li className="mt-1 border-t border-line pt-1">
            {user ? (
              <button
                type="button"
                onClick={signOut}
                className="flex min-h-12 w-full items-center gap-3 rounded-md px-3 text-base font-medium text-ink"
              >
                <Icon name="logout" />
                {t("logout")}
              </button>
            ) : (
              <div className="grid grid-cols-2 gap-2 p-2">
                <ButtonLink href="/login" tone="quiet">
                  {t("login")}
                </ButtonLink>
                <ButtonLink href="/register">{t("register")}</ButtonLink>
              </div>
            )}
          </li>
        </ul>
      </div>
    </header>
  );
}
