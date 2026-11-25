import "server-only";

import type { Plan } from "./types";

const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

/** Server-side fetch of public plans (no user data, safe to cache briefly). */
export async function fetchPlans(): Promise<Plan[]> {
  try {
    const res = await fetch(`${API}/api/plans`, { next: { revalidate: 60 } });
    if (!res.ok) return [];
    return (await res.json()) as Plan[];
  } catch {
    return [];
  }
}
