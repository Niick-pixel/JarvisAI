// The routines, with the last thing each one did. "Run now" uses the same code path the scheduler
// does, so trying a routine is testing the routine.
import { Bot, Pause, Play, Plus, Trash2, Zap } from "lucide-react";
import { useState } from "react";
import type { Job, JobRun } from "../api/types";
import { useAgents } from "../store/agents";
import { Button, Empty, IconButton } from "../ui/controls";
import JobForm, { describe } from "./JobForm";

const STATUS: Record<string, string> = {
  running: "Running now",
  waiting_approval: "Waiting for your OK",
  done: "Finished",
  failed: "Failed",
  cancelled: "Cancelled",
};

function when(ms: number | null | undefined): string {
  if (!ms) return "never";
  return new Date(ms).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" });
}

export default function JobList() {
  const { jobs, runs, tools, busy, runNow, toggle, remove } = useAgents();
  const [adding, setAdding] = useState(false);
  const lastRun = (job: Job): JobRun | undefined => runs.find((r) => r.job_id === job.id);

  if (adding) return <JobForm tools={tools} onDone={() => setAdding(false)} />;

  return (
    <div>
      {jobs.length === 0 ? (
        <Empty icon={Bot} title="No routines yet">
          A routine is an instruction, a schedule, and the tools you allow it - "every morning, summarise what changed in
          my notes folder".
        </Empty>
      ) : (
        <div className="-mx-4">
          {jobs.map((job) => {
            const run = lastRun(job);
            return (
              <article key={job.id} className="group flex items-start gap-3 rounded-3xl px-4 py-3.5 transition-colors hover:bg-ink/[0.03]">
                <div className="min-w-0 flex-1">
                  <p className={`truncate text-[15px] font-medium ${job.enabled ? "text-ink" : "text-ink-faint"}`}>{job.name}</p>
                  <p className="mt-0.5 text-[12.5px] text-ink-faint">
                    {job.enabled ? `${describe(job.cron)} · next ${when(job.next_run_at)}` : "Paused"}
                  </p>
                  {run && (
                    <p className={`mt-1 line-clamp-2 text-[13px] ${run.status === "failed" ? "text-danger" : "text-ink-muted"}`}>
                      {STATUS[run.status] ?? run.status}
                      {run.summary ? ` - ${run.summary}` : ""}
                      {run.error ? ` - ${run.error}` : ""}
                    </p>
                  )}
                </div>
                <div className="flex opacity-60 transition-opacity group-hover:opacity-100">
                  <IconButton icon={Zap} label="Run now" size={32} disabled={busy === job.id} onClick={() => void runNow(job.id)} />
                  <IconButton icon={job.enabled ? Pause : Play} label={job.enabled ? "Pause" : "Resume"} size={32} onClick={() => void toggle(job)} />
                  <IconButton icon={Trash2} label="Delete" size={32} onClick={() => void remove(job.id)} />
                </div>
              </article>
            );
          })}
        </div>
      )}
      <div className="mt-2 flex justify-center">
        <Button icon={Plus} onClick={() => setAdding(true)}>
          New routine
        </Button>
      </div>
    </div>
  );
}
