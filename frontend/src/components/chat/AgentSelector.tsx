import { useEffect } from "react";

import { Select } from "../ui/Form";
import { useAgentStore } from "../../stores/agentStore";

export function AgentSelector() {
  const agents = useAgentStore((state) => state.agents);
  const selectedAgentId = useAgentStore((state) => state.selectedAgentId);
  const loadAgents = useAgentStore((state) => state.loadAgents);
  const selectAgent = useAgentStore((state) => state.selectAgent);

  useEffect(() => {
    if (agents.length === 0) {
      void loadAgents();
    }
  }, [agents.length, loadAgents]);

  return (
    <Select
      aria-label="Agent"
      className="max-w-[13rem] text-xs"
      value={selectedAgentId ?? ""}
      onChange={(event) => selectAgent(event.target.value || null)}
    >
      <option value="">Backend default</option>
      {agents.map((agent) => (
        <option key={agent.id} value={agent.id} disabled={!agent.enabled}>
          {agent.name}
        </option>
      ))}
    </Select>
  );
}
