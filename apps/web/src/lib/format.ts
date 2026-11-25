export function formatSomoni(dirams: number, locale: string): string {
  const value = (dirams / 100).toLocaleString(locale === "ru" ? "ru-RU" : "tg-TJ", {
    minimumFractionDigits: dirams % 100 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  });
  return `${value} ${locale === "ru" ? "сомони" : "сомонӣ"}`;
}

export function formatDate(iso: string, locale: string): string {
  return new Date(iso).toLocaleDateString(locale === "ru" ? "ru-RU" : "tg-TJ", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

export function planName(plan: { name_tg: string; name_ru: string }, locale: string): string {
  return locale === "ru" ? plan.name_ru : plan.name_tg;
}
