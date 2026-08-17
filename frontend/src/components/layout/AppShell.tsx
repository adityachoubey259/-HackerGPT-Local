import {
  Bot,
  Brain,
  BrainCircuit,
  Archive,
  ChevronLeft,
  ChevronRight,
  CircleDot,
  Database,
  GraduationCap,
  Home,
  LockKeyhole,
  LogOut,
  Menu,
  MessageSquarePlus,
  Search,
  SearchCheck,
  Settings,
  ShieldCheck,
  ShieldHalf,
  SlidersHorizontal,
  WandSparkles,
  Pencil,
  RotateCcw,
  Trash2,
  UserRound,
  Wrench,
  X
} from "lucide-react";
import { useEffect, useRef } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { RightInspector } from "../chat/RightInspector";
import { CommandPalette } from "./CommandPalette";
import { IconButton } from "../ui/IconButton";
import { modelsApi } from "../../api/models";
import { useFocusTrap } from "../../hooks/useFocusTrap";
import { useAuthStore } from "../../stores/authStore";
import { useConversationStore } from "../../stores/conversationStore";
import { useModelStore } from "../../stores/modelStore";
import { useUiStore } from "../../stores/uiStore";
import { cn } from "../../utils";

const navItems = [
  { to: "/", label: "Chat", icon: Home },
  { to: "/models", label: "Models", icon: Bot },
  { to: "/knowledge", label: "Knowledge", icon: Database },
  { to: "/ethical-hacking", label: "Ethical Hacking", icon: ShieldHalf },
  { to: "/research", label: "Research", icon: SearchCheck },
  { to: "/intelligence", label: "Intelligence", icon: BrainCircuit },
  { to: "/learning", label: "Learning Studio", icon: GraduationCap },
  { to: "/prompts", label: "Prompt Lab", icon: WandSparkles },
  { to: "/agents", label: "Agents", icon: Brain },
  { to: "/memory", label: "Memory", icon: ShieldCheck },
  { to: "/tools", label: "Tools", icon: Wrench },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/system", label: "System Status", icon: SlidersHorizontal }
] as const;

