import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SettingsPage } from "./SettingsPage";
import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";

describe("SettingsPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders safe config and persists response preferences", async () => {
    const fetchMock = mockFetch((url, init) => {
      if (url.endsWith("/api/v1/preferences") && init?.method === "PATCH") {
        return jsonResponse({
          response_mode: "standard",
          technical_depth: "expert",
          default_agent: "expert",
          intelligence_mode: "auto",
          reasoning_mode: "auto",
          theme: "system"
        });
      }
      if (url.endsWith("/api/v1/preferences")) {
        return jsonResponse({
          response_mode: "direct_expert",
          technical_depth: "expert",
          default_agent: "expert",
          intelligence_mode: "auto",
          reasoning_mode: "auto",
          theme: "system"
        });
      }
      return jsonResponse({
        environment: "test",
        debug: true,
        network_access: false,
        api: { allowed_origins: ["http://localhost:5173"] },
        model_endpoint: {
          base_url: "http://127.0.0.1:11434",
          cloud_inference_enabled: false
        },
        response: {
          default_mode: "direct_expert",
          directness: "high",
          technical_depth: "expert",
          assume_technical_user: true,
          generic_disclaimers: false,
          moralizing: false,
          shallow_keyword_filtering: false,
          prefer_complete_code: true,
          prefer_exact_commands: true,
          verify_current_information: true,
          investigate_before_unknown: true,
          cite_retrieved_sources: true
        }
      });
    });

    renderApp(<SettingsPage />);
    await waitFor(() => expect(screen.getByText("test")).toBeInTheDocument());

    expect(screen.getByDisplayValue("Direct Expert")).toBeInTheDocument();
    expect(screen.queryByText(/api_key/i)).not.toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Response mode"), "standard");

    await waitFor(() => expect(screen.getByText("Saved.")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/preferences",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ response_mode: "standard" })
      })
    );
  });

  it("submits change-password through the backend auth API", async () => {
    mockFetch((url) => {
      if (url.endsWith("/api/v1/auth/change-password")) {
        return jsonResponse({ authenticated: true, user: null });
      }
      if (url.endsWith("/api/v1/preferences")) {
        return jsonResponse({
          response_mode: "direct_expert",
          technical_depth: "expert",
          default_agent: "expert",
          intelligence_mode: "auto",
          reasoning_mode: "auto",
          theme: "system"
        });
      }
      return jsonResponse({
        environment: "test",
        debug: true,
        network_access: false,
        api: {},
        model_endpoint: { cloud_inference_enabled: false },
        response: {
          default_mode: "direct_expert",
          directness: "high",
          technical_depth: "expert",
          assume_technical_user: true,
          generic_disclaimers: false,
          moralizing: false,
          shallow_keyword_filtering: false,
          prefer_complete_code: true,
          prefer_exact_commands: true,
          verify_current_information: true,
          investigate_before_unknown: true,
          cite_retrieved_sources: true
        }
      });
    });

    renderApp(<SettingsPage />);
    await userEvent.type(screen.getByLabelText("Current password"), "admin987");
    await userEvent.type(screen.getByLabelText("New password"), "admin987-new");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "admin987-new");
    await userEvent.click(screen.getByRole("button", { name: /update password/i }));

    await waitFor(() =>
      expect(screen.getByText(/existing old-session cookies are invalidated/i)).toBeInTheDocument()
    );
  });
});
