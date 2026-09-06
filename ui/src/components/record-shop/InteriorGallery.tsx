import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent
} from "react";
import attendantBodyDay from "../../assets/record-shop/formal/attendant-body-day.png";
import attendantBodyNight from "../../assets/record-shop/formal/attendant-body-night.png";
import attendantHandShadowDay from "../../assets/record-shop/formal/attendant-hand-shadow-day.png";
import attendantHandShadowNight from "../../assets/record-shop/formal/attendant-hand-shadow-night.png";
import attendantHandsDay from "../../assets/record-shop/formal/attendant-hands-day.png";
import attendantHandsNight from "../../assets/record-shop/formal/attendant-hands-night.png";
import counterTopDay from "../../assets/record-shop/formal/counter-top-occluder-day.webp";
import counterTopNight from "../../assets/record-shop/formal/counter-top-occluder-night.webp";
import deviceScreenApertureMask from "../../assets/record-shop/formal/device-screen-aperture-mask-v3.png";
import deviceScreenBacklight from "../../assets/record-shop/formal/device-screen-backlight.png";
import deviceScreenGlassMask from "../../assets/record-shop/formal/device-screen-glass-mask-v4.png";
import deviceScreenInnerBezel from "../../assets/record-shop/formal/device-screen-inner-bezel-v1.png";
import environmentDay from "../../assets/record-shop/formal/environment-device-integrated-day-no-hud-v3.webp";
import environmentNight from "../../assets/record-shop/formal/environment-device-integrated-night-no-hud-v3.webp";
import { resolveCoverUrl } from "../../lib/covers";
import { resolvePublicPath } from "../../lib/paths";
import type { Language, RecordShopCopy } from "../../strings/copy";
import { InteriorHud } from "./InteriorHud";
import type { RecordShopCue } from "./audio";
import type { RecordShopDay, RecordShopRecord } from "./catalog";

type DeviceState = "offline" | "ready" | "choice" | "shuffle" | "complete" | "browse";

interface InteriorGalleryProps {
  today: RecordShopDay;
  recentDays: RecordShopDay[];
  availableCount: number;
  bjtTime: string;
  isNight: boolean;
  language: Language;
  historyError?: string | null;
  copy: RecordShopCopy;
  onCue: (cue: RecordShopCue) => void;
  onReturnExterior: () => void;
}

// Keep the decoded source images alive through returns to the exterior. The
// scene uses its approved physical layers, not a flattened character composite.
const interiorLoads = new Map<boolean, { images: HTMLImageElement[]; ready: Promise<void> }>();
export function preloadInterior(isNight: boolean) {
  const cached = interiorLoads.get(isNight);
  if (cached) return cached.ready;
  const sources = [
    isNight ? environmentNight : environmentDay,
    isNight ? attendantBodyNight : attendantBodyDay,
    isNight ? attendantHandsNight : attendantHandsDay,
    isNight ? attendantHandShadowNight : attendantHandShadowDay,
    isNight ? counterTopNight : counterTopDay,
    deviceScreenInnerBezel,
    deviceScreenApertureMask,
    deviceScreenGlassMask,
    deviceScreenBacklight
  ];
  const images = sources.map((src) => {
    const image = new Image();
    image.decoding = "async";
    image.src = src;
    return image;
  });
  const ready = Promise.all(images.map((image) => image.decode())).then(() => undefined).catch((error) => {
    interiorLoads.delete(isNight);
    throw error;
  });
  interiorLoads.set(isNight, { images, ready });
  return ready;
}

function AlbumArtwork({ record, compact = false }: { record: RecordShopRecord; compact?: boolean }) {
  const fallbackCover = resolvePublicPath("assets/placeholder.svg");
  const coverUrl = resolveCoverUrl(record.cover.optimized_cover_url, record.cover.cover_version) ?? fallbackCover;
  return (
    <div className="gallery-art" data-compact={compact || undefined} data-cover={record.cover.has_cover ? "available" : "fallback"} aria-hidden={compact || undefined}>
      <img className="gallery-art__fallback" src={fallbackCover} alt="" aria-hidden="true" />
      <img
        className="gallery-art__cover"
        src={coverUrl}
        alt={compact ? "" : `${record.title} — ${record.artist}`}
        onError={(event) => {
          if (event.currentTarget.dataset.fallbackApplied) return;
          event.currentTarget.dataset.fallbackApplied = "true";
          event.currentTarget.src = fallbackCover;
        }}
      />
      <b>{record.spineLabel}</b>
    </div>
  );
}

