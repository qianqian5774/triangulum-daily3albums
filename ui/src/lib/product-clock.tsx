import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import {
  formatDebugTime,
  getBjtNowParts,
  loadDebugTime,
  parseDebugTime,
  readDebugFlagParam,
  readDebugTimeParam,
  resolveNowState,
  resolveVisualTheme,
  saveDebugTime,
  type BjtNow,
  type NowState,
  type VisualTheme
} from "./bjt";

interface ProductClockValue {
  debugTime: string | null;
  bjtNow: BjtNow;
  nowState: NowState;
  nowSlotId: number | null;
  visualTheme: VisualTheme;
  debugPanelEnabled: boolean;
  clearDebug: () => void;
  setDebugClock: (hour: number, minute: number, second?: number) => void;
}

const ProductClockContext = createContext<ProductClockValue | null>(null);

function loadInitialDebugTime() {
  if (typeof window === "undefined") return null;
  // Resolve a URL preset before the first render. Otherwise a debug link can
  // briefly adopt the real clock, start loading the wrong themed interior,
  // then switch and fetch a second full scene on mount.
  const urlDebugTime = readDebugTimeParam(window.location.search, window.location.hash);
  const parsed = urlDebugTime ? parseDebugTime(urlDebugTime) : null;
  return parsed ? formatDebugTime(parsed) : loadDebugTime();
}

export function ProductClockProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const [debugTime, setDebugTime] = useState<string | null>(() => loadInitialDebugTime());
  const [bjtNow, setBjtNow] = useState<BjtNow>(() => getBjtNowParts(debugTime));

  const applyDebugTime = useCallback((value: string | null) => {
    saveDebugTime(value);
    setDebugTime(value);
    setBjtNow(getBjtNowParts(value));
  }, []);

  useEffect(() => {
    const urlDebugTime = readDebugTimeParam(
      location.search,
      location.hash,
      typeof window === "undefined" ? "" : window.location.search,
      typeof window === "undefined" ? "" : window.location.hash
    );
    const parsed = urlDebugTime ? parseDebugTime(urlDebugTime) : null;
    if (!parsed) {
      return;
    }
    applyDebugTime(formatDebugTime(parsed));
  }, [applyDebugTime, location.hash, location.search]);

  useEffect(() => {
    const tick = () => {
      const stored = loadDebugTime();
      setDebugTime(stored);
      setBjtNow(getBjtNowParts(stored));
    };
    tick();
    const timer = window.setInterval(tick, 500);
    return () => window.clearInterval(timer);
  }, []);

  const nowStateInfo = useMemo(
    () => resolveNowState(bjtNow.secondsSinceMidnight),
    [bjtNow.secondsSinceMidnight]
  );
  const visualTheme = useMemo(
    () => resolveVisualTheme(bjtNow.secondsSinceMidnight),
    [bjtNow.secondsSinceMidnight]
  );
  const debugPanelEnabled = useMemo(
    () =>
      Boolean(debugTime) ||
      readDebugFlagParam(
        location.search,
        location.hash,
        typeof window === "undefined" ? "" : window.location.search,
        typeof window === "undefined" ? "" : window.location.hash
      ),
    [debugTime, location.hash, location.search]
  );

  const clearDebug = useCallback(() => {
    saveDebugTime(null);
    setDebugTime(null);
  }, []);

  const setDebugClock = useCallback(
    (hour: number, minute: number, second = 0) => {
      applyDebugTime(formatDebugTime({ ...bjtNow.parts, hour, minute, second }));
    },
    [applyDebugTime, bjtNow.parts]
  );

  const value = useMemo<ProductClockValue>(
    () => ({
      debugTime,
      bjtNow,
      nowState: nowStateInfo.state,
      nowSlotId: nowStateInfo.slotId,
      visualTheme,
      debugPanelEnabled,
      clearDebug,
      setDebugClock
    }),
    [
      bjtNow,
      clearDebug,
      debugPanelEnabled,
      debugTime,
      nowStateInfo.slotId,
      nowStateInfo.state,
      setDebugClock,
      visualTheme
    ]
  );

  return <ProductClockContext.Provider value={value}>{children}</ProductClockContext.Provider>;
}

export function useProductClock() {
  const context = useContext(ProductClockContext);
  if (!context) {
    throw new Error("useProductClock must be used within ProductClockProvider");
  }
  return context;
}
