import { create } from "zustand";

export type ThemePreference = "light" | "dark" | "system";

const storageKey = "hackergpt-theme";

interface ThemeStore {
  preference: ThemePreference;
  resolvedTheme: "light" | "dark";
  setPreference: (preference: ThemePreference) => void;
}

function resolveTheme(preference: ThemePreference): "light" | "dark" {
  if (preference === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return preference;
}

function applyTheme(preference: ThemePreference): "light" | "dark" {
  const resolved = resolveTheme(preference);
  document.documentElement.dataset.theme = resolved;
  document.documentElement.classList.toggle("dark", resolved === "dark");
  window.localStorage.setItem(storageKey, preference);
  return resolved;
}

function readInitialPreference(): ThemePreference {
  const saved = window.localStorage.getItem(storageKey);
  return saved === "light" || saved === "dark" || saved === "system" ? saved : "system";
}

const initialPreference = readInitialPreference();

export const useThemeStore = create<ThemeStore>((set) => ({
  preference: initialPreference,
  resolvedTheme: applyTheme(initialPreference),
  setPreference: (preference) => {
    const resolvedTheme = applyTheme(preference);
    set({ preference, resolvedTheme });
  }
}));
