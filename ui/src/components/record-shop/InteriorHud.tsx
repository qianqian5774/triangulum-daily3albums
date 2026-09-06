import type { RecordShopCopy } from "../../strings/copy";
import type { RecordShopDay, RecordShopWindow } from "./catalog";
import type { RecordShopCue } from "./audio";

interface InteriorHudProps {
  copy: RecordShopCopy["interior"];
  currentDate: string;
  activeDate: string;
  recentDays: RecordShopDay[];
  bjtTime: string;
  status: "OFFLINE" | "READY" | "ON";
  note: string;
  windows: RecordShopWindow[];
  unlockedWindows: number;
  dateMenuOpen: boolean;
  onToggleDateMenu: () => void;
  onChooseDate: (date: string) => void;
  onCue: (cue: RecordShopCue) => void;
}

export function InteriorHud({
  copy,
  currentDate,
  activeDate,
  recentDays,
  bjtTime,
  status,
  note,
  windows,
  unlockedWindows,
  dateMenuOpen,
  onToggleDateMenu,
  onChooseDate,
  onCue
}: InteriorHudProps) {
  const localizedStatus = status === "OFFLINE" ? copy.offline : status === "READY" ? copy.ready : copy.on;

  return (
    <section className="record-shop__interior-hud" data-testid="interior-hud" aria-label={copy.hudAria}>
      <div className="record-shop__hud-hardware" aria-hidden="true">
        <i className="record-shop__hud-rod record-shop__hud-rod--left"><span /></i>
        <i className="record-shop__hud-rod record-shop__hud-rod--right"><span /></i>
      </div>
      <div className="record-shop__hud-bezel">
        <div className="record-shop__hud-glass">
          <header className="record-shop__hud-brand">
            <strong>TRIANGULUM DAILY</strong>
            <span className="record-shop__hud-lamp" data-status={status} aria-hidden="true" />
          </header>
          <div className="record-shop__hud-readout">
            <button
              className="record-shop__hud-date"
              type="button"
              aria-haspopup="listbox"
              aria-expanded={dateMenuOpen}
              onPointerEnter={() => onCue("hover")}
              onClick={() => { onCue("press"); onToggleDateMenu(); }}
            >
              <span>{copy.date}</span>
              <b>{activeDate.slice(5)}</b>
              <i aria-hidden="true">⌄</i>
            </button>
            <span className="record-shop__hud-status" data-status={status}>
              <small>{copy.device}</small>
              <b>{localizedStatus}</b>
            </span>
            <time className="record-shop__hud-time">
              <small>{copy.bjt}</small>
              <b>{bjtTime}</b>
            </time>
          </div>
          <div className="record-shop__hud-progress">
            <small className="record-shop__hud-note">{note}</small>
            <div className="record-shop__hud-windows" aria-hidden="true">{windows.map((window, index) => <span key={`${window.slotId}-${window.label}`} data-unlocked={index < unlockedWindows}>{window.shortLabel}</span>)}</div>
          </div>
        </div>
      </div>
      {dateMenuOpen ? (
        <div className="record-shop__date-menu" role="listbox" aria-label={copy.recentDates}>
          {recentDays.map((day) => (
            <button
              key={day.date}
              type="button"
              role="option"
              aria-selected={day.date === activeDate}
              onPointerEnter={() => onCue("hover")}
              onClick={() => { onCue("history"); onChooseDate(day.date); }}
            >
              <span>{day.date.slice(5)}</span>
              <small>{day.date === currentDate ? copy.current : copy.history}</small>
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
