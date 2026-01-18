import { useEffect, useMemo, useRef, type KeyboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import type { PickItem } from "../lib/types";
import { resolvePublicPath } from "../lib/paths";
import { FLAGS } from "../config/flags";

interface TreatmentViewerProps {
  picks: PickItem[];
  activeIndex: number;
  activeId: string;
  direction: -1 | 1;
  reducedMotion: boolean;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

function resolveCover(url: string) {
  const trimmed = url.trim();
  if (!trimmed) return null;
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) return trimmed;
  return resolvePublicPath(trimmed.replace(/^\//, ""));
}

function getFocusable(container: HTMLElement | null) {
  if (!container) return [] as HTMLElement[];
  return Array.from(
    container.querySelectorAll<HTMLElement>(
      "button,[href],input,select,textarea,[tabindex]:not([tabindex='-1'])"
    )
  ).filter((el) => !el.hasAttribute("disabled"));
}

export function TreatmentViewer({
  picks,
  activeIndex,
  activeId,
  direction,
  reducedMotion,
  onClose,
  onNavigate
}: TreatmentViewerProps) {
  const { t } = useTranslation();
  const focusRef = useRef<HTMLDivElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);

  const pick = picks[activeIndex];
  const cover = pick ? resolveCover(pick.cover.optimized_cover_url) : null;
  const layoutId = reducedMotion ? undefined : `card-${activeId}`;
  const imageLayoutId = reducedMotion ? undefined : `cover-${activeId}`;

  const hasPrev = activeIndex > 0;
  const hasNext = activeIndex < picks.length - 1;

  useEffect(() => {
    closeRef.current?.focus();
  }, [activeId]);

  const keyHandler = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key === "ArrowLeft" && hasPrev) {
      event.preventDefault();
      onNavigate(activeIndex - 1);
      return;
    }
    if (event.key === "ArrowRight" && hasNext) {
      event.preventDefault();
      onNavigate(activeIndex + 1);
      return;
    }
    if (event.key === "Tab") {
      const items = getFocusable(focusRef.current);
      if (items.length === 0) return;
      const currentIndex = items.indexOf(document.activeElement as HTMLElement);
      const nextIndex = event.shiftKey
        ? (currentIndex - 1 + items.length) % items.length
        : (currentIndex + 1) % items.length;
      event.preventDefault();
      items[nextIndex]?.focus();
    }
  };

  const evidence = useMemo(() => {
    if (!pick?.evidence?.mapping_confidence) return null;
    return `${Math.round(pick.evidence.mapping_confidence * 100)}%`;
  }, [pick]);

  if (!pick) return null;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-40 flex items-center justify-center bg-void-black/80 backdrop-blur-xl"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={(event) => {
          if (event.target === event.currentTarget) {
            onClose();
          }
        }}
        onKeyDown={keyHandler}
        ref={focusRef}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
      >
        <div className="absolute inset-y-0 left-0 z-0 w-1/4" aria-hidden="true">
          {hasPrev && (
            <button
              type="button"
              className="h-full w-full"
              onClick={() => onNavigate(activeIndex - 1)}
              aria-label={t("treatment.viewer.prev")}
              tabIndex={-1}
            />
          )}
        </div>
        <div className="absolute inset-y-0 right-0 z-0 w-1/4" aria-hidden="true">
          {hasNext && (
            <button
              type="button"
              className="h-full w-full"
              onClick={() => onNavigate(activeIndex + 1)}
              aria-label={t("treatment.viewer.next")}
              tabIndex={-1}
            />
          )}
        </div>
        <motion.div
          className="relative z-10 mx-4 flex w-full max-w-5xl flex-col gap-6 rounded-card border border-panel-700/80 bg-panel-900/95 p-6 shadow-hard-xl md:flex-row"
          layoutId={layoutId}
        >
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={activeId}
              className={`flex w-full flex-col gap-6 md:flex-row ${
                FLAGS.organicGlitch && !reducedMotion ? "glitch-once" : ""
              }`}
              custom={direction}
              initial={reducedMotion ? { opacity: 0 } : { opacity: 0, x: direction * 140 }}
              animate={reducedMotion ? { opacity: 1 } : { opacity: 1, x: 0 }}
              exit={reducedMotion ? { opacity: 0 } : { opacity: 0, x: direction * -140 }}
              transition={{ type: "tween", duration: 0.2 }}
            >
              <div className="relative w-full max-w-md overflow-hidden rounded-card bg-panel-800 md:w-1/2">
                {cover ? (
                  <motion.img
                    src={cover}
                    alt={`${pick.title} cover`}
                    className="h-full w-full object-cover"
                    layoutId={imageLayoutId}
                  />
                ) : (
                  <div className="flex h-full min-h-[240px] w-full items-center justify-center bg-gradient-to-br from-panel-900 via-panel-700 to-panel-900">
                    <span className="font-mono text-xs uppercase tracking-[0.4em] text-clinical-white/40">
                      {t("treatment.dose.no_cover")}
                    </span>
                  </div>
                )}
              </div>
              <div className="flex flex-1 flex-col gap-4">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.4em] text-acid-green/80">
                      {t(`treatment.dose.${pick.slot === "DeepCut" ? "deepcut" : pick.slot.toLowerCase()}`)}
                    </p>
                    <h2 className="mt-2 text-3xl font-semibold uppercase tracking-tightish">{pick.title}</h2>
                    <p className="text-sm text-clinical-white/70">
                      {pick.artist_credit || t("treatment.dose.artist_fallback")}
                    </p>
                    <p className="mt-2 font-mono text-xs uppercase tracking-[0.3em] text-clinical-white/40">
                      {activeIndex + 1}/{picks.length}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => hasPrev && onNavigate(activeIndex - 1)}
                      disabled={!hasPrev}
                      className="rounded-hud border border-panel-700/70 px-3 py-2 text-xs uppercase tracking-[0.3em] text-clinical-white/60 transition hover:border-clinical-white/50 disabled:opacity-40"
                      aria-label={t("treatment.viewer.prev")}
                    >
                      {t("treatment.viewer.prev")}
                    </button>
                    <button
                      type="button"
                      onClick={() => hasNext && onNavigate(activeIndex + 1)}
                      disabled={!hasNext}
                      className="rounded-hud border border-panel-700/70 px-3 py-2 text-xs uppercase tracking-[0.3em] text-clinical-white/60 transition hover:border-clinical-white/50 disabled:opacity-40"
                      aria-label={t("treatment.viewer.next")}
                    >
                      {t("treatment.viewer.next")}
                    </button>
                    <button
                      type="button"
                      ref={closeRef}
                      onClick={onClose}
                      className="rounded-hud border border-panel-700/70 px-3 py-2 text-xs uppercase tracking-[0.3em] text-clinical-white/60 transition hover:border-clinical-white/50"
                      aria-label={t("treatment.viewer.exit")}
                    >
                      {t("treatment.viewer.exit")}
                    </button>
                  </div>
                </div>
                <div className="grid gap-3 text-xs uppercase tracking-[0.3em] text-clinical-white/60 sm:grid-cols-2">
                  {pick.first_release_year && (
                    <div className="flex items-center gap-2">
                      <span>{pick.first_release_year}</span>
                    </div>
                  )}
                  {evidence && (
                    <div className="flex items-center gap-2">
                      <span className="text-acid-green/70">{t("treatment.dose.evidence")}</span>
                      <span>{evidence}</span>
                    </div>
                  )}
                </div>
                {pick.reason && (
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-clinical-white/50">
                      {t("treatment.dose.rationale")}
                    </p>
                    <p className="mt-2 text-sm text-clinical-white/80">{pick.reason}</p>
                  </div>
                )}
                {pick.tags?.length ? (
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-clinical-white/50">
                      {t("treatment.dose.tags")}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs uppercase tracking-[0.2em] text-clinical-white/70">
                      {pick.tags.map((tag) => (
                        <span key={tag.name}>#{tag.name}</span>
                      ))}
                    </div>
                  </div>
                ) : null}
                <div className="mt-auto flex flex-wrap gap-3 text-xs uppercase tracking-[0.3em]">
                  <span className="text-clinical-white/40">{t("treatment.dose.links")}</span>
                  {pick.links?.musicbrainz && (
                    <a
                      className="text-acid-green/80 underline decoration-acid-green/60 underline-offset-4"
                      href={pick.links.musicbrainz}
                    >
                      MusicBrainz
                    </a>
                  )}
                  {pick.links?.youtube_search && (
                    <a
                      className="text-clinical-white/70 underline decoration-clinical-white/40 underline-offset-4"
                      href={pick.links.youtube_search}
                    >
                      YouTube
                    </a>
                  )}
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
