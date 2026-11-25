import type { ReactNode } from "react";

import { Ikat, cx } from "@/components/ui";

/**
 * The subscription pass: the one bold element of the brand.
 * Lapis card with an atlas-silk edge. Used on the home page (preview) and in the cabinet.
 */
export function Pass({
  big,
  bigLabel,
  lines,
  badge,
  aside,
  footer,
  animate = false,
  className,
}: {
  big: ReactNode;
  bigLabel: string;
  lines: ReactNode[];
  badge?: ReactNode;
  aside?: ReactNode;
  footer?: ReactNode;
  animate?: boolean;
  className?: string;
}) {
  return (
    <article
      className={cx(
        "relative flex overflow-hidden rounded-pass bg-lapis-deep text-white shadow-[0_24px_48px_-24px_rgb(var(--c-lapis-deep)/0.7)]",
        className,
      )}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-6 p-6 sm:p-8">
        <div className="flex items-center justify-between gap-3">
          <span className="font-display text-lg font-extrabold tracking-display">Payvast</span>
          {badge}
        </div>
        <div className="flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="tabular font-display text-5xl font-black leading-none tracking-display sm:text-[5rem]">
              {big}
            </p>
            <p className="mt-2 text-lg text-white/80">{bigLabel}</p>
            <ul className="mt-4 space-y-1 text-sm text-white/75">
              {lines.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </div>
          {aside}
        </div>
        {footer}
      </div>
      <div className={cx("relative w-9 shrink-0 sm:w-12", animate && "animate-unroll")}>
        <Ikat className="absolute inset-0 h-full w-full" />
      </div>
    </article>
  );
}
