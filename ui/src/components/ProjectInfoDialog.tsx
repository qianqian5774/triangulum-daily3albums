import { useEffect, useRef } from "react";
import { useT } from "../lib/ui-settings";

const REPO_URL = "https://github.com/qianqian5774/triangulum-daily3albums";

interface ProjectInfoDialogProps {
  open: boolean;
  onClose: () => void;
}

export function ProjectInfoDialog({ open, onClose }: ProjectInfoDialogProps) {
  const tx = useT();
  const closeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    closeRef.current?.focus();
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose, open]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[90] flex items-center justify-center px-4 py-6" role="presentation">
      <button
        type="button"
        className="absolute inset-0 cursor-default bg-void-black/80 backdrop-blur-md"
        aria-label={tx("about.close")}
        onClick={onClose}
      />
      <section
        className="hud-border relative z-10 flex max-h-[min(88vh,42rem)] w-full max-w-2xl flex-col overflow-auto rounded-card bg-panel-900/95 p-5 shadow-hard-xl md:p-7"
        role="dialog"
        aria-modal="true"
        aria-labelledby="project-info-title"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="ui-kicker text-clinical-white/50">{tx("about.eyebrow")}</p>
            <h2 id="project-info-title" className="mt-2 text-2xl font-semibold uppercase tracking-tightish">
              {tx("about.title")}
            </h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="ui-button border-panel-700/80 text-clinical-white/70 hover:border-signal-accent/60 hover:text-signal-accent"
          >
            {tx("about.close")}
          </button>
        </div>
        <div className="mt-6 space-y-4 text-base leading-7 text-clinical-white/76">
          <p>{tx("about.body")}</p>
          <p>{tx("about.schedule")}</p>
          <p>{tx("about.static")}</p>
          <p>{tx("about.archive")}</p>
        </div>
        <div className="mt-7 flex flex-wrap gap-3">
          <a
            className="ui-button border-signal-accent/70 text-signal-accent hover:border-signal-accent hover:text-signal-accent/90"
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            {tx("about.github")}
          </a>
        </div>
      </section>
    </div>
  );
}
