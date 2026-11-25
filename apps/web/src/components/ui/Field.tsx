import { useId, type InputHTMLAttributes } from "react";

import { cx } from "./cx";

export const inputClass =
  "h-12 w-full rounded-md border border-line bg-surface px-4 text-base text-ink placeholder:text-ink-soft/60 transition-colors focus:border-lapis focus:outline-none focus:ring-4 focus:ring-lapis/15 aria-[invalid=true]:border-pomegranate";

export function Field({
  label,
  hint,
  error,
  className,
  ...input
}: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string }) {
  const id = useId();
  const describedBy = hint || error ? `${id}-desc` : undefined;
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium text-ink">
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={inputClass}
        {...input}
      />
      {(hint || error) && (
        <p
          id={describedBy}
          className={cx("mt-1.5 text-xs", error ? "text-pomegranate" : "text-ink-soft")}
        >
          {error ?? hint}
        </p>
      )}
    </div>
  );
}
