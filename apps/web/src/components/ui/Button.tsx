import type { ButtonHTMLAttributes, ComponentProps } from "react";

import { Link } from "@/i18n/routing";

import { cx } from "./cx";

export type ButtonTone = "primary" | "quiet" | "danger" | "success" | "inverse";
export type ButtonSize = "md" | "lg" | "sm";

const base =
  "inline-flex select-none items-center justify-center gap-2 rounded-md font-semibold transition-[background-color,transform,box-shadow] duration-150 active:translate-y-px disabled:pointer-events-none disabled:opacity-55";

const tones: Record<ButtonTone, string> = {
  primary: "bg-lapis text-white shadow-[0_1px_0_rgb(var(--c-lapis-deep))] hover:bg-lapis-deep",
  quiet: "border border-line bg-surface text-ink hover:border-lapis hover:text-lapis",
  danger: "bg-pomegranate text-white hover:brightness-95",
  success: "bg-pistachio text-white hover:brightness-95",
  inverse: "bg-white text-lapis-deep hover:bg-lapis-tint",
};

const sizes: Record<ButtonSize, string> = {
  sm: "h-9 px-3 text-sm",
  md: "h-11 px-5 text-base",
  lg: "h-14 px-7 text-lg",
};

export function buttonClass(tone: ButtonTone = "primary", size: ButtonSize = "md", extra?: string) {
  return cx(base, tones[tone], sizes[size], extra);
}

export function Button({
  tone = "primary",
  size = "md",
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: ButtonTone; size?: ButtonSize }) {
  return <button type={type} className={buttonClass(tone, size, className)} {...props} />;
}

export function ButtonLink({
  tone = "primary",
  size = "md",
  className,
  ...props
}: ComponentProps<typeof Link> & { tone?: ButtonTone; size?: ButtonSize }) {
  return <Link className={buttonClass(tone, size, className)} {...props} />;
}
