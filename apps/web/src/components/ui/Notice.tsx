import type { ReactNode } from "react";

import { cx } from "./cx";

const tones = {
  error: "border-pomegranate bg-pomegranate-tint text-[#7d1d2c]",
  success: "border-pistachio bg-pistachio-tint text-[#1d5133]",
  info: "border-lapis bg-lapis-tint text-lapis-deep",
};

/** Inline message with a colored left rule. Errors are announced to screen readers. */
export function Notice({
  tone = "info",
  children,
  className,
}: {
  tone?: keyof typeof tones;
  children: ReactNode;
  className?: string;
}) {
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={cx("rounded-r-md border-l-4 px-4 py-3 text-sm", tones[tone], className)}
    >
      {children}
    </p>
  );
}
