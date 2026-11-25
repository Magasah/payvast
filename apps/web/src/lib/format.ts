export function formatSomoni(dirams: number, locale: string): string {
  const value = (dirams / 100).toLocaleString("ru-RU", {
    minimumFractionDigits: dirams % 100 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  });
  return `${value} ${locale === "ru" ? "сомони" : "сомонӣ"}`;
}

// Browsers often ship without Tajik locale data (they fall back to English),
// so Tajik month names are spelled out here.
const TG_MONTHS = [
  "январ", "феврал", "март", "апрел", "май", "июн",
  "июл", "август", "сентябр", "октябр", "ноябр", "декабр",
];

export function formatDate(iso: string, locale: string): string {
  const date = new Date(iso);
  if (locale === "tg") {
    return `${date.getDate()} ${TG_MONTHS[date.getMonth()]}и ${date.getFullYear()}`;
  }
  return date.toLocaleDateString("ru-RU", { year: "numeric", month: "long", day: "numeric" });
}

export function planName(plan: { name_tg: string; name_ru: string }, locale: string): string {
  return locale === "ru" ? plan.name_ru : plan.name_tg;
}

/** Short display name for a user in the admin area. */
export function userTitle(
  u: { telegram_username: string | null; email: string | null; telegram_id?: number | null },
  fallback: string,
): string {
  if (u.telegram_username) return `@${u.telegram_username}`;
  return u.email ?? (u.telegram_id ? `tg ${u.telegram_id}` : fallback);
}

export function formatDateTime(iso: string, locale: string): string {
  const d = new Date(iso);
  const time = d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  return `${formatDate(iso, locale)}, ${time}`;
}
