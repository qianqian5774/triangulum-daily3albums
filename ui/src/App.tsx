import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Hud } from "./components/Hud";
import { NoiseOverlay } from "./components/NoiseOverlay";
import { ProjectInfoDialog } from "./components/ProjectInfoDialog";
import { ArchiveRoute } from "./routes/Archive";
import { RecordShopRoute } from "./routes/RecordShop";
import { TodayRoute } from "./routes/Today";
import {
  formatBjtTime,
  formatCountdown,
  getNextUnlock,
  getSlotWindowLabel,
  type VisualTheme
} from "./lib/bjt";
import { ProductClockProvider, useProductClock } from "./lib/product-clock";
import { useLocalizedCopy, useT } from "./lib/ui-settings";

export type HudStatus = "OK" | "DEGRADED" | "ERROR" | "OFFLINE" | "ARCHIVE";

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

function AppShell() {
  const location = useLocation();
  const tx = useT();
  const localizedCopy = useLocalizedCopy();
  const { bjtNow, nowSlotId, nowState, visualTheme } = useProductClock();
  const [hud, setHud] = useState<HudState>(() =>
    createDefaultHud(tx, [...localizedCopy.system.marqueeFallback])
  );
  const [aboutOpen, setAboutOpen] = useState(false);
  const [displayVisualTheme, setDisplayVisualTheme] = useState<VisualTheme>(visualTheme);
  const [themeTransition, setThemeTransition] = useState<VisualTheme | null>(null);
  const themeTransitionTimerRef = useRef<number | null>(null);
  const recordShopActive = location.pathname === "/" || location.pathname === "/record-shop";

  const updateHud = useCallback((next: Partial<HudState>) => {
    setHud((prev) => ({ ...prev, ...next }));
  }, []);

  const contextValue = useMemo(() => ({ hud, updateHud }), [hud, updateHud]);

  useEffect(() => {
    const windowLabel =
      nowState === "OFFLINE"
        ? tx("hud.window.offline")
        : `${tx("hud.window.label")} ${getSlotWindowLabel(nowSlotId ?? 0)}`;
    const nextUnlock = getNextUnlock(bjtNow);
    const nextUnlockLabel =
      nowState === "OFFLINE"
        ? `${tx("hud.nextBoot")} ${nextUnlock.label}`
        : `${tx("hud.nextUnlock")} ${nextUnlock.label}`;
    const countdownLabel = `${tx("hud.countdownPrefix")} ${formatCountdown(nextUnlock.targetMs - bjtNow.nowMs)}`;
    setHud((prev) => ({
      ...prev,
      bjtTime: formatBjtTime(bjtNow.parts),
      windowLabel,
      nextUnlockLabel,
      countdownLabel,
      debugActive: bjtNow.source === "debug"
    }));
  }, [bjtNow, nowSlotId, nowState, tx]);

  useEffect(() => {
    if (displayVisualTheme === visualTheme) {
      return;
    }
    setThemeTransition(visualTheme);
    if (themeTransitionTimerRef.current) {
      window.clearTimeout(themeTransitionTimerRef.current);
    }
    themeTransitionTimerRef.current = window.setTimeout(() => {
      setThemeTransition(null);
      themeTransitionTimerRef.current = null;
    }, 1400);
    setDisplayVisualTheme(visualTheme);
  }, [displayVisualTheme, visualTheme]);

  useEffect(
    () => () => {
      if (themeTransitionTimerRef.current) {
        window.clearTimeout(themeTransitionTimerRef.current);
        themeTransitionTimerRef.current = null;
      }
    },
    []
  );

  useEffect(() => {
    document.documentElement.dataset.theme = displayVisualTheme;
    return () => {
      delete document.documentElement.dataset.theme;
    };
  }, [displayVisualTheme]);

  return (
    <HudContext.Provider value={contextValue}>
      <div
        className="theme-shell min-h-screen text-clinical-white"
        data-theme={displayVisualTheme}
        data-transition-active={
          !recordShopActive && themeTransition ? "signal-glitch" : undefined
        }
      >
        {!recordShopActive && themeTransition ? (
          <div
            className={`theme-transition-overlay theme-transition-${themeTransition}`}
            aria-hidden="true"
          />
        ) : null}
        {!recordShopActive ? (
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
        ) : null}
        <main
          aria-label={recordShopActive ? "Triangulum Daily record shop" : undefined}
          className={
            recordShopActive
              ? "app-main app-main-record-shop"
              : "app-main mx-auto flex w-full max-w-[90rem] flex-col gap-10 px-4 pb-10 md:px-6"
          }
        >
          <Routes>
            <Route path="/" element={<RecordShopRoute />} />
            <Route path="/today" element={<TodayRoute />} />
            <Route path="/archive" element={<ArchiveRoute />} />
            <Route path="/record-shop" element={<Navigate to="/" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
        {!recordShopActive ? (
          <>
            <ProjectInfoDialog open={aboutOpen} onClose={() => setAboutOpen(false)} />
            <NoiseOverlay />
          </>
        ) : null}
      </div>
    </HudContext.Provider>
  );
}

function App() {
  return (
    <ProductClockProvider>
      <AppShell />
    </ProductClockProvider>
  );
}

export default App;