function TreatmentViewer({ record, copy, onCue, onClose }: { record: RecordShopRecord; copy: RecordShopCopy["interior"]; onCue: (cue: RecordShopCue) => void; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const metadata = [record.tags.length ? record.tags.join(" · ") : null, record.releaseYear?.toString() ?? null].filter(Boolean);
  const descriptiveText = record.overview ?? record.selectionNote;
  const descriptiveLabel = record.overview ? copy.overview : record.selectionNote ? copy.selectionNote : null;
  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);
  return (
    <section className="gallery-treatment" role="dialog" aria-modal="true" aria-labelledby="treatment-title">
      <button className="gallery-treatment__backdrop" type="button" aria-label={copy.treatmentCloseAria} onClick={onClose} />
      <article className="gallery-treatment__sheet">
        <div className="gallery-treatment__cover"><AlbumArtwork record={record} /></div>
        <div className="gallery-treatment__copy">
          <p>{record.windowLabel} / {copy.roleLabels[record.role]}</p>
          <h1 id="treatment-title">{record.title}</h1>
          <h2>{record.artist}</h2>
          {metadata.length ? <span>{metadata.join(" · ")}</span> : null}
          {descriptiveLabel ? <p className="gallery-treatment__metadata-label">{descriptiveLabel}</p> : null}
          <p>{descriptiveText ?? copy.metadataUnavailable}</p>
          {record.rating !== null ? <p className="gallery-treatment__rating">{copy.rating} {record.rating.toFixed(1)}{record.ratingVotes !== null ? ` · ${record.ratingVotes} ${copy.votes}` : ""}</p> : null}
          <div className="gallery-treatment__rule" />
          <p className="gallery-treatment__integration">{copy.publishedIssue}</p>
          <button ref={closeRef} type="button" onPointerEnter={() => onCue("hover")} onClick={() => { onCue("press"); onClose(); }}>{copy.backToSpines}</button>
        </div>
      </article>
    </section>
  );
}

