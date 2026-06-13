import { useT } from "../lib/ui-settings";

interface AmbientOverlayProps {
  onExit: () => void;
}

export function AmbientOverlay({ onExit }: AmbientOverlayProps) {
  const tx = useT();
  return (
    <div className="ambient-overlay" role="dialog" aria-label={tx("today.ambientEnter")}>
      <div className="ambient-gradient" aria-hidden="true" />
      <div className="ambient-noise" aria-hidden="true" />
      <div className="ambient-grid" aria-hidden="true" />
      <div className="ambient-signal ambient-signal-a" aria-hidden="true" />
      <div className="ambient-signal ambient-signal-b" aria-hidden="true" />
      <div className="ambient-ghost" aria-hidden="true">
        <span className="ambient-standby">STANDBY</span>
        <span className="ambient-time">{new Date().toLocaleTimeString("en-GB", { hour12: false })}</span>
        <span className="ambient-subline">TRIANGULUM DAILY 3 ALBUMS</span>
      </div>
      <button
        type="button"
        onClick={onExit}
        className="ambient-exit-hint ui-button border-acid-green/70 bg-panel-900/80 text-acid-green hover:border-acid-green"
      >
        {tx("today.ambientExit")}
      </button>
    </div>
  );
}
