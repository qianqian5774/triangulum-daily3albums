import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Hud } from "./components/Hud";
import { NoiseOverlay } from "./components/NoiseOverlay";
import { ArchiveRoute } from "./routes/Archive";
import { TodayRoute } from "./routes/Today";
import {
  formatBjtTime,
  formatCountdown,
  formatDebugTime,
  getBjtNowParts,
  getNextUnlock,
  loadDebugTime,
  parseDebugTime,
  readDebugTimeParam,
  resolveNowState,
  saveDebugTime
} from "./lib/bjt";
import { copy } from "./strings/copy";
import { t } from "./strings/t";

export type HudStatus = "OK" | "DEGRADED" | "ERROR";

export interface HudState {
  status: HudStatus;
  marqueeItems: string[];
  bjtTime: string;
  windowLabel: string;
  nextUnlockLabel: string;
  countdownLabel: string;
  statusMessage?: string | null;
  debugActive?: boolean;
  lastSuccess?: string | null;
}

interface HudContextValue {
  hud: HudState;
  updateHud: (next: Partial<HudState>) => void;
}

export const HudContext = createContext<HudContextValue | null>(null);

const defaultHud: HudState = {
  status: "DEGRADED",
  marqueeItems: copy.system.marqueeFallback,
  bjtTime: "--:--:--",
  windowLabel: t("hud.window.booting"),
  nextUnlockLabel: t("hud.nextUnlock"),
  countdownLabel: "T-00:00:00",
  statusMessage: t("system.status.booting"),
  debugActive: false,
  lastSuccess: null
};

function App() {
  const [hud, setHud] = useState<HudState>(defaultHud);
  const location = useLocation();

  const updateHud = useCallback((next: Partial<HudState>) => {
    setHud((prev) => ({ ...prev, ...next }));
  }, []);

  const contextValue = useMemo(() => ({ hud, updateHud }), [hud, updateHud]);

  useEffect(() => {
    const param = readDebugTimeParam(location.search);
    if (!param) {
      return;
    }
    const parsed = parseDebugTime(param);
    if (!parsed) {
      return;
    }
    saveDebugTime(formatDebugTime(parsed));
  }, [location.search]);

  useEffect(() => {
    const tick = () => {
      const now = getBjtNowParts(loadDebugTime());
      const { state, slotId } = resolveNowState(now.secondsSinceMidnight);
      const windowMap: Record<string, string> = {
        SLOT0: "06:00–11:59",
        SLOT1: "12:00–17:59",
        SLOT2: "18:00–23:59"
      };
      const windowLabel =
        state === "OFFLINE"
          ? t("hud.window.offline")
          : `${t("hud.window.label")} ${windowMap[state]} / ${t("hud.window.slot")} ${slotId ?? 0}`;
      const nextUnlock = getNextUnlock(now);
      const nextUnlockLabel =
        state === "OFFLINE"
          ? `${t("hud.nextBoot")} ${nextUnlock.label}`
          : `${t("hud.nextUnlock")} ${nextUnlock.label}`;
      const countdownLabel = `${t("hud.countdownPrefix")} ${formatCountdown(nextUnlock.targetMs - now.nowMs)}`;
      setHud((prev) => ({
        ...prev,
        bjtTime: formatBjtTime(now.parts),
        windowLabel,
        nextUnlockLabel,
        countdownLabel,
        debugActive: now.source === "debug"
      }));
    };
    tick();
    const timer = window.setInterval(tick, 500);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <HudContext.Provider value={contextValue}>
      <div className="min-h-screen bg-void-black text-clinical-white">
        <Hud
          status={hud.status}
          marqueeItems={hud.marqueeItems}
          bjtTime={hud.bjtTime}
          windowLabel={hud.windowLabel}
          nextUnlockLabel={hud.nextUnlockLabel}
          countdownLabel={hud.countdownLabel}
          statusMessage={hud.statusMessage}
          debugActive={hud.debugActive}
          lastSuccess={hud.lastSuccess}
        />
        <main className="mx-auto flex w-full max-w-[90rem] flex-col gap-10 px-4 py-10 md:px-6">
          <Routes>
            <Route path="/" element={<TodayRoute />} />
            <Route path="/archive" element={<ArchiveRoute />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <NoiseOverlay />
      </div>
    </HudContext.Provider>
  );
}

export default App;
