/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "rgb(var(--color-background) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        panel: "rgb(var(--color-panel) / <alpha-value>)",
        elevated: "rgb(var(--color-elevated) / <alpha-value>)",
        floating: "rgb(var(--color-floating) / <alpha-value>)",
        sidebar: "rgb(var(--color-sidebar) / <alpha-value>)",
        border: "rgb(var(--color-border) / <alpha-value>)",
        "border-subtle": "rgb(var(--color-border-subtle) / <alpha-value>)",
        text: "rgb(var(--color-text) / <alpha-value>)",
        secondary: "rgb(var(--color-secondary) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        accent: "rgb(var(--color-accent) / <alpha-value>)",
        "accent-hover": "rgb(var(--color-accent-hover) / <alpha-value>)",
        selection: "rgb(var(--color-selection) / <alpha-value>)",
        focus: "rgb(var(--color-focus) / <alpha-value>)",
        info: "rgb(var(--color-info) / <alpha-value>)",
        positive: "rgb(var(--color-positive) / <alpha-value>)",
        warning: "rgb(var(--color-warning) / <alpha-value>)",
        danger: "rgb(var(--color-danger) / <alpha-value>)"
      },
      boxShadow: {
        soft: "var(--shadow-soft)",
        popover: "var(--shadow-popover)"
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.125rem"
      },
      transitionTimingFunction: {
        standard: "var(--ease-standard)",
        emphasized: "var(--ease-emphasized)"
      },
      zIndex: {
        shell: "20",
        overlay: "40",
        modal: "50",
        toast: "60"
      }
    }
  },
  plugins: []
};
