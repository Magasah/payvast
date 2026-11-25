export type Role = "user" | "admin";

export interface User {
  id: string;
  email: string;
  role: Role;
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

export type PaymentMethod = "alif" | "dushanbe_city";
export type PaymentStatus = "awaiting_receipt" | "pending_review" | "confirmed" | "rejected";

export interface PaymentMethodInfo {
  method: PaymentMethod;
  wallet: string;
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

export interface AdminPayment {
  id: string;
  user_email: string;
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
