import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { EntryDiorama, type DioramaView, type EntryInfoKey } from "../components/record-shop/EntryDiorama";
import { InteriorGallery, preloadInterior } from "../components/record-shop/InteriorGallery";
import { useRecordShopAudio } from "../components/record-shop/audio";
import { toRecordShopDay, type RecordShopDay } from "../components/record-shop/catalog";
import { getRecentArchiveEntries } from "../lib/archive";
import { loadArchiveDay, loadArchiveIndex, normalizeDataLoadError } from "../lib/data";
import { useProductClock } from "../lib/product-clock";
import { useLocalizedCopy, useUiSettings } from "../lib/ui-settings";
import { useTodayData } from "../lib/use-today-data";
import type { RecordShopCopy } from "../strings/copy";
import "./record-shop-fonts.css";
import "./record-shop.css";
import "./record-shop-finish.css";

const DEBUG_PRESETS = [
  { copyKey: "preset0759", hour: 7, minute: 59 },
  { copyKey: "preset0800", hour: 8, minute: 0 },
  { copyKey: "preset1230", hour: 12, minute: 30 },
  { copyKey: "preset1600", hour: 16, minute: 0 },
  { copyKey: "preset2100", hour: 21, minute: 0 }
] as const;

function EntryInfoOverlay({ panel, exteriorCopy, copy, onCue, onClose }: { panel: EntryInfoKey; exteriorCopy: RecordShopCopy["exterior"]; copy: RecordShopCopy["info"]; onCue: ReturnType<typeof useRecordShopAudio>["playCue"]; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const isProject = panel === "project";

  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <section className="entry-info" role="dialog" aria-modal="true" aria-labelledby="entry-info-title">
      <button className="entry-info__backdrop" type="button" aria-label={copy.closeAria} onClick={onClose} />
      <article className="entry-info__sheet">
        <header>
          <span>{isProject ? exteriorCopy.projectInfo : exteriorCopy.dailyRhythm}</span>
          <button ref={closeRef} type="button" onPointerEnter={() => onCue("hover")} onClick={() => { onCue("press"); onClose(); }}>{copy.close}</button>
        </header>
        {isProject ? (
          <div className="entry-info__content">
            <h2 id="entry-info-title">{copy.projectTitle}</h2>
            <p>{copy.projectBody}</p>
            <p>{copy.projectSchedule}</p>
            <ul>
              <li><strong>08:00</strong><span>{copy.recordIncrement}</span></li>
              <li><strong>12:30</strong><span>{copy.recordIncrement}</span></li>
              <li><strong>16:00</strong><span>{copy.finalIncrement}</span></li>
            </ul>
            <p className="entry-info__note">{copy.projectNote}</p>
          </div>
        ) : (
          <div className="entry-info__content">
            <h2 id="entry-info-title">{copy.hoursTitle}</h2>
            <dl>
              <div><dt>00:00–07:59</dt><dd>{copy.closed}</dd></div>
              <div><dt>08:00</dt><dd>{copy.threeRecords}</dd></div>
              <div><dt>12:30</dt><dd>{copy.sixRecords}</dd></div>
              <div><dt>16:00</dt><dd>{copy.nineRecords}</dd></div>
            </dl>
            <p className="entry-info__note">{copy.bjtNote}</p>
          </div>
        )}
      </article>
    </section>
  );
}

