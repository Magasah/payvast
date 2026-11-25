import type { ReactNode } from "react";

import { cx } from "./cx";

export type Tone = "lapis" | "pistachio" | "saffron" | "pomegranate" | "neutral";

const tones: Record<Tone, string> = {
  lapis: "bg-lapis-tint text-lapis-deep",
  pistachio: "bg-pistachio-tint text-pistachio",
  saffron: "bg-saffron-tint text-[#8a560c]",
  pomegranate: "bg-pomegranate-tint text-pomegranate",
  neutral: "bg-paper text-ink-soft",
};

const dots: Record<Tone, string> = {
  lapis: "bg-lapis",
  pistachio: "bg-pistachio",
  saffron: "bg-saffron",
  pomegranate: "bg-pomegranate",
  neutral: "bg-ink-soft",
};

export function Badge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-sm px-2 py-0.5 text-xs font-semibold",
        tones[tone],
      )}
    >
      <span aria-hidden className={cx("h-1.5 w-1.5 rounded-full", dots[tone])} />
      {children}
    </span>
  );
}
