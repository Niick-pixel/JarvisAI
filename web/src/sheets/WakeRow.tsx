// Settings → Voice → Wake word. Turning it on fetches its three small model files (about 3.5 MB,
// checked against pinned hashes) the first time, then keeps the microphone open for it.
import { useWake } from "../store/wake";
import { Row, Switch } from "../ui/controls";

export default function WakeRow() {
  const { enabled, installing, error, setEnabled } = useWake();
  const detail = installing
    ? "Fetching the wake word model (3.5 MB)…"
    : error ||
      'Say "Hey Jarvis" to start talking. Heard on this PC only; the microphone stays on while this is on, and a badge says so.';
  return (
    <Row title="Wake word" detail={detail}>
      <Switch label="Wake word" checked={enabled} onChange={(on) => void setEnabled(on)} />
    </Row>
  );
}
