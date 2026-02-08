import { t } from "../strings/t";

interface AmbientOverlayProps {
  onExit: () => void;
}

export function AmbientOverlay({ onExit }: AmbientOverlayProps) {
  return (
    <div className="ambient-overlay" role="dialog" aria-label="Ambient mode">
      <div className="ambient-gradient" aria-hidden="true" />
      <div className="ambient-noise" aria-hidden="true" />
      <div className="ambient-ghost" aria-hidden="true">
        <span>{new Date().toLocaleTimeString("en-GB", { hour12: false })}</span>
      </div>
      <button
        type="button"
        onClick={onExit}
        className="ambient-exit-hint rounded-full border border-clinical-white/30 px-3 py-1 text-[10px] uppercase tracking-[0.3em] text-clinical-white/60"
      >
        {t("today.ambientExit")}
      </button>
    </div>
  );
}
