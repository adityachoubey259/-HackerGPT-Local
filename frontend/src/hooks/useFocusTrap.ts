import { useEffect, type RefObject } from "react";

const focusableSelector = [
  "a[href]",
  "button:not([disabled])",
  "textarea:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  '[tabindex]:not([tabindex="-1"])'
].join(",");

export function useFocusTrap(
  containerRef: RefObject<HTMLElement>,
  active: boolean,
  onEscape: () => void
) {
  useEffect(() => {
    if (!active) {
      return;
    }
    const activeContainer = containerRef.current;
    if (!activeContainer) {
      return;
    }
    const trapContainer: HTMLElement = activeContainer;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    function getFocusable() {
      return Array.from(trapContainer.querySelectorAll<HTMLElement>(focusableSelector)).filter(
        (element) => !element.hasAttribute("disabled") && element.tabIndex !== -1
      );
    }

    window.setTimeout(() => {
      getFocusable()[0]?.focus();
    }, 0);

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onEscape();
        return;
      }
      if (event.key !== "Tab") {
        return;
      }
      const focusable = getFocusable();
      if (focusable.length === 0) {
        event.preventDefault();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previousFocus?.focus();
    };
  }, [active, containerRef, onEscape]);
}
