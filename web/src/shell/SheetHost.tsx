// Renders whichever sheet is open - only ever one.
import { AnimatePresence } from "framer-motion";
import AgentsSheet from "../sheets/AgentsSheet";
import CouncilSheet from "../sheets/CouncilSheet";
import KnowledgeSheet from "../sheets/KnowledgeSheet";
import MemorySheet from "../sheets/MemorySheet";
import SettingsSheet from "../sheets/SettingsSheet";
import { type SheetName, useUi } from "../store/ui";

const SHEETS: Record<SheetName, () => JSX.Element> = {
  memory: MemorySheet,
  knowledge: KnowledgeSheet,
  agents: AgentsSheet,
  settings: SettingsSheet,
  council: CouncilSheet,
};

export default function SheetHost() {
  const sheet = useUi((s) => s.sheet);
  const Current = sheet ? SHEETS[sheet] : null;
  return <AnimatePresence>{Current && <Current key={sheet} />}</AnimatePresence>;
}
