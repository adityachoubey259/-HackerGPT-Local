import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
});

Object.defineProperty(navigator, "clipboard", {
  writable: true,
  value: {
    writeText: (text: string) => {
      window.localStorage.setItem("test-clipboard", text);
      return Promise.resolve();
    }
  }
});
