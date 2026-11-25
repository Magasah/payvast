import { formatSomoni, planName } from "@/lib/format";
import type { Plan } from "@/lib/types";

export function PlanCard({
  plan,
  locale,
  labels,
  action,
  highlighted = false,
}: {
  plan: Plan;
  locale: string;
  labels: { days: string; devices: string };
  action?: React.ReactNode;
  highlighted?: boolean;
}) {
  return (
    <div
      className={`flex flex-col rounded-xl border bg-white p-6 shadow-sm ${
        highlighted ? "border-brand-500 ring-2 ring-brand-100" : "border-slate-200"
      }`}
    >
      <h3 className="text-lg font-semibold">{planName(plan, locale)}</h3>
      <p className="mt-3 text-3xl font-bold text-brand-700">
        {formatSomoni(plan.price_dirams, locale)}
      </p>
      <ul className="mt-4 space-y-1 text-sm text-slate-600">
        <li>
          {plan.duration_days} {labels.days}
        </li>
        <li>
          {labels.devices}: {plan.device_limit}
        </li>
      </ul>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
