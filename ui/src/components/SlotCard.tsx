import type { KeyboardEvent, MouseEvent } from "react";
import { useRef } from "react";
import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import { appendCacheBuster, resolvePublicPath } from "../lib/paths";
import { t } from "../strings/t";
import type { PickItem } from "../lib/types";

const slotStyles: Record<PickItem["slot"], string> = {
  Headliner: "border-acid-green/60 text-acid-green",
  Lineage: "border-clinical-white/40 text-clinical-white",
  DeepCut: "border-alert-red/60 text-alert-red"
};

interface SlotCardProps {
  pick: PickItem;
  onSelect?: (event: MouseEvent<HTMLElement> | KeyboardEvent<HTMLElement>) => void;
  layoutId?: string;
  dataTestId?: string;
  className?: string;
  cacheKey?: string;
}

function resolveCover(url: string, cacheKey?: string) {
  const trimmed = url.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return appendCacheBuster(trimmed, cacheKey);
  }
  const safe = trimmed.replace(/^\//, "");
  return appendCacheBuster(resolvePublicPath(safe), cacheKey);
}

export function SlotCard({ pick, onSelect, layoutId, dataTestId, className, cacheKey }: SlotCardProps) {
  const cardRef = useRef<HTMLElement | null>(null);
  const prefersReducedMotion = useReducedMotion();
  const coverUrl = resolveCover(pick.cover.optimized_cover_url, cacheKey);
  const isInteractive = Boolean(onSelect);
  const coverLayoutId = layoutId?.startsWith("card-") ? layoutId.replace("card-", "cover-") : undefined;
  const tiltX = useMotionValue(0);
  const tiltY = useMotionValue(0);
  const hover = useMotionValue(0);

  const tiltXSpring = useSpring(tiltX, { stiffness: 160, damping: 18 });
  const tiltYSpring = useSpring(tiltY, { stiffness: 160, damping: 18 });
  const hoverSpring = useSpring(hover, { stiffness: 120, damping: 20 });

  const lift = useTransform(hoverSpring, [0, 1], [0, -6]);
  const glowShadow = useTransform(
    hoverSpring,
    [0, 1],
    ["0 0 0 rgba(204, 255, 0, 0)", "0 0 26px rgba(204, 255, 0, 0.35)"]
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
    const rect = cardRef.current.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const centerX = rect.width / 2;
    const centerY = rect.height / 2;
    const rotateX = ((y - centerY) / rect.height) * -12;
    const rotateY = ((x - centerX) / rect.width) * 12;
    tiltX.set(rotateX);
    tiltY.set(rotateY);
  };

  const handleMouseLeave = () => {
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
      aria-label={isInteractive ? t("treatment.viewer.enter") : undefined}
      className={`hud-border flex h-full flex-col overflow-hidden rounded-card bg-panel-800/70 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-acid ${
        isInteractive
          ? "cursor-pointer transition-shadow duration-200 hover:border-acid-green/80 hover:drop-shadow-[0_0_18px_rgba(204,255,0,0.45)]"
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
      <div className="relative aspect-square w-full overflow-hidden bg-panel-900">
        {coverUrl ? (
          <motion.img
            layoutId={coverLayoutId}
            src={coverUrl}
            alt={`${pick.title} cover`}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-panel-900 via-panel-700 to-panel-900">
            <span className="font-mono text-xs uppercase tracking-[0.4em] text-clinical-white/40">
              {t("treatment.cover.missing")}
            </span>
          </div>
        )}
        <div className="absolute left-4 top-4">
          <span
            className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.3em] ${slotStyles[pick.slot]}`}
          >
            {t(`treatment.slot.${pick.slot}`)}
          </span>
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-3 px-5 py-4">
        <div>
          <h3 className="glitch-text text-lg font-semibold uppercase tracking-tightish">{pick.title}</h3>
          <p className="text-sm text-clinical-white/80">
            {pick.artist_credit || t("treatment.cover.unknownArtist")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.2em] text-clinical-white/60">
          {pick.first_release_year && <span>{pick.first_release_year}</span>}
          {pick.tags?.[0]?.name && <span>#{pick.tags[0].name}</span>}
        </div>
        <div className="mt-auto flex flex-wrap gap-2 text-xs text-clinical-white/70">
          {pick.links?.musicbrainz && (
            <a
              className="underline decoration-acid-green/60 underline-offset-4"
              href={pick.links.musicbrainz}
              onClick={(event) => event.stopPropagation()}
              target="_blank"
              rel="noreferrer"
            >
              {t("treatment.links.musicbrainz")}
            </a>
          )}
          {pick.links?.youtube_search && (
            <a
              className="underline decoration-clinical-white/40 underline-offset-4"
              href={pick.links.youtube_search}
              onClick={(event) => event.stopPropagation()}
              target="_blank"
              rel="noreferrer"
            >
              {t("treatment.links.youtube")}
            </a>
          )}
        </div>
      </div>
    </motion.article>
  );
}
