import { useCallback, useEffect, useState } from "react";
import { addDays, formatDebugTime, getBjtNowParts, loadDebugTime, type NowState } from "./bjt";
import { loadArchiveDay, loadArchiveIndex, loadToday } from "./data";
import { parseTodayIssue, type TodayIssue } from "./types";

const LAST_GOOD_KEY = "lastGoodTodayJson";
const LAST_GOOD_DATE_KEY = "lastGoodDateKey";
const LAST_FETCHED_AT_KEY = "lastFetchedAtBjt";

const RETRY_FAST_MS = 5000;
const RETRY_SLOW_MS = 30000;
const RETRY_SLOW_AFTER_MS = 10 * 60 * 1000;

export type TodaySignalState = "NORMAL" | "SIGNAL_LOST" | "RESTORED";

function getStoredLastGood(): TodayIssue | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(LAST_GOOD_KEY);
  if (!raw) {
    return null;
  }
  try {
    return parseTodayIssue(JSON.parse(raw));
  } catch {
    return null;
  }
}

export function useTodayData({ bjtDateKey, nowState }: { bjtDateKey: string; nowState: NowState }) {
  const [issue, setIssue] = useState<TodayIssue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [signalState, setSignalState] = useState<TodaySignalState>("NORMAL");
  const [signalSince, setSignalSince] = useState<number | null>(null);
  const [lastRetryAt, setLastRetryAt] = useState<number | null>(null);
  const [archivedIssue, setArchivedIssue] = useState<TodayIssue | null>(null);
  const [archivedError, setArchivedError] = useState<string | null>(null);
  const [lastGoodIssue, setLastGoodIssue] = useState<TodayIssue | null>(() => getStoredLastGood());

  const storeLastGood = useCallback((payload: TodayIssue) => {
    if (typeof window === "undefined") {
      return;
    }
    const fetchedAt = getBjtNowParts(loadDebugTime());
    window.localStorage.setItem(LAST_GOOD_KEY, JSON.stringify(payload));
    window.localStorage.setItem(LAST_GOOD_DATE_KEY, payload.date);
    window.localStorage.setItem(LAST_FETCHED_AT_KEY, formatDebugTime(fetchedAt.parts));
    setLastGoodIssue(payload);
  }, []);

  const loadIssue = useCallback(
    async (options?: { cacheBust?: boolean; reason?: string }) => {
      setError(null);
      const cacheBust = options?.cacheBust ? Date.now().toString() : undefined;
      try {
        const data = await loadToday(cacheBust);
        const now = getBjtNowParts(loadDebugTime());
        if (data.date !== now.bjtDateKey) {
          setSignalState("SIGNAL_LOST");
          setSignalSince((prev) => prev ?? Date.now());
          return;
        }
        setIssue(data);
        storeLastGood(data);
        setSignalSince(null);
        setSignalState((prev) => (prev !== "NORMAL" ? "RESTORED" : "NORMAL"));
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setError(message);
        setSignalState("SIGNAL_LOST");
        setSignalSince((prev) => prev ?? Date.now());
      }
    },
    [storeLastGood]
  );

  const retryNow = useCallback(() => {
    setLastRetryAt(Date.now());
    loadIssue({ cacheBust: true, reason: "manual" });
  }, [loadIssue]);

  useEffect(() => {
    loadIssue();
  }, [loadIssue]);

  useEffect(() => {
    const handleRefresh = () => {
      if (document.visibilityState === "visible") {
        loadIssue();
      }
    };

    window.addEventListener("focus", handleRefresh);
    document.addEventListener("visibilitychange", handleRefresh);

    return () => {
      window.removeEventListener("focus", handleRefresh);
      document.removeEventListener("visibilitychange", handleRefresh);
    };
  }, [loadIssue]);

  useEffect(() => {
    if (signalState !== "RESTORED") {
      return;
    }
    const timer = window.setTimeout(() => {
      setSignalState("NORMAL");
    }, 2500);
    return () => window.clearTimeout(timer);
  }, [signalState]);

  const needsArchiveFallback = nowState === "OFFLINE" || (signalState === "SIGNAL_LOST" && !lastGoodIssue);

  useEffect(() => {
    if (!needsArchiveFallback) {
      return;
    }
    let active = true;
    const yesterdayKey = addDays(bjtDateKey, -1);
    setArchivedError(null);
    setArchivedIssue(null);
    loadArchiveIndex()
      .then((index) => {
        const entry = index.items.find((item) => item.date === yesterdayKey) ?? index.items[0];
        if (!entry) {
          throw new Error("Archive index empty");
        }
        return loadArchiveDay(entry.date, entry.run_id);
      })
      .then((data) => {
        if (!active) return;
        setArchivedIssue(data);
      })
      .catch((err: Error) => {
        if (!active) return;
        setArchivedError(err.message);
      });
    return () => {
      active = false;
    };
  }, [bjtDateKey, needsArchiveFallback]);

  useEffect(() => {
    if (nowState === "OFFLINE") {
      return;
    }
    if (signalState !== "SIGNAL_LOST") {
      return;
    }
    const start = signalSince ?? Date.now();
    const elapsed = Date.now() - start;
    const interval = elapsed > RETRY_SLOW_AFTER_MS ? RETRY_SLOW_MS : RETRY_FAST_MS;
    const timer = window.setTimeout(() => {
      setLastRetryAt(Date.now());
      loadIssue({ cacheBust: true, reason: "retry" });
    }, interval);
    return () => window.clearTimeout(timer);
  }, [loadIssue, nowState, signalSince, signalState]);

  const displayIssue = signalState === "NORMAL" ? issue : lastGoodIssue ?? archivedIssue ?? issue;

  return {
    archivedError,
    archivedIssue,
    displayIssue,
    error,
    issue,
    lastGoodIssue,
    lastRetryAt,
    loadIssue,
    retryNow,
    signalState
  };
}
