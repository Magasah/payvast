import type { Tone } from "@/components/ui/Badge";

import type { PaymentStatus, Subscription } from "./types";

export const SUB_TONE: Record<Subscription["status"], Tone> = {
  active: "pistachio",
  expired: "saffron",
  disabled: "neutral",
};

export const PAYMENT_TONE: Record<PaymentStatus, Tone> = {
  awaiting_receipt: "saffron",
  pending_review: "lapis",
  confirmed: "pistachio",
  rejected: "pomegranate",
};
