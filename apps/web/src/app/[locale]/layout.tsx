import type { Metadata, Viewport } from "next";
import { notFound } from "next/navigation";
import { NextIntlClientProvider, type AbstractIntlMessages } from "next-intl";
import { getMessages, getTranslations, setRequestLocale } from "next-intl/server";
import type { ReactNode } from "react";

import { AuthProvider } from "@/components/AuthProvider";
import { Header } from "@/components/Header";
import { routing, type Locale } from "@/i18n/routing";

import "../globals.css";

const CLIENT_NAMESPACES = ["nav", "auth", "cabinet", "pay", "admin", "errors", "common", "plans"];

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export const viewport: Viewport = {
  themeColor: "#172E6E",
  width: "device-width",
  initialScale: 1,
};

export async function generateMetadata({
  params: { locale },
}: {
  params: { locale: string };
}): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace: "meta" });
  return { title: t("title"), description: t("description") };
}

export default async function LocaleLayout({
  children,
  params: { locale },
}: {
  children: ReactNode;
  params: { locale: string };
}) {
  if (!routing.locales.includes(locale as Locale)) notFound();
  setRequestLocale(locale);
  const all = await getMessages();
  // Only namespaces used by client components are serialized into the page.
  const messages: AbstractIntlMessages = Object.fromEntries(
    CLIENT_NAMESPACES.map((ns) => [ns, all[ns] ?? {}]),
  );
  const t = await getTranslations("footer");

  return (
    <html lang={locale}>
      <head>
        {/* Preload the faces every page needs above the fold. */}
        <link
          rel="preload"
          href="/fonts/golos-text-cyrillic.woff2"
          as="font"
          type="font/woff2"
          crossOrigin="anonymous"
        />
        <link
          rel="preload"
          href="/fonts/commissioner-cyrillic.woff2"
          as="font"
          type="font/woff2"
          crossOrigin="anonymous"
        />
      </head>
      <body className="flex min-h-dvh flex-col">
        <NextIntlClientProvider messages={messages}>
          <AuthProvider>
            <Header />
            <div className="flex-1">{children}</div>
            <footer className="mt-16 border-t border-line">
              <div className="mx-auto flex max-w-page flex-col gap-1 px-4 py-8 text-sm text-ink-soft sm:flex-row sm:justify-between sm:px-6">
                <p className="font-display font-extrabold text-ink">Payvast</p>
                <p>{t("privacy")}</p>
              </div>
            </footer>
          </AuthProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