export function InteriorGallery({ today, recentDays, availableCount, bjtTime, isNight, language, historyError = null, copy, onCue, onReturnExterior }: InteriorGalleryProps) {
  const [deviceState, setDeviceState] = useState<DeviceState>(() => availableCount === 0 ? "offline" : "ready");
  const [devicePanelOpen, setDevicePanelOpen] = useState(false);
  const [activeDate, setActiveDate] = useState(today.date);
  const [dateMenuOpen, setDateMenuOpen] = useState(false);
  const [activeRecord, setActiveRecord] = useState<RecordShopRecord | null>(null);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [shufflePhase, setShufflePhase] = useState(0);
  const [completedToday, setCompletedToday] = useState(false);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const recordRefs = useRef(new Map<string, HTMLButtonElement>());
  const primaryRef = useRef<HTMLButtonElement | null>(null);
  const dragRef = useRef({ active: false, moved: false, startX: 0, startScroll: 0 });

  const activeDay = recentDays.find((day) => day.date === activeDate) ?? today;
  const isHistory = activeDate !== today.date;
  const records = useMemo(
    () => isHistory ? activeDay.records : activeDay.records.slice(0, availableCount),
    [activeDay.records, availableCount, isHistory]
  );
  const screenStyle = {
    "--record-shop-aperture-mask": `url(${deviceScreenApertureMask})`,
    "--record-shop-glass-mask": `url(${deviceScreenGlassMask})`
  } as CSSProperties;
  const attendantBody = isNight ? attendantBodyNight : attendantBodyDay;
  const attendantHands = isNight ? attendantHandsNight : attendantHandsDay;
  const attendantHandShadow = isNight ? attendantHandShadowNight : attendantHandShadowDay;
  const counterTop = isNight ? counterTopNight : counterTopDay;
  const bodyLightStyle = { "--record-shop-figure-mask": `url(${attendantBody})` } as CSSProperties;
  const handsLightStyle = { "--record-shop-figure-mask": `url(${attendantHands})` } as CSSProperties;

  useEffect(() => { primaryRef.current?.focus(); }, []);

  useEffect(() => { setCompletedToday(false); }, [today.date]);

  useEffect(() => {
    if (isHistory) {
      setDeviceState("browse");
      setDevicePanelOpen(true);
      return;
    }
    if (availableCount === 0) {
      setDeviceState("offline");
      setDevicePanelOpen(false);
    }
    else if (deviceState === "offline") setDeviceState(completedToday ? "browse" : "ready");
  }, [availableCount, completedToday, deviceState, isHistory]);

  useEffect(() => {
    if (deviceState !== "shuffle") return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const phaseTimers = reduced ? [] : [420, 860].map((delay, index) => window.setTimeout(() => setShufflePhase(index + 1), delay));
    const completion = window.setTimeout(() => {
      setCompletedToday(true);
      setShufflePhase(0);
      setDeviceState("complete");
      setDevicePanelOpen(true);
    }, reduced ? 220 : 1420);
    return () => {
      phaseTimers.forEach((timer) => window.clearTimeout(timer));
      window.clearTimeout(completion);
    };
  }, [deviceState]);

  const startOpen = () => {
    if (deviceState !== "ready") return;
    onCue("device");
    setDeviceState(completedToday ? "choice" : "shuffle");
  };
  const skipShuffle = () => {
    onCue("device");
    setCompletedToday(true);
    setDeviceState("complete");
    setDevicePanelOpen(true);
  };
  const openBrowsePanel = () => {
    onCue("device");
    setDeviceState("browse");
    setDevicePanelOpen(true);
  };
  const closeDevicePanel = useCallback(() => {
    setDevicePanelOpen(false);
    window.setTimeout(() => primaryRef.current?.focus({ preventScroll: true }), 40);
  }, []);
  const chooseDate = (date: string) => {
    setActiveDate(date);
    setDateMenuOpen(false);
    setActiveRecord(null);
    setFocusedIndex(0);
    const nextState = date === today.date ? (completedToday ? "browse" : availableCount ? "ready" : "offline") : "browse";
    setDeviceState(nextState);
    setDevicePanelOpen(nextState === "browse");
  };
  const focusRecord = useCallback((index: number) => {
    const next = Math.max(0, Math.min(index, records.length - 1));
    const record = records[next];
    if (!record) return;
    setFocusedIndex(next);
    recordRefs.current.get(record.id)?.focus({ preventScroll: true });
    recordRefs.current.get(record.id)?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "nearest", inline: "center" });
  }, [records]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (activeRecord) return;
      if (event.key === "Escape" && dateMenuOpen) {
        event.preventDefault();
        setDateMenuOpen(false);
        return;
      }
      if (event.key === "Escape" && devicePanelOpen) {
        event.preventDefault();
        closeDevicePanel();
        return;
      }
      if (deviceState !== "browse" || !devicePanelOpen || dateMenuOpen) return;
      if (event.key === "ArrowLeft") { event.preventDefault(); focusRecord(focusedIndex - 1); }
      if (event.key === "ArrowRight") { event.preventDefault(); focusRecord(focusedIndex + 1); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeRecord, closeDevicePanel, dateMenuOpen, devicePanelOpen, deviceState, focusRecord, focusedIndex]);

  useEffect(() => {
    if (deviceState !== "browse" || !devicePanelOpen) return;
    const frame = window.requestAnimationFrame(() => {
      if (trackRef.current) trackRef.current.scrollLeft = 0;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [activeDate, devicePanelOpen, deviceState]);

  const beginDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!trackRef.current) return;
    dragRef.current = { active: true, moved: false, startX: event.clientX, startScroll: trackRef.current.scrollLeft };
  };
  const moveDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    const track = trackRef.current;
    if (!track || !dragRef.current.active) return;
    const delta = event.clientX - dragRef.current.startX;
    if (Math.abs(delta) > 6) dragRef.current.moved = true;
    track.scrollLeft = dragRef.current.startScroll - delta;
  };
  const endDrag = () => { dragRef.current.active = false; };

  const status: "OFFLINE" | "READY" | "ON" = deviceState === "offline" ? "OFFLINE" : deviceState === "ready" ? "READY" : "ON";
  const activeWindowCount = activeDay.windows.length;
  const focusedRecord = records[focusedIndex] ?? records[0] ?? null;
  const note = isHistory
    ? language === "zh"
      ? `${copy.interior.history} ${activeDate.slice(5)} / ${activeWindowCount} / ${activeWindowCount} ${copy.interior.windows} · ${activeDay.records.length} ${copy.interior.records}`
      : `${copy.interior.history} ${activeDate.slice(5)} / ${activeWindowCount} OF ${activeWindowCount} ${copy.interior.windows} / ${activeDay.records.length} ${copy.interior.records}`
    : deviceState === "offline"
      ? copy.interior.noWindow
      : language === "zh"
        ? `${availableCount / 3} / 3 ${copy.interior.windows} · ${availableCount} ${copy.interior.records}`
        : `${availableCount / 3} OF 3 ${copy.interior.windows} / ${availableCount} ${copy.interior.records}`;

  return (
    <section className="record-shop" data-device-state={deviceState} data-device-panel={devicePanelOpen ? "open" : "closed"} data-environment={isNight ? "night" : "day"} data-language={language} data-history-error={historyError ? "true" : undefined}>
      <div className="record-shop__stage">
        <div className="record-shop__world">
          <img decoding="async" className="record-shop__layer record-shop__environment" src={isNight ? environmentNight : environmentDay} alt={copy.interior.environmentAlt} />
          {deviceState !== "offline" ? <img decoding="async" className="record-shop__layer record-shop__screen-backlight" style={screenStyle} src={deviceScreenBacklight} alt="" /> : null}
          <div className="record-shop__screen-mask" style={screenStyle}>
            <section className="record-shop__screen" aria-label={copy.interior.dailyDevice} aria-live={deviceState === "shuffle" ? "polite" : undefined}>
              <span>{copy.interior.dailyDevice}</span>
              <strong>{deviceState === "offline" ? copy.interior.offline : deviceState === "ready" ? copy.interior.windowReady : deviceState === "choice" ? copy.interior.openToday : deviceState === "shuffle" ? copy.interior.arranging : deviceState === "complete" ? copy.interior.triggerComplete : copy.interior.inventoryOpen}</strong>
              <small>{deviceState === "offline" ? copy.interior.nextOnline : `${records.length || availableCount} ${deviceState === "complete" ? copy.interior.recordsWaiting : copy.interior.records}`}</small>
              {deviceState === "ready" ? <button ref={primaryRef} type="button" onPointerEnter={() => onCue("hover")} onClick={startOpen}>{copy.interior.open}</button> : null}
              {deviceState === "choice" ? <div className="record-shop__screen-actions"><button type="button" onPointerEnter={() => onCue("hover")} onClick={() => { onCue("device"); setDeviceState("shuffle"); }}>{copy.interior.play}</button><button type="button" onPointerEnter={() => onCue("hover")} onClick={skipShuffle}>{copy.interior.skip}</button></div> : null}
              {deviceState === "complete" ? <button ref={primaryRef} type="button" onPointerEnter={() => onCue("hover")} onClick={openBrowsePanel}>{copy.interior.continue}</button> : null}
              {deviceState === "browse" && !devicePanelOpen ? <button ref={primaryRef} type="button" onPointerEnter={() => onCue("hover")} onClick={() => { onCue("device"); setDevicePanelOpen(true); }}>{copy.interior.viewRecords}</button> : null}
            </section>
          </div>
          <img decoding="async" className="record-shop__layer record-shop__screen-bezel" src={deviceScreenInnerBezel} alt="" />
          <img decoding="async" className="record-shop__layer record-shop__attendant" src={attendantBody} alt="" />
          <div className="record-shop__figure-light record-shop__figure-light--body" style={bodyLightStyle} aria-hidden="true" />
          <img decoding="async" className="record-shop__layer record-shop__counter" src={counterTop} alt="" />
          <div className="record-shop__counter-contact" aria-hidden="true" />
          <img decoding="async" className="record-shop__layer record-shop__hand-shadow" src={attendantHandShadow} alt="" />
          <img decoding="async" className="record-shop__layer record-shop__hands" src={attendantHands} alt="" />
          <div className="record-shop__figure-light record-shop__figure-light--hands" style={handsLightStyle} aria-hidden="true" />
          <img decoding="async" className="record-shop__layer record-shop__counter-rim" src={counterTop} alt="" />
          <InteriorHud
            copy={copy.interior}
            currentDate={today.date}
            activeDate={activeDate}
            recentDays={recentDays}
            bjtTime={bjtTime}
            status={status}
            note={note}
            windows={isHistory ? activeDay.windows : today.windows}
            unlockedWindows={isHistory ? activeWindowCount : Math.min(today.windows.length, availableCount / 3)}
            dateMenuOpen={dateMenuOpen}
            onToggleDateMenu={() => setDateMenuOpen((open) => !open)}
            onChooseDate={chooseDate}
            onCue={onCue}
          />

          {deviceState === "shuffle" ? (
            <div className="record-shop__shuffle" data-phase={shufflePhase} aria-label={copy.interior.shuffleAria}>
              {today.records.concat(today.records.slice(0, 6)).map((record, index) => (
                <i key={`${record.id}-${index}`} style={{ "--shuffle-index": index } as CSSProperties}><AlbumArtwork record={record} compact /></i>
              ))}
            </div>
          ) : null}

          {deviceState === "complete" && devicePanelOpen ? (
            <section className="record-shop__device-panel record-shop__device-panel--complete" aria-label={copy.interior.triggerComplete}>
              <header><strong>{copy.interior.dailyDevice}</strong><span>{copy.interior.interiorLabel}</span><button className="record-shop__panel-close" type="button" onPointerEnter={() => onCue("hover")} onClick={() => { onCue("press"); closeDevicePanel(); }} aria-label={copy.interior.closePanelAria}>{copy.interior.closePanel}</button></header>
              <div><h2>{copy.interior.deviceReady}</h2><p>{copy.interior.secondAction}</p><button type="button" onPointerEnter={() => onCue("hover")} onClick={openBrowsePanel}>{copy.interior.continue}</button></div>
            </section>
          ) : null}

          {deviceState === "browse" && devicePanelOpen ? (
            <section className="record-shop__device-panel record-shop__device-panel--browse" data-record-count={records.length} aria-label={isHistory ? copy.interior.historyInventoryAria : copy.interior.todayInventoryAria}>
              <header><strong>{copy.interior.dailyDevice}</strong><span>{copy.interior.interiorLabel}</span><button className="record-shop__panel-close" type="button" onPointerEnter={() => onCue("hover")} onClick={() => { onCue("press"); closeDevicePanel(); }} aria-label={copy.interior.closePanelAria}>{copy.interior.closePanel}</button></header>
              <div ref={trackRef} className="record-shop__record-track" onPointerDown={beginDrag} onPointerMove={moveDrag} onPointerUp={endDrag} onPointerCancel={endDrag} onPointerLeave={endDrag}>
                {records.map((record, index) => (
                  <button
                    key={record.id}
                    ref={(node) => { if (node) recordRefs.current.set(record.id, node); else recordRefs.current.delete(record.id); }}
                    className="record-shop__spine"
                    data-current={focusedIndex === index ? "true" : undefined}
                    data-role={record.role}
                    data-slot-id={record.slotId}
                    type="button"
                    onFocus={() => { setFocusedIndex(index); onCue("hover"); }}
                    onPointerEnter={() => { setFocusedIndex(index); onCue("hover"); }}
                    onClick={() => { if (!dragRef.current.moved) { onCue("record"); setActiveRecord(record); } dragRef.current.moved = false; }}
                    aria-label={`${copy.interior.openRecord} ${record.title} — ${record.artist}`}
                  >
                    <b>{record.spineLabel}</b><span>{record.title}</span>
                  </button>
                ))}
              </div>
              <div className="record-shop__record-caption" aria-live="polite"><span>{focusedRecord?.spineLabel}</span><strong>{focusedRecord?.title}</strong><small>{focusedRecord ? `${copy.interior.roleLabels[focusedRecord.role]} · ${focusedRecord.artist}` : null}</small></div>
              <footer>
                <strong>{isHistory ? `${copy.interior.historyInventory} / ${activeDate.slice(5)}` : `${copy.interior.currentInventory} / ${today.date.slice(5)}`}</strong>
                <span>{copy.interior.browseHint}</span>
                <div><button type="button" disabled={focusedIndex <= 0} onPointerEnter={() => onCue("hover")} onClick={() => { onCue("record"); focusRecord(focusedIndex - 1); }} aria-label={copy.interior.previousRecord}>←</button><button type="button" disabled={focusedIndex >= records.length - 1} onPointerEnter={() => onCue("hover")} onClick={() => { onCue("record"); focusRecord(focusedIndex + 1); }} aria-label={copy.interior.nextRecord}>→</button></div>
              </footer>
            </section>
          ) : null}
        </div>
      </div>

      <div className="record-shop__utility">
        <button type="button" onPointerEnter={() => onCue("hover")} onClick={() => { onCue("press"); onReturnExterior(); }}>{copy.interior.returnExterior}</button>
        {isHistory ? <button type="button" onPointerEnter={() => onCue("hover")} onClick={() => { onCue("history"); chooseDate(today.date); }}>{copy.interior.returnToday}</button> : null}
      </div>
      {activeRecord ? <TreatmentViewer record={records.find(record => record.id === activeRecord.id) ?? activeRecord} copy={copy.interior} onCue={onCue} onClose={() => { const record = activeRecord; setActiveRecord(null); window.setTimeout(() => recordRefs.current.get(record.id)?.focus({ preventScroll: true }), 60); }} /> : null}
    </section>
  );
}
