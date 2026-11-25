"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { Button, type ButtonTone } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";

async function copyText(value: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    // Old WebViews (some Android Telegram builds) have no async clipboard API.
    const area = document.createElement("textarea");
    area.value = value;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  }
}

export function CopyButton({
  value,
  tone = "quiet",
  className,
  label,
}: {
  value: string;
  tone?: ButtonTone;
  className?: string;
  /** Accessible name, e.g. "Copy amount". Defaults to "Copy". */
  label?: string;
}) {
  const t = useTranslations("common");
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => () => clearTimeout(timer.current), []);

  return (
    <Button
      size="sm"
      tone={tone}
      className={className}
      aria-label={label}
      onClick={async () => {
        if (await copyText(value)) {
          setCopied(true);
          clearTimeout(timer.current);
          timer.current = setTimeout(() => setCopied(false), 1800);
        }
      }}
    >
      <Icon name={copied ? "check" : "copy"} size={16} />
      <span aria-live="polite">{copied ? t("copied") : t("copy")}</span>
    </Button>
  );
}
