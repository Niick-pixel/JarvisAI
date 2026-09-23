// Agents (BRIEF.md 4.9): routines that run on their own schedule, what they reported, and a record
// of every action they took. Anything with a side effect still asks you first.
import { useEffect, useState } from "react";
import AuditLog from "../agents/AuditLog";
import Inbox from "../agents/Inbox";
import JobList from "../agents/JobList";
import Sheet from "../shell/Sheet";
import { useAgents } from "../store/agents";
import { Segmented } from "../ui/controls";

type Tab = "routines" | "inbox" | "activity";

export default function AgentsSheet() {
  const [tab, setTab] = useState<Tab>("routines");
  const error = useAgents((s) => s.error);
  const dismiss = useAgents((s) => s.dismiss);
  const refresh = useAgents((s) => s.refresh);
  const unread = useAgents((s) => s.inbox.filter((i) => !i.read_at).length);

  useEffect(() => {
    void refresh().catch(() => undefined);
  }, [refresh]);

  return (
    <Sheet title="Agents" subtitle="Routines that work in the background. Anything that changes your files asks first.">
      <div className="mb-4">
        <Segmented
          id="agents"
          value={tab}
          onChange={setTab}
          options={[
            { value: "routines", label: "Routines" },
            { value: "inbox", label: unread ? `Inbox (${unread})` : "Inbox" },
            { value: "activity", label: "Activity" },
          ]}
        />
      </div>
      {error && (
        <button type="button" onClick={dismiss} className="mb-3 w-full rounded-2xl bg-danger/[0.07] px-4 py-2.5 text-left text-[13px] text-ink">
          {error}
        </button>
      )}
      {tab === "routines" && <JobList />}
      {tab === "inbox" && <Inbox />}
      {tab === "activity" && <AuditLog />}
    </Sheet>
  );
}
