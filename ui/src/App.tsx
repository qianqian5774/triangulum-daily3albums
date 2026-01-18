import { createContext, useCallback, useMemo, useState, type CSSProperties } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Hud } from "./components/Hud";
import { FLAGS } from "./config/flags";
import { ArchiveRoute } from "./routes/Archive";
import { TodayRoute } from "./routes/Today";

export type HudStatus = "OK" | "DEGRADED" | "ERROR";

export interface HudState {
  batchId: string;
  status: HudStatus;
  marqueeItems: string[];
}

interface HudContextValue {
  hud: HudState;
  updateHud: (next: Partial<HudState>) => void;
}

export const HudContext = createContext<HudContextValue | null>(null);

const defaultHud: HudState = {
  batchId: "BOOTING",
  status: "DEGRADED",
  marqueeItems: ["Triangulum intake stable", "Awaiting data stream"]
};

const UI_SCALE_STORAGE_KEY = "ui.scale";

function App() {
  const [hud, setHud] = useState<HudState>(defaultHud);
  const [scale, setScale] = useState(() => {
    if (!FLAGS.scaleControl) {
      return 1;
    }
    const stored = Number.parseFloat(localStorage.getItem(UI_SCALE_STORAGE_KEY) ?? "1");
    return Number.isFinite(stored) ? stored : 1;
  });

  const updateHud = useCallback((next: Partial<HudState>) => {
    setHud((prev) => ({ ...prev, ...next }));
  }, []);

  const updateScale = useCallback((next: number) => {
    setScale(next);
    localStorage.setItem(UI_SCALE_STORAGE_KEY, String(next));
  }, []);

  const contextValue = useMemo(() => ({ hud, updateHud }), [hud, updateHud]);

  return (
    <HudContext.Provider value={contextValue}>
      <div
        className="min-h-screen bg-void-black text-clinical-white ui-root"
        style={FLAGS.scaleControl ? ({ "--ui-scale": scale } as CSSProperties) : undefined}
      >
        <Hud
          batchId={hud.batchId}
          status={hud.status}
          marqueeItems={hud.marqueeItems}
          scale={scale}
          onScaleChange={updateScale}
        />
        <main
          className={`mx-auto flex w-full ${
            FLAGS.dominantViewport ? "max-w-[1200px]" : "max-w-5xl"
          } flex-col gap-10 px-4 py-10 md:px-6`}
        >
          <Routes>
            <Route path="/" element={<TodayRoute />} />
            <Route path="/archive" element={<ArchiveRoute />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </HudContext.Provider>
  );
}

export default App;
