import { create } from "zustand";

import { authApi } from "../api/auth";
import type { AuthUser } from "../types/api";

type AuthStatus = "checking" | "authenticated" | "unauthenticated";

interface AuthStore {
  status: AuthStatus;
  user: AuthUser | null;
  error: string | null;
  restore: () => Promise<void>;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>((set) => ({
  status: "checking",
  user: null,
  error: null,
  restore: async () => {
    set({ status: "checking", error: null });
    try {
      const session = await authApi.me();
      set({
        status: session.authenticated ? "authenticated" : "unauthenticated",
        user: session.user,
        error: null
      });
    } catch {
      set({ status: "unauthenticated", user: null, error: "Authentication check failed." });
    }
  },
  login: async (username, password) => {
    set({ error: null });
    try {
      const session = await authApi.login({ username, password });
      set({
        status: session.authenticated ? "authenticated" : "unauthenticated",
        user: session.user,
        error: null
      });
    } catch (error) {
      set({
        status: "unauthenticated",
        user: null,
        error: error instanceof Error ? error.message : "Login failed."
      });
      throw error;
    }
  },
  logout: async () => {
    try {
      await authApi.logout();
    } finally {
      set({ status: "unauthenticated", user: null, error: null });
    }
  }
}));
