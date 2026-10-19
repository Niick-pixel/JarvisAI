// Settings > Phone: use Jarvis from your phone on the same Wi-Fi (or over Tailscale). Off until you
// turn it on; a phone gets in only by entering the code shown here, and you can revoke it anytime.
import { RefreshCw, Smartphone, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { request } from "../api/client";
import type { PhoneStatus } from "../api/types";
import { Button, IconButton, Row, Switch } from "../ui/controls";

const phoneApi = {
  status: () => request<PhoneStatus>("/api/phone"),
  toggle: (enabled: boolean) => request<PhoneStatus>("/api/phone", { method: "POST", body: JSON.stringify({ enabled }) }),
  code: () => request<PhoneStatus>("/api/phone/code", { method: "POST" }),
  revoke: (id: string) => request<PhoneStatus>(`/api/phone/devices/${id}`, { method: "DELETE" }),
};

export default function PhoneSettings() {
  const [status, setStatus] = useState<PhoneStatus | null>(null);
  useEffect(() => {
    void phoneApi.status().then(setStatus).catch(() => undefined);
    // The code expires and phones pair while you watch: keep it current while this is open.
    const timer = window.setInterval(() => void phoneApi.status().then(setStatus).catch(() => undefined), 4000);
    return () => window.clearInterval(timer);
  }, []);
  if (!status) return <Row title="Phone" detail="Checking…" />;

  const minutes = status.code_expires_at ? Math.max(0, Math.ceil((status.code_expires_at - Date.now()) / 60000)) : 0;
  return (
    <>
      <Row
        title="Use Jarvis from your phone"
        detail={
          status.error ||
          "On the same Wi-Fi, or anywhere over Tailscale. Everything still runs on this PC; a phone only gets in with the code below."
        }
      >
        <Switch label="Use Jarvis from your phone" checked={status.enabled} onChange={(on) => void phoneApi.toggle(on).then(setStatus)} />
      </Row>
      {status.enabled && (
        <div className="flex flex-wrap items-center gap-5 py-4">
          {status.qr_svg && (
            <div className="rounded-2xl bg-white p-2" aria-label="QR code to pair a phone" dangerouslySetInnerHTML={{ __html: status.qr_svg }} />
          )}
          <div className="min-w-[200px] flex-1">
            <p className="text-[13px] text-ink-muted">Scan with your phone's camera, or open</p>
            {status.addresses.map((url) => (
              <p key={url} className="font-mono text-[13.5px] text-ink">
                {url}/pair
              </p>
            ))}
            <p className="mt-3 text-[13px] text-ink-muted">and enter</p>
            <p className="font-display text-[34px] font-semibold tracking-[0.25em] text-ink">{status.code || "------"}</p>
            <div className="mt-1 flex items-center gap-2 text-[12.5px] text-ink-faint">
              {status.code ? `Works once, for ${minutes} more minute${minutes === 1 ? "" : "s"}.` : "Expired."}
              <Button small tone="ghost" icon={RefreshCw} onClick={() => void phoneApi.code().then(setStatus)}>
                New code
              </Button>
            </div>
          </div>
        </div>
      )}
      {status.devices.map((device) => (
        <Row
          key={device.id}
          title={device.name}
          detail={`Paired ${new Date(device.created_at).toLocaleDateString()}${device.last_seen ? ` · last used ${new Date(device.last_seen).toLocaleString()}` : ""}`}
        >
          <span className="flex items-center gap-1 text-ink-faint">
            <Smartphone size={16} />
            <IconButton icon={Trash2} label={`Unpair ${device.name}`} size={30} onClick={() => void phoneApi.revoke(device.id).then(setStatus)} />
          </span>
        </Row>
      ))}
      {status.enabled && (
        <p className="pb-2 pt-1 text-[12px] leading-relaxed text-ink-faint">
          The connection is plain HTTP on your own network, so pair only on Wi-Fi you trust. Talking out loud needs a secure
          connection, so on the phone you type. Windows may ask once whether to allow Jarvis on private networks - say yes.
        </p>
      )}
    </>
  );
}
