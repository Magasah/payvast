"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button, type ButtonTone } from "@/components/ui/Button";

export function CopyButton({
  value,
  tone = "quiet",
  className,
}: {
  value: string;
  tone?: ButtonTone;
  className?: string;
}) {
  const t = useTranslations("common");
  const [copied, setCopied] = useState(false);
  return (
    <Button
      size="sm"
      tone={tone}
      className={className}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1800);
        } catch {
          /* clipboard blocked: the value stays selectable */
        }
      }}
      aria-live="polite"
    >
      {copied ? t("copied") : t("copy")}
    </Button>
  );
}
