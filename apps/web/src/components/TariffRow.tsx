import type { ReactNode } from "react";

import { cx } from "@/components/ui";
import { formatSomoni, planName } from "@/lib/format";
import type { Plan } from "@/lib/types";

export interface TariffLabels {
  perMonth: string;
  devices: (n: number) => string;
  days: (n: number) => string;
}

/**
 * One tariff as a row of a price list (not a card): duration is the headline,
 * because that is what people compare first.
 */
export function TariffRow({
  plan,
  locale,
  labels,
  action,
  selected,
  compactAction = false,
}: {
  plan: Plan;
  locale: string;
  labels: TariffLabels;
  action?: ReactNode;
  selected?: boolean;
  /** Small control (radio): stays on the row's right edge on phones too. */
  compactAction?: boolean;
}) {
  const months = Math.max(1, Math.round(plan.duration_days / 30));
  const perMonth = Math.round(plan.price_dirams / months / 100) * 100;
  const [count, ...unit] = planName(plan, locale).split(" ");
  return (
    <div
      className={cx(
        "grid items-center gap-x-4 gap-y-3 px-5 py-5 sm:grid-cols-[6rem_1fr_auto] sm:gap-x-8 sm:px-7",
        compactAction ? "grid-cols-[4.5rem_1fr_auto]" : "grid-cols-[4.5rem_1fr]",
        selected && "bg-lapis-tint",
      )}
    >
      <p className={cx("font-display leading-none tracking-display sm:row-span-1", !compactAction && "row-span-2")}>
        <span className="tabular block text-4xl font-black text-lapis sm:text-5xl">{count}</span>
        <span className="text-sm font-bold text-ink-soft">{unit.join(" ")}</span>
      </p>
      <div>
        <p className="tabular text-xl font-semibold">{formatSomoni(plan.price_dirams, locale)}</p>
        <p className="text-sm text-ink-soft">
          {months > 1 && (
            <>
              {formatSomoni(perMonth, locale)} {labels.perMonth}
              <br />
            </>
          )}
          {labels.days(plan.duration_days)}, {labels.devices(plan.device_limit)}
        </p>
      </div>
      {action && (
        <div className={compactAction ? undefined : "col-start-2 sm:col-start-auto"}>{action}</div>
      )}
    </div>
  );
}
