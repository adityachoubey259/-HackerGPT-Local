import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";
import { PromptLabPage } from "./PromptLabPage";

describe("PromptLabPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads profiles and renders generated prompt output", async () => {
    mockFetch((url) => {
      if (url.includes("/profiles")) {
        return jsonResponse([
          {
            id: "react-frontend",
            label: "React Frontend",
            prompt_type: "frontend",
            domains: ["ui"],
            languages: ["typescript"],
            default_agent: "engineer",
            recommended_capabilities: ["coding"],
            required_context_sources: ["project"],
            checklist: ["Check responsive behavior"]
          },
          {
            id: "ethical-hacking-lab",
            label: "Ethical Hacking Lab",
            prompt_type: "ethical_hacking_lab",
            domains: ["ethical-hacking"],
            languages: ["bash"],
            default_agent: "cybersecurity",
            recommended_capabilities: ["security"],
            required_context_sources: ["project"],
            checklist: ["Use active authorized scope"]
          }
        ]);
      }
      return jsonResponse({
        optimized_prompt: "Objective: Build a premium local settings panel",
        system_prompt: "You are an expert prompt architect.",
        structured_output_schema: null,
        recommended_agent: "engineer",
        recommended_model_capability: "coding",
        recommended_context_sources: ["system", "agent", "project"],
        assumptions: ["Manual user model choice remains available."],
        profile: null
      });
    });

    renderApp(<PromptLabPage />);
    await waitFor(() => expect(screen.getByText("React Frontend")).toBeInTheDocument());
    expect(screen.getAllByText("Ethical Hacking Lab").length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole("button", { name: /generate prompt/i }));
    await waitFor(() =>
      expect(screen.getByText("Objective: Build a premium local settings panel")).toBeInTheDocument()
    );
    expect(screen.getByText("Manual user model choice remains available.")).toBeInTheDocument();
  });
});
