import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

function millisecondsUntilNextCycle() {
  const now = new Date();
  const next = new Date(now);
  next.setHours(24, 0, 0, 0);
  return Math.max(0, next.getTime() - now.getTime());
}

function formatCountdown(totalMilliseconds: number) {
  const totalSeconds = Math.floor(totalMilliseconds / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const centiseconds = Math.floor((totalMilliseconds % 1000) / 10);
  return {
    hours: String(hours).padStart(2, "0"),
    minutes: String(minutes).padStart(2, "0"),
    seconds: String(seconds).padStart(2, "0"),
    centiseconds: String(centiseconds).padStart(2, "0")
  };
}

export function BioClock() {
  const [remainingMs, setRemainingMs] = useState(millisecondsUntilNextCycle());
  const { t } = useTranslation();

  useEffect(() => {
    const id = window.setInterval(() => {
      setRemainingMs(millisecondsUntilNextCycle());
    }, 100);
    return () => window.clearInterval(id);
  }, []);

  const value = useMemo(() => formatCountdown(remainingMs), [remainingMs]);

  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] uppercase tracking-[0.4em] text-clinical-white/50">
        {t("hud.clock.next_cycle")}
      </span>
      <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-[0.3em] text-clinical-white/70">
        <span className="text-acid-green/80">{t("hud.clock.tminus")}</span>
        <span className="rounded-hud border border-panel-700/70 px-2 py-1 text-clinical-white/80">
          {value.hours}
          <span className="pulse-separator">:</span>
          {value.minutes}
          <span className="pulse-separator">:</span>
          {value.seconds}
          <span className="pulse-separator">:</span>
          {value.centiseconds}
        </span>
      </div>
      <span className="text-[10px] uppercase tracking-[0.3em] text-clinical-white/40">
        {t("hud.clock.estimate")}
      </span>
    </div>
  );
}
