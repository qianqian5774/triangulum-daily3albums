import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { cn } from "../lib/cn";

interface MarqueeProps {
  items: string[];
  className?: string;
}

export function Marquee({ items, className }: MarqueeProps) {
  const { t } = useTranslation();
  const sequence = useMemo(() => {
    if (items.length === 0) {
      const fallback = t("marquee.fallback", { returnObjects: true });
      return Array.isArray(fallback) ? fallback : [String(fallback)];
    }
    return items;
  }, [items, t]);

  const repeated = [...sequence, ...sequence];

  return (
    <div className={cn("overflow-hidden whitespace-nowrap", className)}>
      <div className="marquee">
        {repeated.map((item, index) => (
          <span key={`${item}-${index}`} className="text-xs uppercase tracking-[0.3em] text-clinical-white/70">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
