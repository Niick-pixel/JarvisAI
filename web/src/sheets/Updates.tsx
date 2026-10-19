// Settings > Updates: which version this is, whether it keeps itself current, and a button to
// look now. Updating itself happens from the sidebar row, once a new version is verified.
import { useEffect } from "react";
import { useUpdates } from "../store/updates";
import { Button, Row, Switch } from "../ui/controls";

function mb(bytes: number): string {
  return `${Math.round(bytes / 1e6).toLocaleString()} MB`;
}

export default function Updates() {
  const { status, refresh, check, setAuto, updateNow } = useUpdates();
  useEffect(() => void refresh(), [refresh]);
  if (!status) return <Row title="Version" detail="Checking…" />;

  const detail = (() => {
    switch (status.state) {
      case "checking":
        return "Checking for a new version…";
      case "up_to_date":
        return "This is the latest version.";
      case "available":
        return status.can_install
          ? `Jarvis ${status.latest} is available.`
          : `Jarvis ${status.latest} is available. A copy run from source updates with git pull.`;
      case "downloading":
        return `Getting Jarvis ${status.latest}… ${mb(status.bytes_done)} of ${mb(status.bytes_total)}`;
      case "ready":
        return `Jarvis ${status.latest} is downloaded and verified.`;
      case "installing":
        return "Installing. Jarvis will reopen in a moment.";
      case "failed":
        return status.detail;
      default:
        return "Updates come from this app's GitHub releases.";
    }
  })();

  return (
    <>
      <Row title={`Jarvis ${status.current}`} detail={detail}>
        {status.state === "ready" ? (
          <Button small tone="primary" onClick={() => void updateNow()}>
            Restart to update
          </Button>
        ) : status.can_install &&
          (status.state === "available" || status.state === "downloading") ? (
          <Button
            small
            tone="primary"
            disabled={status.state === "downloading"}
            onClick={() => void updateNow()}
          >
            {status.state === "downloading" ? "Updating…" : "Update now"}
          </Button>
        ) : (
          <Button
            small
            tone="ghost"
            disabled={status.state === "checking"}
            onClick={() => void check()}
          >
            Check now
          </Button>
        )}
      </Row>
      <Row
        title="Update automatically"
        detail="Once a day, ask GitHub whether there is a new version and fetch it in the background. Nothing about you is sent."
      >
        <Switch
          label="Update automatically"
          checked={status.auto}
          onChange={(on) => void setAuto(on)}
        />
      </Row>
    </>
  );
}
