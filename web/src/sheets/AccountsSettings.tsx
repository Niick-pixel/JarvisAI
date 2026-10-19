// Settings > Accounts: Gmail and GitHub. Connecting checks the credential with the service first,
// then it is stored on this PC (encrypted for your Windows account) and never shown again.
// Once connected, chats in tools mode and workflows can read your mail and GitHub; writing a
// draft or a comment always asks you first.
import { GitBranch, Mail } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { ApiError, request } from "../api/client";
import type { AccountStatus } from "../api/types";
import { toast } from "../store/toast";
import { useUi } from "../store/ui";
import { Button, FIELD, Row } from "../ui/controls";
import { Group } from "./SettingsPanels";

const put = (path: string, body: unknown) => request<AccountStatus[]>(path, { method: "PUT", body: JSON.stringify(body) });

function Account({
  icon: Icon,
  title,
  status,
  what,
  help,
  onDisconnect,
  children,
}: {
  icon: LucideIcon;
  title: string;
  status?: AccountStatus;
  what: string;
  help: ReactNode;
  onDisconnect: () => void;
  children: ReactNode;
}) {
  return (
    <div className="py-4">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-ink/[0.05] text-ink-muted">
          <Icon size={18} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-[14px] font-medium text-ink">{title}</p>
          <p className="mt-0.5 text-[13px] leading-snug text-ink-faint">
            {status?.connected ? `Connected as ${status.who}. ${what}` : what}
          </p>
        </div>
        {status?.connected && (
          <Button small tone="ghost" onClick={onDisconnect}>
            Disconnect
          </Button>
        )}
      </div>
      {!status?.connected && (
        <div className="ml-12 mt-3 space-y-2">
          {children}
          <p className="text-[12.5px] leading-relaxed text-ink-faint">{help}</p>
        </div>
      )}
    </div>
  );
}

export default function AccountsSettings() {
  const [accounts, setAccounts] = useState<AccountStatus[]>([]);
  const [address, setAddress] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState("");
  useEffect(() => void request<AccountStatus[]>("/api/connections").then(setAccounts).catch(() => undefined), []);
  const by = Object.fromEntries(accounts.map((a) => [a.name, a]));

  const run = async (name: string, call: () => Promise<AccountStatus[]>) => {
    setBusy(name);
    try {
      setAccounts(await call());
      setPassword("");
      setToken("");
    } catch (error) {
      toast(error instanceof ApiError ? error.body.message : `Couldn't connect ${name}`, "error");
    } finally {
      setBusy("");
    }
  };
  const disconnect = (name: string) => () =>
    void run(name, () => request<AccountStatus[]>(`/api/connections/${name}`, { method: "DELETE" }));

  return (
    <>
      <Group title="Accounts">
        <Account
          icon={Mail}
          title="Gmail"
          status={by.gmail}
          what="Jarvis can search and read your mail, and write drafts - it never sends."
          onDisconnect={disconnect("gmail")}
          help="Use an app password, not your normal one: Google Account > Security > 2-Step Verification > App passwords. Gmail's IMAP must be on (Gmail settings > Forwarding and POP/IMAP)."
        >
          <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="you@gmail.com" className={FIELD} />
          <div className="flex gap-2">
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="App password (16 letters)" className={FIELD} />
            <Button tone="primary" disabled={!address || !password || busy === "gmail"} onClick={() => void run("gmail", () => put("/api/connections/gmail", { address, app_password: password }))}>
              {busy === "gmail" ? "Checking…" : "Connect"}
            </Button>
          </div>
        </Account>
        <Account
          icon={GitBranch}
          title="GitHub"
          status={by.github}
          what="Jarvis can read your notifications, issues and pull requests, and comment when you approve."
          onDisconnect={disconnect("github")}
          help="Create a token at GitHub > Settings > Developer settings > Personal access tokens. A fine-grained token can be limited to read-only and to the repositories you choose."
        >
          <div className="flex gap-2">
            <input type="password" value={token} onChange={(e) => setToken(e.target.value)} placeholder="github_pat_…" className={FIELD} />
            <Button tone="primary" disabled={!token || busy === "github"} onClick={() => void run("github", () => put("/api/connections/github", { token }))}>
              {busy === "github" ? "Checking…" : "Connect"}
            </Button>
          </div>
        </Account>
      </Group>
      <Group title="Also connected">
        <Row title="Home Assistant" detail="Lights, locks and sensors. Set up from Home.">
          <Button small tone="ghost" onClick={() => useUi.getState().openSheet("home")}>
            Open Home
          </Button>
        </Row>
      </Group>
      <p className="text-[12.5px] leading-relaxed text-ink-faint">
        Passwords and tokens stay on this PC, encrypted for your Windows account, and go only to Google or GitHub. What Jarvis reads
        from your mail is treated as information, never as instructions.
      </p>
    </>
  );
}
