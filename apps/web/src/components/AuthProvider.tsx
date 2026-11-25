"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { onAuthChange, refreshSession } from "@/lib/api";
import type { User } from "@/lib/types";

interface AuthState {
  user: User | null;
  ready: boolean;
}

const AuthContext = createContext<AuthState>({ user: null, ready: false });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ user: null, ready: false });

  useEffect(() => {
    const off = onAuthChange((user) => setState({ user, ready: true }));
    void refreshSession();
    return off;
  }, []);

  return <AuthContext.Provider value={state}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}
