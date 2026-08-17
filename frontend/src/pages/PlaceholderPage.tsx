import { Construction } from "lucide-react";

import { EmptyState } from "../components/ui/EmptyState";

const phaseCopy: Record<string, string> = {
  "Knowledge Base": "Document ingestion, chunking, retrieval, and citations are planned for Phase 7.",
  Agents: "Configurable agent execution is planned for a later phase.",
  Memory: "Layered long-term memory is planned for a later phase and remains disabled by policy.",
  Tools: "Secure tool execution is planned for Phase 10 and is not available here."
};

export function PlaceholderPage({ title }: { title: keyof typeof phaseCopy }) {
  return (
    <div className="p-6">
      <EmptyState className="min-h-[58vh]" title={title} icon={<Construction size={28} />}>
        {phaseCopy[title]}
      </EmptyState>
    </div>
  );
}