export function AppShell() {
  const collapsed = useUiStore((state) => state.sidebarCollapsed);
  const mobileSidebarOpen = useUiStore((state) => state.mobileSidebarOpen);
  const toggleSidebar = useUiStore((state) => state.toggleSidebar);
  const openMobileSidebar = useUiStore((state) => state.openMobileSidebar);
  const closeMobileSidebar = useUiStore((state) => state.closeMobileSidebar);
  const openCommandPalette = useUiStore((state) => state.openCommandPalette);
  const mobileDrawerRef = useRef<HTMLDivElement | null>(null);
  const conversations = useConversationStore((state) => state.conversations);
  const archivedConversations = useConversationStore((state) => state.archivedConversations);
  const activeConversationId = useConversationStore((state) => state.activeConversationId);
  const search = useConversationStore((state) => state.search);
  const setSearch = useConversationStore((state) => state.setSearch);
  const loadConversations = useConversationStore((state) => state.loadConversations);
  const newChat = useConversationStore((state) => state.newChat);
  const selectConversation = useConversationStore((state) => state.selectConversation);
  const renameConversation = useConversationStore((state) => state.renameConversation);
  const archiveConversation = useConversationStore((state) => state.archiveConversation);
  const deleteConversation = useConversationStore((state) => state.deleteConversation);
  const selectedProvider = useModelStore((state) => state.selectedProvider);
  const setProviders = useModelStore((state) => state.setProviders);
  const setModels = useModelStore((state) => state.setModels);
  const selectModel = useModelStore((state) => state.selectModel);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  useFocusTrap(mobileDrawerRef, mobileSidebarOpen, closeMobileSidebar);

  useEffect(() => {
    const handle = window.setTimeout(() => {
      void loadConversations(false);
      void loadConversations(true);
    }, 180);
    return () => window.clearTimeout(handle);
  }, [loadConversations, search]);

  useEffect(() => {
    async function loadModels() {
      try {
        const [providers, models] = await Promise.all([modelsApi.providers(), modelsApi.models()]);
        setProviders(providers);
        setModels(models);
        if (!selectedProvider && models[0]) {
          selectModel(models[0].provider, models[0].provider_model_id);
        }
      } catch {
        setProviders([]);
        setModels([]);
      }
    }
    void loadModels();
  }, [selectModel, selectedProvider, setModels, setProviders]);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-text">
      <aside
        className={cn(
          "hidden shrink-0 border-r border-border-subtle bg-sidebar/95 transition-[width] duration-200 ease-emphasized md:block",
          collapsed ? "w-16" : "w-64"
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-border-subtle px-3">
          {!collapsed ? (
            <div className="flex min-w-0 items-center gap-3">
              <BrandMark />
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">HackerGPT Local</div>
                <div className="flex items-center gap-1.5 text-xs text-muted">
                  <LockKeyhole size={12} />
                  <span>Local-first workstation</span>
                </div>
              </div>
            </div>
          ) : (
            <BrandMark compact />
          )}
          <IconButton
            label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            icon={collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            onClick={toggleSidebar}
          />
        </div>
        <div className="space-y-2 p-3">
          <button
            className="motion-standard flex h-10 w-full items-center gap-2 rounded-xl border border-accent/30 bg-accent px-3 text-sm font-medium text-white shadow-[0_12px_30px_rgb(var(--color-accent)/0.24)] transition-[background,transform] hover:bg-accent-hover active:translate-y-px dark:text-background"
            onClick={newChat}
          >
            <MessageSquarePlus size={16} />
            {!collapsed ? <span>New Chat</span> : null}
          </button>
          {!collapsed ? (
            <button
              className="motion-standard flex h-9 w-full items-center justify-between rounded-lg border border-border-subtle bg-elevated/60 px-3 text-left text-xs text-muted transition hover:bg-elevated hover:text-text"
              onClick={openCommandPalette}
            >
              <span className="flex items-center gap-2">
                <Search size={14} />
                Command palette
              </span>
              <kbd className="rounded border border-border-subtle bg-panel px-1.5 py-0.5 text-[10px]">
                Ctrl K
              </kbd>
            </button>
          ) : null}
        </div>
        <nav aria-label="Primary navigation" className="space-y-1 px-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                aria-label={collapsed ? item.label : undefined}
                end={item.to === "/"}
                className={({ isActive }) =>
                  cn(
                    "motion-standard relative flex h-10 items-center gap-3 rounded-xl px-3 text-sm transition-[background,color,transform]",
                    isActive
                      ? "bg-elevated text-text shadow-sm"
                      : "text-muted hover:bg-elevated/70 hover:text-text",
                    collapsed && "justify-center px-0"
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {!collapsed && isActive ? (
                      <span className="absolute left-0 h-5 w-0.5 rounded-full bg-accent" />
                    ) : null}
                    <Icon size={16} />
                    {!collapsed ? <span className="truncate">{item.label}</span> : null}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
        {!collapsed ? (
          <div className="mt-4 border-t border-border-subtle px-3 pt-3">
            <div className="mb-2 flex items-center gap-2 rounded-lg border border-border-subtle bg-elevated/60 px-2">
              <Search size={14} className="text-muted" />
              <input
                aria-label="Search conversations"
                className="h-8 min-w-0 flex-1 bg-transparent text-xs text-text outline-none placeholder:text-muted"
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search chats"
                value={search}
              />
              {search ? (
                <button className="text-xs text-muted hover:text-text" onClick={() => setSearch("")}>
                  Clear
                </button>
              ) : null}
            </div>
            <div className="max-h-[34vh] space-y-1 overflow-auto pr-1">
              {conversations.map((conversation) => (
                <div
                  className={cn(
                    "group rounded-xl border px-2 py-2 transition",
                    conversation.id === activeConversationId
                      ? "border-accent/40 bg-accent/10"
                      : "border-transparent hover:border-border-subtle hover:bg-elevated/60"
                  )}
                  key={conversation.id}
                >
                  <button
                    className="w-full text-left"
                    onClick={() => void selectConversation(conversation.id)}
                  >
                    <div className="truncate text-sm font-medium">{conversation.title}</div>
                    <div className="text-technical mt-1 truncate text-[11px] text-muted">
                      {new Date(conversation.updated_at).toLocaleString()}
                    </div>
                  </button>
                  <div className="mt-2 flex gap-1 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                    <IconButton
                      className="size-7"
                      label="Rename conversation"
                      icon={<Pencil size={13} />}
                      onClick={() => {
                        const title = window.prompt("Rename conversation", conversation.title);
                        if (title?.trim()) {
                          void renameConversation(conversation.id, title.trim());
                        }
                      }}
                    />
                    <IconButton
                      className="size-7"
                      label="Archive conversation"
                      icon={<Archive size={13} />}
                      onClick={() => void archiveConversation(conversation.id, true)}
                    />
                    <IconButton
                      className="size-7"
                      label="Delete conversation"
                      icon={<Trash2 size={13} />}
                      onClick={() => {
                        if (window.confirm(`Delete "${conversation.title}"? This cannot be undone.`)) {
                          void deleteConversation(conversation.id);
                        }
                      }}
                    />
                  </div>
                </div>
              ))}
              {conversations.length === 0 ? (
                <div className="rounded-xl border border-dashed border-border-subtle p-3 text-xs leading-5 text-muted">
                  {search ? "No conversations match your search." : "No saved conversations yet."}
                </div>
              ) : null}
            </div>
            {archivedConversations.length > 0 ? (
              <div className="mt-3 border-t border-border-subtle pt-3">
                <div className="mb-2 text-xs font-medium uppercase text-muted">Archived</div>
                <div className="space-y-1">
                  {archivedConversations.slice(0, 6).map((conversation) => (
                    <div
                      className="group flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-muted hover:bg-elevated/60"
                      key={conversation.id}
                    >
                      <span className="min-w-0 flex-1 truncate">{conversation.title}</span>
                      <IconButton
                        className="size-7"
                        label="Restore conversation"
                        icon={<RotateCcw size={13} />}
                        onClick={() => void archiveConversation(conversation.id, false)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
        {!collapsed ? (
          <div className="mt-5 px-3">
            <div className="mb-3 rounded-xl border border-positive/20 bg-positive/10 p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-xs font-medium text-secondary">
                    <UserRound size={13} className="text-positive" />
                    <span className="truncate">{user?.username ?? "local"}</span>
                  </div>
                  <div className="mt-1 text-technical text-[11px] text-muted">
                    {user?.role ?? "admin"} session
                  </div>
                </div>
                <IconButton
                  className="size-8"
                  label="Log out"
                  icon={<LogOut size={14} />}
                  onClick={() => void logout()}
                />
              </div>
            </div>
            <div className="hairline-panel rounded-xl p-3">
              <div className="flex items-center gap-2 text-xs font-medium text-secondary">
                <CircleDot size={13} className="text-positive" />
                Privacy Boundary
              </div>
              <p className="mt-2 text-xs leading-5 text-muted">
                Browser UI calls only HackerGPT backend APIs. Model endpoints stay server-side.
              </p>
            </div>
          </div>
        ) : null}
      </aside>
      <main className="flex min-w-0 flex-1 flex-col">
        <div className="flex min-h-14 items-center justify-between border-b border-border-subtle bg-panel/90 px-4 backdrop-blur md:hidden">
          <div className="flex items-center gap-3">
            <IconButton label="Open navigation" icon={<Menu size={16} />} onClick={openMobileSidebar} />
            <BrandMark />
            <span className="text-sm font-semibold">HackerGPT Local</span>
          </div>
          <IconButton label="Open command palette" icon={<Search size={16} />} onClick={openCommandPalette} />
        </div>
        <div className="min-h-0 flex-1 overflow-auto">
          <Outlet />
        </div>
      </main>
      {mobileSidebarOpen ? (
        <div
          aria-label="Mobile navigation"
          aria-modal="true"
          className="fixed inset-0 z-overlay bg-background/55 backdrop-blur-sm md:hidden"
          role="dialog"
        >
          <div
            className="h-full w-[min(20rem,calc(100vw-2rem))] border-r border-border-subtle bg-sidebar p-3 shadow-popover"
            ref={mobileDrawerRef}
          >
            <div className="mb-3 flex h-12 items-center justify-between">
              <div className="flex items-center gap-3">
                <BrandMark />
                <span className="text-sm font-semibold">HackerGPT Local</span>
              </div>
              <IconButton label="Close navigation" icon={<X size={16} />} onClick={closeMobileSidebar} />
            </div>
            <button
              className="motion-standard mb-3 flex h-10 w-full items-center gap-2 rounded-xl border border-accent/30 bg-accent px-3 text-sm font-medium text-white shadow-[0_12px_30px_rgb(var(--color-accent)/0.24)] transition-[background,transform] hover:bg-accent-hover active:translate-y-px dark:text-background"
              onClick={() => {
                newChat();
                closeMobileSidebar();
              }}
            >
              <MessageSquarePlus size={16} />
              <span>New Chat</span>
            </button>
            <nav aria-label="Mobile primary navigation" className="space-y-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    className={({ isActive }) =>
                      cn(
                        "motion-standard flex h-10 items-center gap-3 rounded-xl px-3 text-sm transition-[background,color]",
                        isActive
                          ? "bg-elevated text-text shadow-sm"
                          : "text-muted hover:bg-elevated/70 hover:text-text"
                      )
                    }
                    end={item.to === "/"}
                    key={item.to}
                    onClick={closeMobileSidebar}
                    to={item.to}
                  >
                    <Icon size={16} />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>
            <div className="mt-4 border-t border-border-subtle pt-3">
              <div className="text-xs font-medium uppercase text-muted">Conversations</div>
              <div className="mt-2 space-y-1">
                {conversations.slice(0, 8).map((conversation) => (
                  <button
                    className="w-full truncate rounded-lg px-2 py-2 text-left text-sm text-muted hover:bg-elevated hover:text-text"
                    key={conversation.id}
                    onClick={() => {
                      void selectConversation(conversation.id);
                      closeMobileSidebar();
                    }}
                  >
                    {conversation.title}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : null}
      <RightInspector />
      <CommandPalette />
    </div>
  );
}

function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <span
      aria-hidden
      className={cn(
        "relative flex size-9 shrink-0 items-center justify-center rounded-xl border border-accent/25 bg-accent/10 text-xs font-black text-accent shadow-soft",
        compact && "mx-auto"
      )}
    >
      HG
      <span className="absolute -right-0.5 -top-0.5 size-2 rounded-full bg-positive ring-2 ring-sidebar" />
    </span>
  );
}
