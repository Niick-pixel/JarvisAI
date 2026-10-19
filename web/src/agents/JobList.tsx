// The workflows, with how each one has been doing: the last runs as a strip, oldest to newest, and
// the last thing it did. "Run now" uses the same code path the scheduler does, so trying a
// workflow is testing the workflow.
import { Bot, Pause, Play, Plus, Trash2, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import type { Job, JobRun, JobStats } from "../api/types";
import { useAgents } from "../store/agents";
import { useWorkflows } from "../store/workflows";
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

const DOT: Record<string, string> = {
  done: "bg-success",
  failed: "bg-danger",
  waiting_approval: "bg-accent",
  running: "bg-accent animate-pulse",
  cancelled: "bg-ink/20",
};

function History({ stats }: { stats?: JobStats }) {
  if (!stats || stats.runs === 0) return null;
  const seconds = stats.avg_seconds ? ` · about ${Math.max(1, Math.round(stats.avg_seconds))}s a run` : "";
  return (
    <div className="mt-1.5 flex items-center gap-2 text-[12px] text-ink-faint">
      <span className="flex gap-[3px]" aria-hidden>
        {stats.recent.map((status, i) => (
          <span key={i} title={STATUS[status] ?? status} className={`h-3 w-1.5 rounded-full ${DOT[status] ?? "bg-ink/20"}`} />
        ))}
      </span>
      <span>
        {stats.ok} of {stats.runs} finished{stats.failed ? `, ${stats.failed} failed` : ""}
        {seconds}
        {stats.waiting ? ` · ${stats.waiting} waiting for you` : ""}
      </span>
    </div>
  );
}

export default function JobList() {
  const { jobs, runs, tools, busy, runNow, toggle, remove } = useAgents();
  const { draft, drafting, stats, loadStats, clear } = useWorkflows();
  const [adding, setAdding] = useState(false);
  const lastRun = (job: Job): JobRun | undefined => runs.find((r) => r.job_id === job.id);
  useEffect(() => void loadStats().catch(() => undefined), [loadStats, runs]);

  if (adding || draft || drafting) {
    return (
      <JobForm
        tools={tools}
        onDone={() => {
          setAdding(false);
          clear();
        }}
      />
    );
  }

  return (
    <div>
      {jobs.length === 0 ? (
        <Empty icon={Bot} title="No workflows yet">
          Describe one in a sentence - "every weekday at 7, check ES and tell me if the overnight range was over 30
          points" - or open a chat where you did something once and choose "Make this a workflow".
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
                  <History stats={stats[job.id]} />
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
          New workflow
        </Button>
      </div>
    </div>
  );
}
