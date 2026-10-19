// Renders whichever sheet is open - only ever one.
import { AnimatePresence } from "framer-motion";
import HomeSheet from "../home/HomeSheet";
import FilesSheet from "../files/FilesSheet";
import CodeSheet from "../sheets/CodeSheet";
import ImagesSheet from "../sheets/ImagesSheet";
import TradingSheet from "../trading/TradingSheet";
import AgentsSheet from "../sheets/AgentsSheet";
import CouncilSheet from "../sheets/CouncilSheet";
import KnowledgeSheet from "../sheets/KnowledgeSheet";
import MemorySheet from "../sheets/MemorySheet";
import SettingsSheet from "../sheets/SettingsSheet";
import { type SheetName, useUi } from "../store/ui";
import SheetBoundary from "./SheetBoundary";

const SHEETS: Record<SheetName, () => JSX.Element> = {
  memory: MemorySheet,
  knowledge: KnowledgeSheet,
  agents: AgentsSheet,
  settings: SettingsSheet,
  council: CouncilSheet,
  home: HomeSheet,
  forecast: TradingSheet,
  files: FilesSheet,
  images: ImagesSheet,
  code: CodeSheet,
};

export default function SheetHost() {
  const sheet = useUi((s) => s.sheet);
  const Current = sheet ? SHEETS[sheet] : null;
  return (
    <AnimatePresence>
      {Current && sheet && (
        <SheetBoundary key={sheet} name={sheet}>
          <Current />
        </SheetBoundary>
      )}
    </AnimatePresence>
  );
}
