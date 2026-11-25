"use client";

import type { TokenResponse, User } from "./types";

/**
 * Browser API client.
 * - Access token lives only in memory (never localStorage: not readable by injected scripts
 *   after reload, and it expires in 15 minutes anyway).
 * - Refresh token is an httpOnly SameSite=Strict cookie the browser sends to /api/auth/*.
 * - All requests go to the same origin (/api/*); Next.js proxies them to FastAPI.
 */

let accessToken: string | null = null;
let refreshing: Promise<User | null> | null = null;
const listeners = new Set<(user: User | null) => void>();

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
  ) {
    super(code);
  }
}

function setSession(data: TokenResponse | null): User | null {
  accessToken = data?.access_token ?? null;
  const user = data?.user ?? null;
  listeners.forEach((fn) => fn(user));
  return user;
}

export function onAuthChange(fn: (user: User | null) => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

async function parseError(res: Response): Promise<ApiError> {
  let code = "error";
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (typeof body.detail === "string") code = body.detail;
    else if (Array.isArray(body.detail)) code = "validation_error";
  } catch {
    /* non-JSON error body */
  }
  if (res.status === 429) code = "rate_limited";
  return new ApiError(res.status, code);
}

/** Try to restore the session from the refresh cookie. Deduplicates parallel calls. */
export function refreshSession(): Promise<User | null> {
  refreshing ??= (async () => {
    try {
      const res = await fetch("/api/auth/refresh", { method: "POST", credentials: "same-origin" });
      return setSession(res.ok ? ((await res.json()) as TokenResponse) : null);
    } catch {
      return setSession(null);
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

async function raw(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return fetch(path, { ...init, headers, credentials: "same-origin" });
}

/** Authenticated request with one transparent refresh on 401. */
export async function request(path: string, init: RequestInit = {}): Promise<Response> {
  let res = await raw(path, init);
  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    if (await refreshSession()) res = await raw(path, init);
  }
  if (!res.ok) throw await parseError(res);
  return res;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const res = await request(path, { ...init, headers });
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export async function login(email: string, password: string): Promise<User> {
  const data = await api<TokenResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  return setSession(data) as User;
}

export async function register(email: string, password: string, locale: string): Promise<User> {
  const data = await api<TokenResponse>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, locale }),
  });
  return setSession(data) as User;
}

export async function logout(): Promise<void> {
  try {
    await fetch("/api/auth/logout", { method: "POST", credentials: "same-origin" });
  } finally {
    setSession(null);
  }
}

/** Fetch an authenticated image (QR, receipt) as an object URL for <img src>. */
export async function imageUrl(path: string): Promise<string> {
  const res = await request(path);
  return URL.createObjectURL(await res.blob());
}
