import { create } from "zustand";

import { preferencesApi } from "../api/preferences";
import type { UserPreferences, UserPreferencesPatch } from "../types/api";

type PreferenceStatus = "idle" | "loading" | "ready" | "saving" | "error";

interface PreferenceState {
  preferences: UserPreferences | null;
  status: PreferenceStatus;
  error: string | null;
  load: () => Promise<void>;
  save: (patch: UserPreferencesPatch) => Promise<UserPreferences>;
}

export const usePreferenceStore = create<PreferenceState>((set, get) => ({
  preferences: null,
  status: "idle",
  error: null,
  async load() {
    if (get().status === "loading") {
      return;
    }
    set({ status: "loading", error: null });
    try {
      const preferences = await preferencesApi.get();
      set({ preferences, status: "ready", error: null });
    } catch (error) {
      set({ status: "error", error: error instanceof Error ? error.message : "Preferences failed" });
    }
  },
  async save(patch) {
    set({ status: "saving", error: null });
    try {
      const preferences = await preferencesApi.patch(patch);
      set({ preferences, status: "ready", error: null });
      return preferences;
    } catch (error) {
      const message = error instanceof Error ? error.message : "Preferences failed";
      set({ status: "error", error: message });
      throw error;
    }
  }
}));
