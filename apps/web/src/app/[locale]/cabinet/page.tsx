import { setRequestLocale } from "next-intl/server";

import { RequireAuth } from "@/components/RequireAuth";

import { Cabinet } from "./Cabinet";

export default function CabinetPage({ params: { locale } }: { params: { locale: string } }) {
  setRequestLocale(locale);
  return (
    <RequireAuth>
      <Cabinet />
    </RequireAuth>
  );
}
