"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { Link, useRouter } from "@/i18n/routing";
import { ApiError, login, register } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const t = useTranslations("auth");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    setError(null);
    if (mode === "register" && password !== String(form.get("password2") ?? "")) {
      setError(te("password_mismatch"));
      return;
    }
    setBusy(true);
    try {
      const user =
        mode === "login" ? await login(email, password) : await register(email, password, locale);
      router.push(user.role === "admin" ? "/admin/payments" : "/cabinet");
    } catch (err) {
      const code = err instanceof ApiError ? err.code : "error";
      setError(te.has(code) ? te(code) : te("error"));
    } finally {
      setBusy(false);
    }
  }

  const input =
    "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-100";

  return (
    <main className="mx-auto max-w-sm px-4 py-12">
      <h1 className="text-2xl font-bold">{t(mode === "login" ? "loginTitle" : "registerTitle")}</h1>
      <form onSubmit={onSubmit} className="mt-6 space-y-4" noValidate={false}>
        <label className="block text-sm">
          {t("email")}
          <input name="email" type="email" required maxLength={254} autoComplete="email" className={input} />
        </label>
        <label className="block text-sm">
          {t("password")}
          <input
            name="password"
            type="password"
            required
            minLength={mode === "register" ? 10 : 1}
            maxLength={128}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            className={input}
          />
        </label>
        {mode === "register" && (
          <label className="block text-sm">
            {t("password2")}
            <input
              name="password2"
              type="password"
              required
              minLength={10}
              maxLength={128}
              autoComplete="new-password"
              className={input}
            />
            <span className="mt-1 block text-xs text-slate-500">{t("passwordHint")}</span>
          </label>
        )}
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-lg bg-brand-600 px-4 py-2 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {t(mode === "login" ? "loginButton" : "registerButton")}
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">
        {mode === "login" ? (
          <Link href="/register" className="text-brand-700 underline">
            {t("toRegister")}
          </Link>
        ) : (
          <Link href="/login" className="text-brand-700 underline">
            {t("toLogin")}
          </Link>
        )}
      </p>
    </main>
  );
}
