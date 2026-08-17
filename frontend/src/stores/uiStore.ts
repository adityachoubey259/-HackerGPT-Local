import { create } from "zustand";

interface UiStore {
  sidebarCollapsed: boolean;
  mobileSidebarOpen: boolean;
  inspectorCollapsed: boolean;
  commandPaletteOpen: boolean;
  toggleSidebar: () => void;
  openMobileSidebar: () => void;
  closeMobileSidebar: () => void;
  toggleInspector: () => void;
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  toggleCommandPalette: () => void;
}

export const useUiStore = create<UiStore>((set) => ({
  sidebarCollapsed: false,
  mobileSidebarOpen: false,
  inspectorCollapsed: false,
  commandPaletteOpen: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  openMobileSidebar: () => set({ mobileSidebarOpen: true }),
  closeMobileSidebar: () => set({ mobileSidebarOpen: false }),
  toggleInspector: () => set((state) => ({ inspectorCollapsed: !state.inspectorCollapsed })),
  openCommandPalette: () => set({ commandPaletteOpen: true }),
  closeCommandPalette: () => set({ commandPaletteOpen: false }),
  toggleCommandPalette: () =>
    set((state) => ({ commandPaletteOpen: !state.commandPaletteOpen }))
}));
