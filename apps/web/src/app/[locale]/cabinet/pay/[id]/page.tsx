import type { Metadata } from "next";
import { setRequestLocale } from "next-intl/server";

import { RequireAuth } from "@/components/RequireAuth";

import { PayFlow } from "./PayFlow";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function PayPage({ params }: { params: { locale: string; id: string } }) {
  setRequestLocale(params.locale);
  return (
    <RequireAuth>
      <PayFlow paymentId={params.id} />
    </RequireAuth>
  );
}
