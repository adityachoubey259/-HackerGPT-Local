import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          markdown: ["react-markdown", "rehype-sanitize", "remark-gfm"],
          icons: ["lucide-react"]
        }
      }
    }
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
    css: true,
    testTimeout: 15000
  }
});
