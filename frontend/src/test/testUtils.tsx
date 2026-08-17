import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

export function renderApp(ui: ReactElement) {
  return render(ui);
}

export function mockFetch(handler: (url: string, init?: RequestInit) => Response | Promise<Response>) {
  return vi.spyOn(window, "fetch").mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
    const url =
      typeof input === "string" ? input : input instanceof Request ? input.url : input.toString();
    return Promise.resolve(handler(url, init));
  });
}

export function jsonResponse(body: unknown, status = 200, requestId = "test-request-id") {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": requestId
    }
  });
}