export function RecordShopRoute() {
  const { bjtNow, nowSlotId, nowState, debugTime, debugPanelEnabled, clearDebug, setDebugClock } = useProductClock();
  const { language, setLanguage } = useUiSettings();
  const localizedCopy = useLocalizedCopy();
  const recordShopCopy = localizedCopy.recordShop;
  const [space, setSpace] = useState<"exterior" | "interior">("exterior");
  const [approaching, setApproaching] = useState(false);
  const { enabled: soundEnabled, playCue, toggleSound } = useRecordShopAudio(space, approaching);
  const [interiorImagesReady, setInteriorImagesReady] = useState(false);
  const [exteriorView, setExteriorView] = useState<DioramaView>("axonometric");
  const [entryInfo, setEntryInfo] = useState<EntryInfoKey | null>(null);
  const [entryResetKey, setEntryResetKey] = useState(0);
  const [entryReplayToken, setEntryReplayToken] = useState(0);
  const [debugOpen, setDebugOpen] = useState(false);
  const [archiveDays, setArchiveDays] = useState<RecordShopDay[]>([]);
  const [archiveError, setArchiveError] = useState<string | null>(null);
  const [assetError, setAssetError] = useState<string | null>(null);
  const { displayIssue, error: todayError } = useTodayData({
    bjtDateKey: bjtNow.bjtDateKey,
    nowState
  });
  const today = useMemo(() => displayIssue ? toRecordShopDay(displayIssue) : null, [displayIssue]);
  const recentDays = useMemo(
    () => today ? [today, ...archiveDays.filter((day) => day.date !== today.date)] : archiveDays,
    [archiveDays, today]
  );
  const isNight = bjtNow.parts.hour >= 20 || bjtNow.parts.hour < 8;

  useEffect(() => {
    let active = true;
    setInteriorImagesReady(false);
    setAssetError(null);
    void preloadInterior(isNight)
      .then(() => { if (active) setInteriorImagesReady(true); })
      .catch(() => { if (active) setAssetError("Interior assets failed to load"); });
    return () => { active = false; };
  }, [isNight]);
  const approachInterior = useCallback(() => setApproaching(true), []);

  useEffect(() => {
    let active = true;
    setArchiveError(null);
    void loadArchiveIndex()
      .then(async (indexResult) => {
        const entries = getRecentArchiveEntries(indexResult.data);
        const settled = await Promise.allSettled(
          entries.map(async (entry) => {
            const issueResult = await loadArchiveDay(entry.date, entry.run_id);
            return toRecordShopDay(issueResult.data);
          })
        );
        if (!active) return;
        setArchiveDays(
          settled
            .filter((result): result is PromiseFulfilledResult<RecordShopDay> => result.status === "fulfilled")
            .map((result) => result.value)
        );
        const failure = settled.find((result) => result.status === "rejected");
        if (failure?.status === "rejected") {
          setArchiveError(normalizeDataLoadError(failure.reason, "archive_run").message);
        }
      })
      .catch((error: unknown) => {
        if (!active) return;
        setArchiveDays([]);
        setArchiveError(normalizeDataLoadError(error, "archive_index").message);
      });
    return () => { active = false; };
  }, []);

  const enterInterior = useCallback(() => {
    // A debug replay is one-shot. Clear its token before the exterior remounts
    // so returning from the gallery never starts another automatic entry.
    setEntryReplayToken(0);
    setSpace("interior");
    setApproaching(false);
  }, []);
  const returnExterior = useCallback(() => { setApproaching(false); setSpace("exterior"); }, []);
  const openEntryInfo = useCallback((panel: EntryInfoKey) => setEntryInfo(panel), []);
  const closeEntryInfo = useCallback(() => setEntryInfo(null), []);
  const runEntryDebug = useCallback(() => {
    setEntryInfo(null);
    setApproaching(false);
    setExteriorView("front");
    setSpace("exterior");
    setEntryReplayToken((token) => token + 1);
  }, []);
  const resetEntryDebug = useCallback(() => {
    setApproaching(false);
    setEntryInfo(null);
    setEntryReplayToken(0);
    setExteriorView("front");
    setSpace("exterior");
    setEntryResetKey((key) => key + 1);
  }, []);
  const hour = bjtNow.parts.hour.toString().padStart(2, "0");
  const minute = bjtNow.parts.minute.toString().padStart(2, "0");
  const availableCount = nowSlotId === null ? 0 : (nowSlotId + 1) * 3;
  const visibleRecordCount = today ? Math.min(availableCount, today.records.length) : availableCount;
  const dataError = todayError ?? assetError;
  const entryStatus = availableCount === 0
    ? recordShopCopy.exterior.todayClosed
    : `${localizedCopy.today.label.toUpperCase()} · ${availableCount} / 9 ${recordShopCopy.exterior.recordsAvailable}`;
  const debugPanel = debugPanelEnabled ? (
    <div className="record-shop-debug" data-open={debugOpen || undefined} aria-label={recordShopCopy.debug.aria}>
      <button className="record-shop-debug__toggle" type="button" aria-expanded={debugOpen} onPointerEnter={() => playCue("hover")} onClick={() => { playCue("press"); setDebugOpen((open) => !open); }}>
        {recordShopCopy.debug.toggle}
      </button>
      {debugOpen ? (
        <div className="record-shop-debug__panel">
          <header><strong>{`${bjtNow.bjtDateKey} ${hour}:${minute} BJT`}</strong><span>{debugTime ? recordShopCopy.debug.simulated : recordShopCopy.debug.realClock}</span></header>
          <div>
            {DEBUG_PRESETS.map((preset) => <button key={preset.copyKey} type="button" onPointerEnter={() => playCue("hover")} onClick={() => { playCue("press"); setDebugClock(preset.hour, preset.minute); setDebugOpen(false); }}>{recordShopCopy.debug[preset.copyKey]}</button>)}
            <button type="button" onPointerEnter={() => playCue("hover")} onClick={() => { playCue("press"); clearDebug(); setDebugOpen(false); }}>{recordShopCopy.debug.realTime}</button>
          </div>
          <section className="record-shop-debug__entry" aria-label={recordShopCopy.debug.entryAria}>
            <span>{recordShopCopy.debug.entryLabel}</span>
            <div>
              <button type="button" onPointerEnter={() => playCue("hover")} onClick={() => { playCue("press"); runEntryDebug(); }}>{recordShopCopy.debug.runEntry}</button>
              <button type="button" onPointerEnter={() => playCue("hover")} onClick={() => { playCue("press"); resetEntryDebug(); }}>{recordShopCopy.debug.resetEntry}</button>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  ) : null;
  const experienceControls = (
    <aside className="record-shop-controls" data-crossing={approaching || undefined} aria-label={recordShopCopy.controls.aria}>
      <div className="record-shop-controls__language" aria-label={localizedCopy.controls.language}>
        <button type="button" aria-pressed={language === "en"} onPointerEnter={() => playCue("hover")} onClick={() => { playCue("press"); setLanguage("en"); }}>EN</button>
        <button type="button" aria-pressed={language === "zh"} onPointerEnter={() => playCue("hover")} onClick={() => { playCue("press"); setLanguage("zh"); }}>中文</button>
      </div>
      <button
        className="record-shop-controls__sound"
        type="button"
        aria-pressed={soundEnabled}
        aria-label={soundEnabled ? recordShopCopy.controls.disableSound : recordShopCopy.controls.enableSound}
        onPointerEnter={() => playCue("hover")}
        onClick={toggleSound}
      >
        <span aria-hidden="true">{soundEnabled ? "◖))" : "◖×"}</span>
        {soundEnabled ? recordShopCopy.controls.soundOn : recordShopCopy.controls.soundOff}
      </button>
      {debugPanel}
    </aside>
  );

  if (space === "exterior") {
    return <>
      <EntryDiorama key={`entry-${entryResetKey}`} view={exteriorView} theme={isNight ? "night" : "day"} statusLabel={dataError ? recordShopCopy.loading.failed : entryStatus} copy={recordShopCopy.exterior} onCue={playCue} availableCount={availableCount} interiorReady={interiorImagesReady && !!today} onApproach={approachInterior} onViewChange={setExteriorView} onOpenInfo={openEntryInfo} onEnter={enterInterior} debugReplayToken={entryReplayToken} />
      {entryInfo ? <EntryInfoOverlay panel={entryInfo} exteriorCopy={recordShopCopy.exterior} copy={recordShopCopy.info} onCue={playCue} onClose={closeEntryInfo} /> : null}
      {experienceControls}
    </>;
  }

  if (!today) {
    return (
      <><section className="record-shop-loading" role="status">
        <strong>{recordShopCopy.loading.title}</strong>
        <p>{dataError ? recordShopCopy.loading.failed : recordShopCopy.loading.preparing}</p>
        {dataError ? <button type="button" onClick={returnExterior}>{recordShopCopy.interior.returnExterior}</button> : null}
      </section>{experienceControls}</>
    );
  }

  return (
    <>
      <InteriorGallery
        today={today}
        recentDays={recentDays}
        availableCount={visibleRecordCount}
        bjtTime={`${hour}:${minute}`}
        isNight={isNight}
        language={language}
        historyError={archiveError}
        copy={recordShopCopy}
        onCue={playCue}
        onReturnExterior={returnExterior}
      />
      {experienceControls}
    </>
  );
}
