export type Role = "user" | "admin";

export interface User {
  id: string;
  email: string | null;
  telegram_username: string | null;
  has_telegram: boolean;
  role: Role;
  is_admin: boolean;
  locale: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}

export interface Plan {
  id: number;
  code: string;
  name_tg: string;
  name_ru: string;
  price_dirams: number;
  duration_days: number;
  device_limit: number;
}

export type PaymentMethod = "alif" | "dushanbe_city" | "card";
export type PaymentStatus = "awaiting_receipt" | "pending_review" | "confirmed" | "rejected";

export type BankCode = "alif" | "dc" | "sber" | "tbank";

export interface PaymentMethodInfo {
  method: PaymentMethod;
  account_kind: "phone" | "card";
  account: string;
  recipient: string;
  fee_percent: number;
  banks: { code: BankCode; url: string }[];
}

export interface Payment {
  id: string;
  plan_id: number;
  method: PaymentMethod;
  amount_dirams: number;
  duration_days: number;
  status: PaymentStatus;
  has_receipt: boolean;
  reject_reason: string | null;
  created_at: string;
  confirmed_at: string | null;
}

export interface Subscription {
  id: string;
  status: "active" | "expired" | "disabled";
  expires_at: string;
  days_left: number;
  device_limit: number;
  subscription_url: string | null;
}

export type SubStatus = Subscription["status"];

export interface AdminPayment {
  id: string;
  user_id: string;
  user_email: string | null;
  user_telegram: string | null;
  plan_code: string;
  method: PaymentMethod;
  amount_dirams: number;
  duration_days: number;
  status: PaymentStatus;
  has_receipt: boolean;
  created_at: string;
  reviewed_at: string | null;
  reject_reason: string | null;
}

export interface AdminSubscription {
  id: string;
  status: SubStatus;
  expires_at: string;
  days_left: number;
  device_limit: number;
  server_id: number | null;
  subscription_url: string;
}

export interface AdminUserRow {
  id: string;
  email: string | null;
  telegram_id: number | null;
  telegram_username: string | null;
  is_admin: boolean;
  is_active: boolean;
  locale: string;
  created_at: string;
  subscription_status: SubStatus | null;
  expires_at: string | null;
}

export interface AdminUserDetail {
  user: AdminUserRow;
  subscription: AdminSubscription | null;
  payments: AdminPayment[];
}

export interface AuditEntry {
  id: number;
  created_at: string;
  admin: string | null;
  action: string;
  target_type: string;
  target_id: string;
  details: Record<string, unknown>;
}
