import { useCallback, useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import {
  BrainCircuit,
  CheckCircle2,
  KeyRound,
  LogOut,
  MonitorCog,
  Palette,
  ShieldCheck,
  UserRound
} from "lucide-react";

import { authApi } from "../api/auth";
import { systemApi } from "../api/system";
import { Card } from "../components/ui/Card";
import { Input, Select } from "../components/ui/Form";
import { Spinner } from "../components/ui/Spinner";
import { useAsyncResource } from "../hooks/useAsyncResource";
import { useAgentStore } from "../stores/agentStore";
import { useAuthStore } from "../stores/authStore";
import { usePreferenceStore } from "../stores/preferenceStore";
import { useThemeStore, type ThemePreference } from "../stores/themeStore";
import type {
  IntelligenceMode,
  ReasoningMode,
  ResponseMode,
  TechnicalDepth,
  UserPreferencesPatch
} from "../types/api";

export function SettingsPage() {
  const themePreference = useThemeStore((state) => state.preference);
  const setThemePreference = useThemeStore((state) => state.setPreference);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const agents = useAgentStore((state) => state.agents);
  const selectedAgentId = useAgentStore((state) => state.selectedAgentId);
  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId);
  const preferences = usePreferenceStore((state) => state.preferences);
  const preferenceStatus = usePreferenceStore((state) => state.status);
  const preferenceError = usePreferenceStore((state) => state.error);
  const loadPreferences = usePreferenceStore((state) => state.load);
  const savePreferences = usePreferenceStore((state) => state.save);
  const [preferenceMessage, setPreferenceMessage] = useState<string | null>(null);
  const [passwordState, setPasswordState] = useState({
    current: "",
    next: "",
    confirm: "",
    status: "idle" as "idle" | "saving" | "success" | "error",
    message: ""
  });
  const config = useAsyncResource(useCallback((signal) => systemApi.publicConfig(signal), []));

  useEffect(() => {
    void loadPreferences();
  }, [loadPreferences]);

  const updatePreferences = async (patch: UserPreferencesPatch) => {
    setPreferenceMessage(null);
    try {
      const updated = await savePreferences(patch);
      if (patch.theme) {
        setThemePreference(updated.theme);
      }
      setPreferenceMessage("Saved.");
    } catch (error) {
      setPreferenceMessage(error instanceof Error ? error.message : "Preference update failed.");
    }
  };

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (passwordState.next !== passwordState.confirm) {
      setPasswordState((state) => ({
        ...state,
        status: "error",
        message: "New password confirmation does not match."
      }));
      return;
    }
    setPasswordState((state) => ({ ...state, status: "saving", message: "" }));
    try {
      await authApi.changePassword({
        current_password: passwordState.current,
        new_password: passwordState.next
      });
      setPasswordState({
        current: "",
        next: "",
        confirm: "",
        status: "success",
        message: "Password changed. Existing old-session cookies are invalidated."
      });
    } catch (error) {
      setPasswordState((state) => ({
        ...state,
        status: "error",
        message: error instanceof Error ? error.message : "Password change failed."
      }));
    }
  };

  return (
    <div className="space-y-5 p-6">
      <header className="max-w-3xl">
        <div className="text-xs font-medium uppercase tracking-[0.16em] text-accent">
          Local preferences
        </div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          User preferences are persisted locally. Execution policy, tool scopes, network rules, and
          audit controls remain backend-owned.
        </p>
      </header>
      <Card className="max-w-3xl">
        <h2 className="flex items-center gap-2 font-semibold">
          <BrainCircuit size={17} className="text-accent" />
          Response Workbench
        </h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Field label="Response Mode">
            <Select
              aria-label="Response mode"
              value={preferences?.response_mode ?? "direct_expert"}
              onChange={(event) =>
                void updatePreferences({ response_mode: event.target.value as ResponseMode })
              }
            >
              <option value="standard">Standard</option>
              <option value="direct_expert">Direct Expert</option>
            </Select>
          </Field>
          <Field label="Technical Depth">
            <Select
              aria-label="Technical depth"
              value={preferences?.technical_depth ?? "expert"}
              onChange={(event) =>
                void updatePreferences({ technical_depth: event.target.value as TechnicalDepth })
              }
            >
              <option value="standard">Standard</option>
              <option value="deep">Deep</option>
              <option value="expert">Expert</option>
            </Select>
          </Field>
          <Field label="Default Agent">
            <Select
              aria-label="Default agent"
              value={preferences?.default_agent ?? ""}
              onChange={(event) =>
                void updatePreferences({ default_agent: event.target.value || null })
              }
            >
              <option value="">No default agent</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>
                  {agent.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Router Bias">
            <Select
              aria-label="Intelligence mode"
              value={preferences?.intelligence_mode ?? "auto"}
              onChange={(event) =>
                void updatePreferences({ intelligence_mode: event.target.value as IntelligenceMode })
              }
            >
              <option value="auto">Auto</option>
              <option value="quality">Quality</option>
              <option value="speed">Speed</option>
              <option value="local_only">Local Only</option>
            </Select>
          </Field>
          <Field label="Reasoning Mode">
            <Select
              aria-label="Reasoning mode"
              value={preferences?.reasoning_mode ?? "auto"}
              onChange={(event) =>
                void updatePreferences({ reasoning_mode: event.target.value as ReasoningMode })
              }
            >
              <option value="auto">Auto</option>
              <option value="fast">Fast</option>
              <option value="deep">Deep</option>
            </Select>
          </Field>
        </div>
        <PreferenceStatus status={preferenceStatus} message={preferenceMessage} error={preferenceError} />
      </Card>
      <Card className="max-w-3xl">
        <h2 className="flex items-center gap-2 font-semibold">
          <Palette size={17} className="text-accent" />
          Theme
        </h2>
        <Select
          aria-label="Theme preference"
          className="mt-3 w-full sm:w-64"
          value={preferences?.theme ?? themePreference}
          onChange={(event) => void updatePreferences({ theme: event.target.value as ThemePreference })}
        >
          <option value="system">System</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </Select>
      </Card>
      <Card className="max-w-3xl">
        <h2 className="flex items-center gap-2 font-semibold">
          <UserRound size={17} className="text-accent" />
          Local Account
        </h2>
        <dl className="mt-3 space-y-2 text-sm">
          <Row label="Username" value={user?.username ?? "Unavailable"} />
          <Row label="Role" value={user?.role ?? "Unavailable"} />
          <Row label="Session" value={user ? "Authenticated" : "Unauthenticated"} />
          <Row label="Active Agent" value={selectedAgent?.name ?? "Default"} />
        </dl>
        <button
          className="motion-standard mt-4 inline-flex h-9 items-center gap-2 rounded-lg border border-border-subtle bg-elevated/70 px-3 text-sm text-muted transition hover:border-border hover:bg-panel hover:text-text"
          onClick={() => void logout()}
        >
          <LogOut size={15} />
          Log Out
        </button>
      </Card>
      <Card className="max-w-3xl">
        <h2 className="flex items-center gap-2 font-semibold">
          <KeyRound size={17} className="text-accent" />
          Change Password
        </h2>
        <form className="mt-4 grid gap-3 sm:grid-cols-3" onSubmit={(event) => void changePassword(event)}>
          <Input
            aria-label="Current password"
            autoComplete="current-password"
            placeholder="Current password"
            type="password"
            value={passwordState.current}
            onChange={(event) => setPasswordState((state) => ({ ...state, current: event.target.value }))}
          />
          <Input
            aria-label="New password"
            autoComplete="new-password"
            placeholder="New password"
            type="password"
            value={passwordState.next}
            onChange={(event) => setPasswordState((state) => ({ ...state, next: event.target.value }))}
          />
          <Input
            aria-label="Confirm new password"
            autoComplete="new-password"
            placeholder="Confirm new password"
            type="password"
            value={passwordState.confirm}
            onChange={(event) => setPasswordState((state) => ({ ...state, confirm: event.target.value }))}
          />
          <div className="sm:col-span-3">
            <button
              className="motion-standard inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-accent px-3 text-sm font-semibold text-accent-contrast transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={passwordState.status === "saving"}
              type="submit"
            >
              <KeyRound size={15} />
              {passwordState.status === "saving" ? "Saving..." : "Update Password"}
            </button>
            {passwordState.message ? (
              <p
                className={`mt-2 text-sm ${
                  passwordState.status === "error" ? "text-danger" : "text-positive"
                }`}
                role="status"
              >
                {passwordState.message}
              </p>
            ) : null}
          </div>
        </form>
      </Card>
      <Card className="max-w-3xl">
        <h2 className="flex items-center gap-2 font-semibold">
          <MonitorCog size={17} className="text-accent" />
          Backend Connectivity
        </h2>
        {config.loading ? <Spinner /> : null}
        {config.data ? (
          <dl className="mt-3 space-y-2 text-sm">
            <Row label="Environment" value={config.data.environment} />
            <Row label="Network access" value={config.data.network_access ? "Enabled" : "Disabled"} />
            <Row
              label="Cloud inference"
              value={
                config.data.model_endpoint.cloud_inference_enabled === true ? "Enabled" : "Disabled"
              }
            />
          </dl>
        ) : (
          <p className="mt-3 text-sm text-muted">Public backend config is unavailable.</p>
        )}
      </Card>
      <Card className="max-w-3xl">
        <h2 className="flex items-center gap-2 font-semibold">
          <ShieldCheck size={17} className="text-accent" />
          Provider Settings
        </h2>
        <p className="mt-2 text-sm text-muted">
          Provider endpoints are configured on the backend. Secrets are never returned to this page.
        </p>
      </Card>
    </div>
  );
}

function PreferenceStatus({
  status,
  message,
  error
}: {
  status: string;
  message: string | null;
  error: string | null;
}) {
  if (status === "loading" || status === "saving") {
    return (
      <p className="mt-4 inline-flex items-center gap-2 text-sm text-muted" role="status">
        <Spinner /> {status === "loading" ? "Loading preferences..." : "Saving preferences..."}
      </p>
    );
  }
  if (error) {
    return <p className="mt-4 text-sm text-danger">{error}</p>;
  }
  if (message) {
    return (
      <p className="mt-4 inline-flex items-center gap-2 text-sm text-positive" role="status">
        <CheckCircle2 size={15} /> {message}
      </p>
    );
  }
  return null;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="space-y-1 text-sm">
      <span className="block text-muted">{label}</span>
      {children}
    </label>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-muted">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
