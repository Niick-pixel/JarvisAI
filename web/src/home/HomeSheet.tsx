// Home: every device Home Assistant knows, by room, as tiles you tap - and a line to tell it what
// to do in words. The same words work in chat and voice mode, when that is switched on below.
import { ArrowUp, House, Unplug } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { Device } from "../api/types";
import Sheet from "../shell/Sheet";
import { useHome } from "../store/home";
import { Button, Empty, FIELD, Row, Switch } from "../ui/controls";
import DeviceTile from "./DeviceTile";

const POLL_MS = 4000;

function Connect() {
  const { connect, error } = useHome();
  const [url, setUrl] = useState("homeassistant.local:8123");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    await connect(url, token);
    setBusy(false);
  };
  return (
    <div className="mx-auto mt-2 max-w-[520px]">
      <Empty icon={House} title="Connect Home Assistant">
        Jarvis controls your home through Home Assistant on your own network. Nothing goes through a cloud.
      </Empty>
      <label className="mt-2 block text-[13px] font-medium text-ink-muted" htmlFor="ha-url">
        Address
      </label>
      <input id="ha-url" value={url} onChange={(e) => setUrl(e.target.value)} className={`${FIELD} mt-1`} />
      <label className="mt-4 block text-[13px] font-medium text-ink-muted" htmlFor="ha-token">
        Long-lived access token
      </label>
      <input
        id="ha-token"
        type="password"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && void submit()}
        placeholder="Paste the token"
        className={`${FIELD} mt-1`}
      />
      <p className="mt-2 text-[12.5px] leading-relaxed text-ink-faint">
        In Home Assistant, open your profile (bottom left), then Security › Long-lived access tokens › Create token. It is
        stored only on this PC.
      </p>
      {error && <p className="mt-3 text-[13px] text-danger">{error}</p>}
      <div className="mt-4 flex justify-end">
        <Button tone="primary" disabled={busy || !url.trim() || !token.trim()} onClick={() => void submit()}>
          {busy ? "Connecting…" : "Connect"}
        </Button>
      </div>
    </div>
  );
}

function Command() {
  const say = useHome((s) => s.say);
  const [text, setText] = useState("");
  const [reply, setReply] = useState("");
  const send = async () => {
    if (!text.trim()) return;
    setReply("…");
    setReply(await say(text).catch((e: Error) => e.message));
    setText("");
  };
  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 rounded-full border border-ink/[0.08] bg-surface p-1.5 pl-5 shadow-card">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void send()}
          placeholder="Turn off the kitchen lights"
          className="min-w-0 flex-1 bg-transparent text-[15px] text-ink outline-none placeholder:text-ink-faint"
        />
        <button
          type="button"
          aria-label="Send to Home Assistant"
          disabled={!text.trim()}
          onClick={() => void send()}
          className="flex h-10 w-10 items-center justify-center rounded-full bg-ink text-bg disabled:opacity-25"
        >
          <ArrowUp size={20} strokeWidth={2} />
        </button>
      </div>
      {reply && <p className="mt-2 pl-5 text-[13.5px] text-ink-muted">{reply}</p>}
    </div>
  );
}

export default function HomeSheet() {
  const { status, devices, error, refresh, loadDevices, setRouteChat, disconnect } = useHome();
  const connected = status?.connected ?? false;

  useEffect(() => void refresh().catch(() => undefined), [refresh]);
  useEffect(() => {
    // Keep tiles honest while you look: a light switched at the wall shows within seconds.
    if (!connected) return;
    const timer = window.setInterval(() => void loadDevices(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [connected, loadDevices]);

  const rooms = useMemo(() => {
    const byRoom = new Map<string, Device[]>();
    for (const device of devices) byRoom.set(device.area, [...(byRoom.get(device.area) ?? []), device]);
    return [...byRoom.entries()];
  }, [devices]);

  const subtitle = connected
    ? `${status?.name || "Home Assistant"} · ${devices.length} devices`
    : "Your devices, in one place, from Home Assistant.";

  return (
    <Sheet title="Home" subtitle={subtitle} width={980}>
      {!status ? null : !status.configured ? (
        <Connect />
      ) : (
        <>
          {!connected && (
            <p className="mb-4 rounded-2xl bg-danger/[0.07] px-4 py-3 text-[13.5px] text-ink">
              {status.error || "Home Assistant isn't answering."}
            </p>
          )}
          {connected && <Command />}
          {error && connected && <p className="mb-4 text-[13px] text-danger">{error}</p>}
          {rooms.map(([room, items]) => (
            <section key={room} className="mb-6">
              <h3 className="mb-2 text-[13px] font-semibold text-ink-muted">{room}</h3>
              <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(168px,1fr))]">
                {items.map((device) => (
                  <DeviceTile key={device.entity_id} device={device} />
                ))}
              </div>
            </section>
          ))}
          <div className="mt-4 divide-y divide-ink/[0.06] border-t border-ink/[0.06]">
            <Row
              title="Home commands in chat and voice"
              detail='Messages like "dim the bedroom to 30%" go to Home Assistant first, using its own local command matcher. Anything else goes to the model as usual.'
            >
              <Switch label="Home commands in chat and voice" checked={status.route_chat} onChange={(on) => void setRouteChat(on)} />
            </Row>
            <Row title={status.url} detail={status.version ? `Home Assistant ${status.version}` : "Not answering"}>
              <Button small tone="ghost" icon={Unplug} onClick={() => void disconnect()}>
                Disconnect
              </Button>
            </Row>
          </div>
        </>
      )}
    </Sheet>
  );
}
