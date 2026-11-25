"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState, type FormEvent } from "react";

import { Button, Field, Notice } from "@/components/ui";
import { Link, useRouter } from "@/i18n/routing";
import { ApiError, login, register } from "@/lib/api";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const t = useTranslations("auth");
  const te = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    setError(null);
    if (!isLogin && password !== String(form.get("password2") ?? "")) {
      setError(te("password_mismatch"));
      return;
    }
    setBusy(true);
    try {
      const user = isLogin ? await login(email, password) : await register(email, password, locale);
      router.push(user.role === "admin" ? "/admin/payments" : "/cabinet");
    } catch (err) {
      const code = err instanceof ApiError ? err.code : "error";
      setError(te.has(code) ? te(code) : te("error"));
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-4 pb-10 pt-12 sm:pt-16">
      <h1 className="text-3xl font-black tracking-display">
        {t(isLogin ? "loginTitle" : "registerTitle")}
      </h1>
      <p className="mt-2 text-ink-soft">{t(isLogin ? "loginLead" : "registerLead")}</p>
      <form onSubmit={onSubmit} className="mt-8 space-y-5">
        <Field
          label={t("email")}
          name="email"
          type="email"
          inputMode="email"
          required
          maxLength={254}
          autoComplete="email"
        />
        <Field
          label={t("password")}
          name="password"
          type="password"
          required
          minLength={isLogin ? 1 : 10}
          maxLength={128}
          autoComplete={isLogin ? "current-password" : "new-password"}
          hint={isLogin ? undefined : t("passwordHint")}
        />
        {!isLogin && (
          <Field
            label={t("password2")}
            name="password2"
            type="password"
            required
            minLength={10}
            maxLength={128}
            autoComplete="new-password"
          />
        )}
        {error && <Notice tone="error">{error}</Notice>}
        <Button type="submit" size="lg" disabled={busy} className="w-full">
          {t(isLogin ? "loginButton" : "registerButton")}
        </Button>
      </form>
      <p className="mt-8 text-center text-sm text-ink-soft">
        {t(isLogin ? "noAccount" : "haveAccount")}{" "}
        <Link href={isLogin ? "/register" : "/login"} className="font-semibold text-lapis underline-offset-4 hover:underline">
          {t(isLogin ? "toRegister" : "toLogin")}
        </Link>
      </p>
    </main>
  );
}
