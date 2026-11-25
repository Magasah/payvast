import type { HTMLAttributes } from "react";

import { cx } from "./cx";

/** Flat white surface. No shadow: hierarchy comes from spacing and type, not elevation. */
export function Panel({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={cx("rounded-lg border border-line bg-surface p-5 sm:p-7", className)}
      {...props}
    />
  );
}
