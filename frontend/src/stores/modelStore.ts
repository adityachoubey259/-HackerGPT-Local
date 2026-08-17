import { create } from "zustand";

import type { NormalizedModel, ProviderHealth } from "../types/api";

interface ModelStore {
  selectedProvider: string | null;
  selectedModel: string | null;
  providers: ProviderHealth[];
  models: NormalizedModel[];
  setProviders: (providers: ProviderHealth[]) => void;
  setModels: (models: NormalizedModel[]) => void;
  selectModel: (provider: string, model: string) => void;
}

export const useModelStore = create<ModelStore>((set) => ({
  selectedProvider: null,
  selectedModel: null,
  providers: [],
  models: [],
  setProviders: (providers) => set({ providers }),
  setModels: (models) => set({ models }),
  selectModel: (provider, model) => set({ selectedProvider: provider, selectedModel: model })
}));
