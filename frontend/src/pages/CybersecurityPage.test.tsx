import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { CybersecurityPage } from "./CybersecurityPage";
import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";

describe("CybersecurityPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows security posture and runs read-only static review", async () => {
    const fetchSpy = mockFetch((url, init) => {
      if (url.includes("/api/v1/security/dashboard")) {
        return jsonResponse({
          modes: ["general-security", "secure-code-review"],
          scope_types: ["localhost", "configured_repository"],
          severity_levels: ["info", "low", "medium", "high", "critical"],
          confidence_levels: ["low", "medium", "high"],
          policy_scopes: [],
          workspace_count: 1,
          scope_count: 0,
          finding_count: 0
        });
      }
      if (url.includes("/api/v1/security/workspaces")) {
        return jsonResponse({
          items: [
            {
              id: "ws-1",
              name: "Local Security Lab",
              mode: "general-security",
              description: "Authorized local security workspace.",
              active_scope_id: null,
              enabled: true,
              metadata: {},
              created_at: "2026-08-10T00:00:00Z",
              updated_at: "2026-08-10T00:00:00Z"
            }
          ]
        });
      }
      if (url.includes("/api/v1/security/static-review") && init?.method === "POST") {
        return jsonResponse({
          findings: [
            {
              title: "Possible hardcoded secret",
              severity: "high",
              confidence: "medium",
              category: "secrets",
              affected_asset: "backend/sample.py",
              evidence: "line 1: API_KEY = 'abc123abc123'",
              remediation: "Move secrets to environment variables.",
              cwe: "CWE-798"
            }
          ],
          persisted: 0,
          scanned_files: 1,
          skipped_files: 0,
          diagnostics: {}
        });
      }
      if (url.includes("/api/v1/security/scopes")) {
        return jsonResponse({ items: [] });
      }
      if (url.includes("/api/v1/security/findings")) {
        return jsonResponse({ items: [], total: 0 });
      }
      if (url.includes("/api/v1/security/notes")) {
        return jsonResponse({ items: [] });
      }
      return jsonResponse({});
    });

    renderApp(<CybersecurityPage />);
    expect(await screen.findByRole("heading", { name: "Ethical Hacking Workspace" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Review" }));

    await screen.findByText("Possible hardcoded secret");
    await waitFor(() =>
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/security/static-review"),
        expect.objectContaining({ method: "POST" })
      )
    );
  });
});
