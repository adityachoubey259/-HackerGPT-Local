import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ResearchPage } from "./ResearchPage";
import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";

describe("ResearchPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows policy-offline state and records an explicit offline research run", async () => {
    mockFetch((url, init) => {
      if (url.includes("/api/v1/research/status")) {
        return jsonResponse({
          enabled: false,
          search_enabled: false,
          provider: "searxng",
          configured: false,
          allowed_domains: [],
          blocked_domains: ["169.254.169.254"],
          max_results: 8,
          cache_ttl_seconds: 86400,
          official_sources_preferred: true,
          private_networks_blocked: true
        });
      }
      if (url.includes("/api/v1/research/history")) {
        return jsonResponse({ items: [], total: 0 });
      }
      if (url.includes("/api/v1/research/run") && init?.method === "POST") {
        return jsonResponse({
          session: {
            id: "rs-1",
            query: "latest FastAPI security release notes",
            status: "offline",
            provider: "searxng",
            answer: "Live research is disabled by policy.",
            official_only: false,
            filters: {},
            diagnostics: { reason: "policy_disabled" },
            created_at: "2026-08-10T00:00:00Z",
            updated_at: "2026-08-10T00:00:00Z"
          },
          sources: []
        });
      }
      return jsonResponse({});
    });

    renderApp(<ResearchPage />);
    expect(await screen.findByText("Policy offline")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Run" }));

    expect(await screen.findByText("Live research is disabled by policy.")).toBeInTheDocument();
  });
});
