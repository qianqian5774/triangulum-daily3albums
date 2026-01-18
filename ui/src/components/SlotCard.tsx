import { forwardRef } from "react";
import { motion, type MotionProps } from "framer-motion";
import { useTranslation } from "react-i18next";
import { resolvePublicPath } from "../lib/paths";
import type { PickItem } from "../lib/types";

const slotStyles: Record<PickItem["slot"], string> = {
  Headliner: "border-acid-green/60 text-acid-green",
  Lineage: "border-clinical-white/40 text-clinical-white",
  DeepCut: "border-alert-red/60 text-alert-red"
};

const slotLabels: Record<PickItem["slot"], string> = {
  Headliner: "treatment.dose.headliner",
  Lineage: "treatment.dose.lineage",
  DeepCut: "treatment.dose.deepcut"
};

interface SlotCardProps {
  pick: PickItem;
  onSelect?: () => void;
  layoutId?: string;
  imageLayoutId?: string;
  motionProps?: MotionProps;
}

function resolveCover(url: string) {
  const trimmed = url.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  const safe = trimmed.replace(/^\//, "");
  return resolvePublicPath(safe);
}

export const SlotCard = forwardRef<HTMLButtonElement, SlotCardProps>(function SlotCard(
  { pick, onSelect, layoutId, imageLayoutId, motionProps }: SlotCardProps,
  ref
) {
  const { t } = useTranslation();
  const coverUrl = resolveCover(pick.cover.optimized_cover_url);
  const sharedProps = {
    layoutId,
    className:
      "hud-border flex h-full w-full flex-col overflow-hidden rounded-card bg-panel-800/70 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-acid",
    ...motionProps
  };

  const SlotComponent = onSelect ? motion.button : motion.article;

  return (
    <SlotComponent
      ref={onSelect ? ref : undefined}
      type={onSelect ? "button" : undefined}
      onClick={onSelect}
      {...sharedProps}
    >
      <div className="relative aspect-square w-full overflow-hidden bg-panel-900">
        {coverUrl ? (
          <motion.img
            src={coverUrl}
            alt={`${pick.title} cover`}
            className="h-full w-full object-cover"
            loading="lazy"
            layoutId={imageLayoutId}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-panel-900 via-panel-700 to-panel-900">
            <span className="font-mono text-xs uppercase tracking-[0.4em] text-clinical-white/40">
              {t("treatment.dose.no_cover")}
            </span>
          </div>
        )}
        <div className="absolute left-4 top-4">
          <span
            className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.3em] ${
              slotStyles[pick.slot]
            }`}
          >
            {t(slotLabels[pick.slot])}
          </span>
        </div>
      </div>
      <div className="flex flex-1 min-h-0 flex-col gap-3 overflow-y-auto px-5 py-4">
        <div>
          <h3 className="glitch-text text-lg font-semibold uppercase tracking-tightish">{pick.title}</h3>
          <p className="text-sm text-clinical-white/80">
            {pick.artist_credit || t("treatment.dose.artist_fallback")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.2em] text-clinical-white/60">
          {pick.first_release_year && <span>{pick.first_release_year}</span>}
          {pick.tags?.[0]?.name && <span>#{pick.tags[0].name}</span>}
        </div>
        <div className="mt-auto flex items-center gap-2 text-[10px] uppercase tracking-[0.3em] text-clinical-white/40">
          {onSelect ? t("treatment.viewer.enter") : null}
        </div>
      </div>
    </SlotComponent>
  );
});
