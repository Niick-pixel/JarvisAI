// Code: point Jarvis at a project folder and work on it in chat. It reads the code freely; every
// file it writes and every command it runs asks you first. A coder model is used when installed.
import { FolderOpen, FolderCode, Play } from "lucide-react";
import Sheet from "../shell/Sheet";
import { folderName, useCode } from "../store/code";
import { useDownloads } from "../store/downloads";
import { useLibrary } from "../store/library";
import { useUi } from "../store/ui";
import { Button, Row } from "../ui/controls";

export default function CodeSheet() {
  const { project, recent, choose, use, start } = useCode();
  const models = useLibrary((s) => s.models);
  const coder = models.find((m) => /coder|code/i.test(m.model.display_name));

  const go = async () => {
    if (await start()) useUi.getState().closeSheet();
  };

  return (
    <Sheet title="Code" subtitle="A coding agent on a folder of yours. Reads freely; every write and command asks you first." width={680}>
      <div className="divide-y divide-ink/[0.06]">
        <Row title={project ? folderName(project) : "No project yet"} detail={project || "Choose the folder of the project you want to work on."}>
          <Button small icon={FolderOpen} onClick={() => void choose()}>
            {project ? "Change" : "Choose folder"}
          </Button>
        </Row>
        <Row
          title={coder ? `Model: ${coder.model.display_name}` : "No coder model installed"}
          detail={
            coder
              ? "Code mode uses it automatically."
              : "Your general model will do. A coder model (Qwen2.5 Coder, Qwen3 Coder 30B-A3B, DeepSeek Coder) is noticeably better at real code."
          }
        >
          {!coder && (
            <Button small tone="ghost" onClick={() => void useDownloads.getState().show()}>
              Get one
            </Button>
          )}
        </Row>
      </div>
      {recent.length > 1 && (
        <div className="mt-5">
          <p className="mb-1 text-[13px] font-semibold text-ink-muted">Recent projects</p>
          {recent
            .filter((p) => p !== project)
            .map((p) => (
              <button key={p} type="button" onClick={() => use(p)} className="flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-left hover:bg-ink/[0.04]">
                <FolderCode size={17} className="shrink-0 text-ink-faint" />
                <span className="min-w-0">
                  <span className="block text-[14px] text-ink">{folderName(p)}</span>
                  <span className="block truncate text-[12px] text-ink-faint">{p}</span>
                </span>
              </button>
            ))}
        </div>
      )}
      <div className="mt-6 flex justify-end">
        <Button tone="primary" icon={Play} onClick={() => void go()}>
          Start coding
        </Button>
      </div>
    </Sheet>
  );
}
