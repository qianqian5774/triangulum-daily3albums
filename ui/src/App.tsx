import { createContext, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Hud } from "./components/Hud";
import { NoiseOverlay } from "./components/NoiseOverlay";
import { ProjectInfoDialog } from "./components/ProjectInfoDialog";
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
  resolveVisualTheme,
  saveDebugTime,
  type VisualTheme
} from "./lib/bjt";
import { useLocalizedCopy, useT } from "./lib/ui-settings";

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
}

interface HudContextValue {
  hud: HudState;
  updateHud: (next: Partial<HudState>) => void;
}

export const HudContext = createContext<HudContextValue | null>(null);

function createDefaultHud(tx: (key: string) => string, marqueeFallback: string[]): HudState {
  return {
  status: "DEGRADED",
  marqueeItems: marqueeFallback,
  bjtTime: "--:--:--",
  windowLabel: tx("hud.window.booting"),
  nextUnlockLabel: tx("hud.nextUnlock"),
  countdownLabel: "T-00:00:00",
  statusMessage: tx("system.status.booting"),
  debugActive: false
  };
}

function App() {
  const tx = useT();
  const localizedCopy = useLocalizedCopy();
  const [hud, setHud] = useState<HudState>(() =>
    createDefaultHud(tx, [...localizedCopy.system.marqueeFallback])
  );
  const [aboutOpen, setAboutOpen] = useState(false);
  const [visualTheme, setVisualTheme] = useState<VisualTheme>(() =>
    resolveVisualTheme(getBjtNowParts(loadDebugTime()).secondsSinceMidnight)
  );
  const [themeTransition, setThemeTransition] = useState<VisualTheme | null>(null);
  const themeTransitionTimerRef = useRef<number | null>(null);
  const location = useLocation();

  const updateHud = useCallback((next: Partial<HudState>) => {
    setHud((prev) => ({ ...prev, ...next }));
  }, []);

  const contextValue = useMemo(() => ({ hud, updateHud }), [hud, updateHud]);

  useEffect(() => {
    const param = readDebugTimeParam(
      location.search,
      typeof window === "undefined" ? "" : window.location.search
    );
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
      const nextVisualTheme = resolveVisualTheme(now.secondsSinceMidnight);
      const { state } = resolveNowState(now.secondsSinceMidnight);
      const windowMap: Record<string, string> = {
        SLOT0: "06:00–11:59",
        SLOT1: "12:00–17:59",
        SLOT2: "18:00–23:59"
      };
      const windowLabel =
        state === "OFFLINE"
          ? tx("hud.window.offline")
          : `${tx("hud.window.label")} ${windowMap[state]}`;
      const nextUnlock = getNextUnlock(now);
      const nextUnlockLabel =
        state === "OFFLINE"
          ? `${tx("hud.nextBoot")} ${nextUnlock.label}`
          : `${tx("hud.nextUnlock")} ${nextUnlock.label}`;
      const countdownLabel = `${tx("hud.countdownPrefix")} ${formatCountdown(nextUnlock.targetMs - now.nowMs)}`;
      setVisualTheme((prev) => {
        if (prev === nextVisualTheme) {
          return prev;
        }
        setThemeTransition(nextVisualTheme);
        if (themeTransitionTimerRef.current) {
          window.clearTimeout(themeTransitionTimerRef.current);
        }
        themeTransitionTimerRef.current = window.setTimeout(() => {
          setThemeTransition(null);
          themeTransitionTimerRef.current = null;
        }, 1400);
        return nextVisualTheme;
      });
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
    return () => {
      window.clearInterval(timer);
      if (themeTransitionTimerRef.current) {
        window.clearTimeout(themeTransitionTimerRef.current);
        themeTransitionTimerRef.current = null;
      }
    };
  }, [tx]);

  useEffect(() => {
    document.documentElement.dataset.theme = visualTheme;
    return () => {
      delete document.documentElement.dataset.theme;
    };
  }, [visualTheme]);

  return (
    <HudContext.Provider value={contextValue}>
      <div
        className="theme-shell min-h-screen text-clinical-white"
        data-theme={visualTheme}
        data-transition-active={themeTransition ? "signal-glitch" : undefined}
      >
        {themeTransition ? (
          <div
            className={`theme-transition-overlay theme-transition-${themeTransition}`}
            aria-hidden="true"
          />
        ) : null}
        <Hud
          status={hud.status}
          marqueeItems={hud.marqueeItems}
          bjtTime={hud.bjtTime}
          windowLabel={hud.windowLabel}
          nextUnlockLabel={hud.nextUnlockLabel}
          countdownLabel={hud.countdownLabel}
          statusMessage={hud.statusMessage}
          debugActive={hud.debugActive}
          onOpenAbout={() => setAboutOpen(true)}
        />
        <main className="app-main mx-auto flex w-full max-w-[90rem] flex-col gap-10 px-4 pb-10 md:px-6">
          <Routes>
            <Route path="/" element={<TodayRoute />} />
            <Route path="/archive" element={<ArchiveRoute />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        <ProjectInfoDialog open={aboutOpen} onClose={() => setAboutOpen(false)} />
        <NoiseOverlay />
      </div>
    </HudContext.Provider>
  );
}

export default App;
