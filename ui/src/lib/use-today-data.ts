import { useCallback, useEffect, useState } from "react";
import { addDays, formatDebugTime, getBjtNowParts, loadDebugTime, type NowState } from "./bjt";
import {
  loadArchiveDay,
  loadArchiveIndex,
  loadToday,
  normalizeDataLoadError,
  type DataLoadDiagnostic,
  type DataLoadError,
  type DataLoadErrorCode
} from "./data";
import { parseTodayIssue, type TodayIssue } from "./types";

const LAST_GOOD_KEY = "lastGoodTodayJson";
const LAST_GOOD_DATE_KEY = "lastGoodDateKey";
const LAST_FETCHED_AT_KEY = "lastFetchedAtBjt";

const RETRY_FAST_MS = 5000;
const RETRY_SLOW_MS = 30000;
const RETRY_SLOW_AFTER_MS = 10 * 60 * 1000;

export type TodaySignalState = "NORMAL" | "SIGNAL_LOST" | "RESTORED";
export type TodayRecoverySource = "last_good" | "archive" | null;
export type TodayDataDiagnostic =
  | DataLoadDiagnostic
  | { code: "stale_data"; resource: "today"; expectedDate: string; actualDate: string }
  | {
      code: "fallback_used";
      resource: "today_recovery";
      source: Exclude<TodayRecoverySource, null>;
      reason: "current_unavailable" | "offline_state";
    }
  | { code: "recovery_exhausted"; resource: "today_recovery" };

interface TodayRecoveryFailure {
  code: DataLoadErrorCode | "legitimate_empty";
  message: string;
  error?: DataLoadError;
}

export function getTodayDateDiagnostics(expectedDate: string, actualDate: string): TodayDataDiagnostic[] {
  return expectedDate === actualDate
    ? []
    : [{ code: "stale_data", resource: "today", expectedDate, actualDate }];
}

export function buildTodayDataDiagnostics({
  loadDiagnostics,
  archiveDiagnostics,
  recoverySource,
  signalState,
  nowState,
  recoveryFailed
}: {
  loadDiagnostics: TodayDataDiagnostic[];
  archiveDiagnostics: DataLoadDiagnostic[];
  recoverySource: TodayRecoverySource;
  signalState: TodaySignalState;
  nowState: NowState;
  recoveryFailed: boolean;
}): TodayDataDiagnostic[] {
  const diagnostics: TodayDataDiagnostic[] = [...loadDiagnostics, ...archiveDiagnostics];
  if (recoverySource) {
    diagnostics.push({
      code: "fallback_used",
      resource: "today_recovery",
      source: recoverySource,
      reason: nowState === "OFFLINE" ? "offline_state" : "current_unavailable"
    });
  } else if (signalState === "SIGNAL_LOST" && recoveryFailed) {
    diagnostics.push({ code: "recovery_exhausted", resource: "today_recovery" });
  }
  return diagnostics;
}

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
  const [dataError, setDataError] = useState<DataLoadError | null>(null);
  const [loadDiagnostics, setLoadDiagnostics] = useState<TodayDataDiagnostic[]>([]);
  const [signalState, setSignalState] = useState<TodaySignalState>("NORMAL");
  const [signalSince, setSignalSince] = useState<number | null>(null);
  const [lastRetryAt, setLastRetryAt] = useState<number | null>(null);
  const [archivedIssue, setArchivedIssue] = useState<TodayIssue | null>(null);
  const [archivedFailure, setArchivedFailure] = useState<TodayRecoveryFailure | null>(null);
  const [archiveDiagnostics, setArchiveDiagnostics] = useState<DataLoadDiagnostic[]>([]);
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
      setDataError(null);
      setLoadDiagnostics([]);
      const cacheBust = options?.cacheBust ? Date.now().toString() : undefined;
      try {
        const result = await loadToday(cacheBust);
        const data = result.data;
        const now = getBjtNowParts(loadDebugTime());
        if (data.date !== now.bjtDateKey) {
          setLoadDiagnostics([...result.diagnostics, ...getTodayDateDiagnostics(now.bjtDateKey, data.date)]);
          setSignalState("SIGNAL_LOST");
          setSignalSince((prev) => prev ?? Date.now());
          return;
        }
        setLoadDiagnostics(result.diagnostics);
        setArchiveDiagnostics([]);
        setArchivedFailure(null);
        setIssue(data);
        storeLastGood(data);
        setSignalSince(null);
        setSignalState((prev) => (prev !== "NORMAL" ? "RESTORED" : "NORMAL"));
      } catch (err) {
        setDataError(normalizeDataLoadError(err, "today"));
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
    setArchivedFailure(null);
    setArchiveDiagnostics([]);
    setArchivedIssue(null);
    void (async () => {
      try {
        const indexResult = await loadArchiveIndex();
        if (!active) return;
        setArchiveDiagnostics(indexResult.diagnostics);
        const entry = indexResult.data.items.find((item) => item.date === yesterdayKey) ?? indexResult.data.items[0];
        if (!entry) {
          setArchivedFailure({ code: "legitimate_empty", message: "Archive index empty" });
          return;
        }
        const archiveResult = await loadArchiveDay(entry.date, entry.run_id);
        if (!active) return;
        setArchiveDiagnostics([...indexResult.diagnostics, ...archiveResult.diagnostics]);
        setArchivedIssue(archiveResult.data);
      } catch (err) {
        if (!active) return;
        const error = normalizeDataLoadError(err, "archive_index");
        setArchivedFailure({ code: error.code, message: error.message, error });
      }
    })();
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
  const recoverySource: TodayRecoverySource = signalState === "SIGNAL_LOST"
    ? lastGoodIssue
      ? "last_good"
      : archivedIssue
        ? "archive"
        : null
    : nowState === "OFFLINE" && archivedIssue
      ? "archive"
      : null;
  const diagnostics = buildTodayDataDiagnostics({
    loadDiagnostics,
    archiveDiagnostics,
    recoverySource,
    signalState,
    nowState,
    recoveryFailed: Boolean(archivedFailure)
  });

  return {
    archivedError: archivedFailure?.message ?? null,
    archivedErrorCode: archivedFailure?.code ?? null,
    archivedFailure,
    archivedIssue,
    dataError,
    diagnostics,
    displayIssue,
    error: dataError?.message ?? null,
    errorCode: dataError?.code ?? null,
    issue,
    lastGoodIssue,
    lastRetryAt,
    loadIssue,
    recoverySource,
    retryNow,
    signalState
  };
}
