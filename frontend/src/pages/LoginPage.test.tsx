import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { LoginPage } from "./LoginPage";
import { useAuthStore } from "../stores/authStore";
import { jsonResponse, mockFetch, renderApp } from "../test/testUtils";

describe("LoginPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    useAuthStore.setState({ status: "checking", user: null, error: null });
  });

  it("renders local bootstrap login affordance", async () => {
    mockFetch(() => jsonResponse({ authenticated: false, user: null }));

    renderApp(
      <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
        <LoginPage />
      </MemoryRouter>
    );

    expect(screen.getByText("HackerGPT Local")).toBeInTheDocument();
    expect(screen.getByText(/admin \/ admin987/i)).toBeInTheDocument();
    await waitFor(() => expect(useAuthStore.getState().status).toBe("unauthenticated"));
  });

  it("submits credentials through the backend auth API", async () => {
    const calls: string[] = [];
    mockFetch((url) => {
      calls.push(url);
      if (url.includes("/api/v1/auth/login")) {
        return jsonResponse({
          authenticated: true,
          user: {
            id: "local-user",
            username: "admin",
            display_name: "Local Admin",
            role: "admin",
            is_bootstrap: true
          }
        });
      }
      return jsonResponse({ authenticated: false, user: null });
    });

    renderApp(
      <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
        <LoginPage />
      </MemoryRouter>
    );
    await userEvent.type(screen.getByLabelText(/password/i), "admin987");
    await userEvent.click(screen.getByRole("button", { name: /enter workstation/i }));

    await waitFor(() => expect(useAuthStore.getState().status).toBe("authenticated"));
    expect(calls.some((url) => url.includes("/api/v1/auth/login"))).toBe(true);
  });
});
