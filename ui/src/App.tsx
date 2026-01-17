import { createContext, useCallback, useMemo, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Hud } from "./components/Hud";
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

function App() {
  const [hud, setHud] = useState<HudState>(defaultHud);

  const updateHud = useCallback((next: Partial<HudState>) => {
    setHud((prev) => ({ ...prev, ...next }));
  }, []);

  const contextValue = useMemo(() => ({ hud, updateHud }), [hud, updateHud]);

  return (
    <HudContext.Provider value={contextValue}>
      <div className="min-h-screen bg-void-black text-clinical-white">
        <Hud batchId={hud.batchId} status={hud.status} marqueeItems={hud.marqueeItems} />
        <main className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-10 md:px-6">
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
