import { ArrowRight, Cpu, Database, LockKeyhole, ShieldCheck, TerminalSquare } from "lucide-react";
import type { FormEvent, ReactNode } from "react";
import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { Button } from "../components/ui/Button";
import { Spinner } from "../components/ui/Spinner";
import { useAuthStore } from "../stores/authStore";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const status = useAuthStore((state) => state.status);
  const error = useAuthStore((state) => state.error);
  const login = useAuthStore((state) => state.login);
  const restore = useAuthStore((state) => state.restore);
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (status === "checking") {
      void restore();
    }
  }, [restore, status]);

  if (status === "authenticated") {
    const target = loginRedirectTarget(location.state);
    return <Navigate replace to={target} />;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      await login(username, password);
      navigate("/", { replace: true });
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-grid relative grid min-h-screen overflow-hidden bg-background text-text">
      <div className="pointer-events-none absolute inset-0 login-ambient" />
      <div className="relative z-10 grid min-h-screen place-items-center px-4 py-8">
        <section className="login-panel w-full max-w-[28rem] rounded-2xl border border-accent/20 bg-panel/82 p-6 shadow-popover backdrop-blur-xl sm:p-7">
          <div className="mb-6 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="relative grid size-11 place-items-center rounded-xl border border-accent/30 bg-accent/10 text-accent shadow-soft">
                <TerminalSquare size={22} />
                <span className="absolute -right-0.5 -top-0.5 size-2 rounded-full bg-positive ring-2 ring-panel" />
              </div>
              <div>
                <h1 className="text-lg font-semibold tracking-tight">HackerGPT Local</h1>
                <p className="text-xs text-muted">Private Technical Intelligence Workstation</p>
              </div>
            </div>
            <span className="rounded-full border border-positive/25 bg-positive/10 px-2.5 py-1 text-technical text-[11px] text-positive">
              local
            </span>
          </div>

          <div className="mb-6 grid grid-cols-3 gap-2">
            <StatusChip icon={<ShieldCheck size={13} />} label="auth" />
            <StatusChip icon={<Cpu size={13} />} label="model-aware" />
            <StatusChip icon={<Database size={13} />} label="private" />
          </div>

          <form className="space-y-4" onSubmit={(event) => void submit(event)}>
            <label className="block text-sm">
              <span className="text-muted">Username</span>
              <input
                autoComplete="username"
                className="mt-1 h-11 w-full rounded-xl border border-border-subtle bg-elevated/70 px-3 text-sm outline-none transition focus:border-accent focus:bg-panel focus:ring-2 focus:ring-accent/25"
                onChange={(event) => setUsername(event.target.value)}
                value={username}
              />
            </label>
            <label className="block text-sm">
              <span className="text-muted">Password</span>
              <input
                autoComplete="current-password"
                className="mt-1 h-11 w-full rounded-xl border border-border-subtle bg-elevated/70 px-3 text-sm outline-none transition focus:border-accent focus:bg-panel focus:ring-2 focus:ring-accent/25"
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                value={password}
              />
            </label>
            {error ? (
              <div className="rounded-xl border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
                {error}
              </div>
            ) : null}
            <Button
              className="h-11 w-full rounded-xl"
              disabled={busy || !username.trim() || !password}
              icon={busy ? <Spinner /> : <ArrowRight size={16} />}
              type="submit"
              variant="primary"
            >
              Enter Workstation
            </Button>
          </form>

          <div className="mt-5 rounded-xl border border-border-subtle bg-elevated/45 p-3">
            <div className="flex items-center gap-2 text-xs font-medium text-secondary">
              <LockKeyhole size={13} className="text-accent" />
              Local bootstrap account
            </div>
            <p className="mt-2 text-xs leading-5 text-muted">
              Default local admin: <span className="text-technical text-secondary">admin / admin987</span>
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}

function StatusChip({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="flex items-center justify-center gap-1.5 rounded-xl border border-border-subtle bg-elevated/50 px-2 py-2 text-technical text-[11px] text-muted">
      <span className="text-accent">{icon}</span>
      {label}
    </div>
  );
}

function loginRedirectTarget(state: unknown): string {
  if (state === null || typeof state !== "object" || !("from" in state)) {
    return "/";
  }
  const from = (state as { from?: unknown }).from;
  return typeof from === "string" && from.startsWith("/") ? from : "/";
}
