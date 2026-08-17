import { lazy, Suspense, useEffect, type ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AppShell } from "./components/layout/AppShell";
import { ChatPage } from "./pages/ChatPage";
import { LoginPage } from "./pages/LoginPage";
import { useAuthStore } from "./stores/authStore";

const AgentsPage = lazy(() => import("./pages/AgentsPage").then((module) => ({ default: module.AgentsPage })));
const CybersecurityPage = lazy(() =>
  import("./pages/CybersecurityPage").then((module) => ({ default: module.CybersecurityPage }))
);
const IntelligencePage = lazy(() =>
  import("./pages/IntelligencePage").then((module) => ({ default: module.IntelligencePage }))
);
const KnowledgePage = lazy(() =>
  import("./pages/KnowledgePage").then((module) => ({ default: module.KnowledgePage }))
);
const LearningStudioPage = lazy(() =>
  import("./pages/LearningStudioPage").then((module) => ({ default: module.LearningStudioPage }))
);
const MemoryPage = lazy(() => import("./pages/MemoryPage").then((module) => ({ default: module.MemoryPage })));
const ModelsPage = lazy(() => import("./pages/ModelsPage").then((module) => ({ default: module.ModelsPage })));
const PromptLabPage = lazy(() =>
  import("./pages/PromptLabPage").then((module) => ({ default: module.PromptLabPage }))
);
const ResearchPage = lazy(() =>
  import("./pages/ResearchPage").then((module) => ({ default: module.ResearchPage }))
);
const SettingsPage = lazy(() =>
  import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage }))
);
const SystemStatusPage = lazy(() =>
  import("./pages/SystemStatusPage").then((module) => ({ default: module.SystemStatusPage }))
);
const ToolsPage = lazy(() => import("./pages/ToolsPage").then((module) => ({ default: module.ToolsPage })));

export function App() {
  return (
    <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedShell />}>
          <Route index element={<ChatPage />} />
          <Route path="models" element={<LazyPage><ModelsPage /></LazyPage>} />
          <Route path="knowledge" element={<LazyPage><KnowledgePage /></LazyPage>} />
          <Route path="ethical-hacking" element={<LazyPage><CybersecurityPage /></LazyPage>} />
          <Route path="cybersecurity" element={<LazyPage><CybersecurityPage /></LazyPage>} />
          <Route path="research" element={<LazyPage><ResearchPage /></LazyPage>} />
          <Route path="intelligence" element={<LazyPage><IntelligencePage /></LazyPage>} />
          <Route path="learning" element={<LazyPage><LearningStudioPage /></LazyPage>} />
          <Route path="prompts" element={<LazyPage><PromptLabPage /></LazyPage>} />
          <Route path="agents" element={<LazyPage><AgentsPage /></LazyPage>} />
          <Route path="memory" element={<LazyPage><MemoryPage /></LazyPage>} />
          <Route path="tools" element={<LazyPage><ToolsPage /></LazyPage>} />
          <Route path="settings" element={<LazyPage><SettingsPage /></LazyPage>} />
          <Route path="system" element={<LazyPage><SystemStatusPage /></LazyPage>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

function ProtectedShell() {
  const location = useLocation();
  const status = useAuthStore((state) => state.status);
  const restore = useAuthStore((state) => state.restore);

  useEffect(() => {
    if (status === "checking") {
      void restore();
    }
  }, [restore, status]);

  if (status === "checking") {
    return (
      <div className="grid min-h-screen place-items-center bg-background p-6 text-sm text-muted">
        Restoring secure local session...
      </div>
    );
  }
  if (status === "unauthenticated") {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />;
  }
  return <AppShell />;
}

function LazyPage({ children }: { children: ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="grid min-h-[60vh] place-items-center p-6 text-sm text-muted">
          Loading workspace...
        </div>
      }
    >
      {children}
    </Suspense>
  );
}
