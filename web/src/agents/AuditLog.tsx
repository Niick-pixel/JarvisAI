// Every action a routine ever took, as it is stored: paths, hosts, outcomes, and hashes.
//
// There are no arguments and no content here, and that is not an omission in the UI - the writer
// never had them (BRIEF.md 7). Standing permissions live here too, since revoking one is an
// audit-shaped act.
import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { AuditEntry, ToolGrant } from "../api/types";
import { Button, Row } from "../ui/controls";

const OUTCOME: Record<string, string> = {
  ran: "Done",
  refused: "Refused",
  failed: "Failed",
  awaiting_approval: "Waiting for you",
};

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [grants, setGrants] = useState<ToolGrant[]>([]);

  const load = () => {
    void api.auditLog().then(setEntries).catch(() => undefined);
    void api.grants().then(setGrants).catch(() => undefined);
  };
  useEffect(load, []);

  return (
    <div className="space-y-6">
      <section>
        <h3 className="mb-1 text-[13px] font-medium text-ink-muted">Always allowed</h3>
        {grants.length === 0 && <p className="py-2 text-[13px] text-ink-faint">Nothing. Every action is asked for, one at a time.</p>}
        <div className="divide-y divide-ink/[0.06]">
          {grants.map((grant) => (
            <Row key={`${grant.tool}:${grant.scope}`} title={grant.tool} detail={<span className="break-all font-mono text-[12px]">{grant.scope}</span>}>
              <Button small tone="ghost" onClick={() => void api.revokeGrant(grant.tool, grant.scope).then(load).catch(() => undefined)}>
                Revoke
              </Button>
            </Row>
          ))}
        </div>
      </section>
      <section>
        <h3 className="mb-1 text-[13px] font-medium text-ink-muted">Everything that ran</h3>
        {entries.length === 0 && <p className="py-2 text-[13px] text-ink-faint">Nothing has run yet.</p>}
        <ul className="divide-y divide-ink/[0.06]">
          {entries.map((entry) => (
            <li key={entry.id} className="flex items-baseline gap-3 py-2.5 text-[13px]">
              <span className="w-16 shrink-0 tabular-nums text-ink-faint">
                {new Date(entry.at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
              </span>
              <span className="min-w-0 flex-1">
                <span className="text-ink">{entry.tool}</span>
                <span className="text-ink-faint"> · {entry.actor}</span>
                <span className="block break-all font-mono text-[12px] text-ink-muted">{entry.target}</span>
                <span className="block font-mono text-[11px] text-ink-faint">
                  args {entry.args_hash}
                  {entry.result_hash ? ` · result ${entry.result_hash} (${entry.bytes} bytes)` : ""}
                </span>
              </span>
              <span className={`shrink-0 text-[12.5px] ${entry.outcome === "ran" ? "text-success" : entry.outcome === "awaiting_approval" ? "text-accent" : "text-danger"}`}>
                {OUTCOME[entry.outcome] ?? entry.outcome}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
