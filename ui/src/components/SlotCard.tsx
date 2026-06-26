import type { KeyboardEvent, MouseEvent } from "react";
import { useEffect, useId, useRef, useState } from "react";
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { resolveCoverUrl } from "../lib/covers";
import { useT } from "../lib/ui-settings";
import type { PickItem } from "../lib/types";

const slotStyles: Record<PickItem["slot"], string> = {
  Headliner: "slotcard-badge-accent",
  Lineage: "slotcard-badge-accent",
  DeepCut: "slotcard-badge-accent"
};

interface SlotCardProps {
  pick: PickItem;
  onSelect?: (event: MouseEvent<HTMLElement> | KeyboardEvent<HTMLElement>) => void;
  layoutId?: string;
  dataTestId?: string;
  className?: string;
  cacheKey?: string;
  imageLoading?: "eager" | "lazy";
  fetchPriority?: "high" | "auto" | "low";
  disableLinks?: boolean;
  locked?: boolean;
}

export function SlotCard({
  pick,
  onSelect,
  layoutId,
  dataTestId,
  className,
  cacheKey,
  imageLoading = "lazy",
  fetchPriority = "auto",
  disableLinks = false,
  locked = false
}: SlotCardProps) {
  const tx = useT();
  const cardRef = useRef<HTMLElement | null>(null);
  const tiltFrameRef = useRef<number | null>(null);
  const lastPointerRef = useRef<{ clientX: number; clientY: number } | null>(null);
  const prefersReducedMotion = useReducedMotion();
  const [retryToken, setRetryToken] = useState<string | null>(null);
  const [coverFailed, setCoverFailed] = useState(false);
  const [slotInfoOpen, setSlotInfoOpen] = useState(false);
  const slotInfoId = useId();
  const coverUrl = resolveCoverUrl(pick.cover.optimized_cover_url, cacheKey, retryToken);
  const isInteractive = Boolean(onSelect) && !locked;
  const coverLayoutId = layoutId?.startsWith("card-") ? layoutId.replace("card-", "cover-") : undefined;
  const tiltX = useMotionValue(0);
  const tiltY = useMotionValue(0);
  const hover = useMotionValue(0);

  useEffect(() => {
    setRetryToken(null);
    setCoverFailed(false);
  }, [pick.cover.optimized_cover_url, cacheKey]);

  useEffect(
    () => () => {
      if (tiltFrameRef.current) {
        window.cancelAnimationFrame(tiltFrameRef.current);
      }
    },
    []
  );

  const tiltXSpring = useSpring(tiltX, { stiffness: 160, damping: 18 });
  const tiltYSpring = useSpring(tiltY, { stiffness: 160, damping: 18 });
  const hoverSpring = useSpring(hover, { stiffness: 120, damping: 20 });

  const lift = useTransform(hoverSpring, [0, 1], [0, -6]);
  const glowShadow = useTransform(
    hoverSpring,
    [0, 1],
    ["0 0 0 rgb(var(--theme-accent-rgb) / 0)", "0 0 14px rgb(var(--theme-accent-rgb) / 0.26)"]
  );

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!onSelect) {
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(event);
    }
  };

  const handleMouseMove = (event: MouseEvent<HTMLElement>) => {
    if (prefersReducedMotion || !cardRef.current) {
      return;
    }
    lastPointerRef.current = { clientX: event.clientX, clientY: event.clientY };
    if (tiltFrameRef.current) {
      return;
    }
    tiltFrameRef.current = window.requestAnimationFrame(() => {
      tiltFrameRef.current = null;
      const pointer = lastPointerRef.current;
      if (!pointer || !cardRef.current) {
        return;
      }
      const rect = cardRef.current.getBoundingClientRect();
      const x = pointer.clientX - rect.left;
      const y = pointer.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / rect.height) * -7;
      const rotateY = ((x - centerX) / rect.width) * 7;
      tiltX.set(rotateX);
      tiltY.set(rotateY);
    });
  };

  const handleMouseLeave = () => {
    if (tiltFrameRef.current) {
      window.cancelAnimationFrame(tiltFrameRef.current);
      tiltFrameRef.current = null;
    }
    lastPointerRef.current = null;
    tiltX.set(0);
    tiltY.set(0);
    hover.set(0);
  };

  return (
    <motion.article
      ref={cardRef}
      layoutId={layoutId}
      data-testid={dataTestId}
      onClick={onSelect}
      onKeyDown={handleKeyDown}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      onHoverStart={() => hover.set(1)}
      onHoverEnd={handleMouseLeave}
      whileTap={{ scale: 0.98 }}
      role={isInteractive ? "button" : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      aria-label={isInteractive ? tx("treatment.viewer.enter") : undefined}
      className={`slotcard hud-border flex h-full flex-col overflow-hidden rounded-card bg-panel-800/70 transition ${
        isInteractive
          ? "slotcard-interactive cursor-pointer transition-shadow duration-200"
          : ""
      } ${className ?? ""}`}
      style={{
        rotateX: prefersReducedMotion ? 0 : tiltXSpring,
        rotateY: prefersReducedMotion ? 0 : tiltYSpring,
        y: prefersReducedMotion ? 0 : lift,
        boxShadow: prefersReducedMotion ? undefined : glowShadow,
        transformPerspective: 1000,
        transformStyle: "preserve-3d"
      }}
    >
      <div className="slotcard-cover relative aspect-square w-full overflow-hidden bg-panel-900">
        {!locked && coverUrl && !coverFailed ? (
          <motion.img
            layoutId={coverLayoutId}
            src={coverUrl}
            alt={`${pick.title} cover`}
            className="h-full w-full object-cover"
            loading={imageLoading}
            fetchPriority={fetchPriority}
            onError={() => {
              if (retryToken === null) {
                setRetryToken(Date.now().toString());
                return;
              }
              setCoverFailed(true);
            }}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-panel-900 via-panel-700 to-panel-900">
            <span className="font-mono text-2xl uppercase tracking-[0.4em] text-clinical-white/40">
              {locked ? "?" : tx("treatment.cover.missing")}
            </span>
          </div>
        )}
        <div className="slotcard-badge absolute left-4 top-4">
          <span
            className={`inline-flex min-h-[1.75rem] items-center rounded-hud border px-3 py-1 text-[0.68rem] font-black uppercase tracking-[0.22em] ${slotStyles[pick.slot]}`}
          >
            {tx(`treatment.slot.${pick.slot}`)}
          </span>
        </div>
      </div>
      <div className="slotcard-body flex flex-1 flex-col gap-3 px-5 py-4">
        <div>
          <div className="flex items-start justify-between gap-3">
            <h3 className="glitch-text text-lg font-semibold uppercase tracking-tightish text-clinical-white">
              {locked ? tx("today.timeline.locked") : pick.title}
            </h3>
            {!locked ? (
              <button
                type="button"
                className="slotcard-info-button"
                aria-label={`${tx("treatment.slotInfoButton")}: ${tx(`treatment.slot.${pick.slot}`)}`}
                aria-expanded={slotInfoOpen}
                aria-controls={slotInfoId}
                onClick={(event) => {
                  event.stopPropagation();
                  setSlotInfoOpen((open) => !open);
                }}
                onKeyDown={(event) => event.stopPropagation()}
              >
                i
              </button>
            ) : null}
          </div>
          <p className="text-sm text-clinical-white/60">
            {locked ? "???" : pick.artist_credit || tx("treatment.cover.unknownArtist")}
          </p>
        </div>
        {!locked && slotInfoOpen ? (
          <div
            id={slotInfoId}
            className="slotcard-info-panel"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => event.stopPropagation()}
          >
            <span>{tx(`treatment.slot.${pick.slot}`)}</span>
            <p>{tx(`treatment.slotInfo.${pick.slot}`)}</p>
          </div>
        ) : null}
        <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.2em] text-clinical-white/50">
          {!locked && pick.first_release_year && <span>{pick.first_release_year}</span>}
          {!locked && pick.tags?.[0]?.name && <span>#{pick.tags[0].name}</span>}
        </div>
        {!disableLinks && !locked ? (
          <div className="mt-auto flex flex-wrap gap-2 text-sm text-clinical-white/70">
            {pick.links?.musicbrainz && (
              <a
                className="inline-flex min-h-[36px] items-center px-2 py-1 text-[11px] uppercase tracking-[0.3em] text-signal-accent underline decoration-signal-accent/60 underline-offset-4 transition hover:text-signal-accent/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-signal-accent/70"
                href={pick.links.musicbrainz}
                onClick={(event) => event.stopPropagation()}
                target="_blank"
                rel="noopener noreferrer"
              >
                {tx("treatment.links.musicbrainz")}
              </a>
            )}
            {pick.links?.youtube_search && (
              <a
                className="inline-flex min-h-[36px] items-center px-2 py-1 text-[11px] uppercase tracking-[0.3em] text-clinical-white underline decoration-clinical-white/50 underline-offset-4 transition hover:text-clinical-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-white/60"
                href={pick.links.youtube_search}
                onClick={(event) => event.stopPropagation()}
                target="_blank"
                rel="noopener noreferrer"
              >
                {tx("treatment.links.youtube")}
              </a>
            )}
          </div>
        ) : null}
      </div>
    </motion.article>
  );
}
