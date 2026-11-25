import type { Metadata } from "next";
import type { ReactNode } from "react";

import { RequireAuth } from "@/components/RequireAuth";

import { AdminShell } from "./AdminShell";

// Never indexed. Access is enforced by the API (Telegram id from ADMIN_TELEGRAM_IDS);
// this page shell only hides the UI from everyone else.
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth admin>
      <AdminShell>{children}</AdminShell>
    </RequireAuth>
  );
}
