import { useMemo } from "react";
import { cn } from "../lib/cn";
import { copy } from "../strings/copy";

interface MarqueeProps {
  items: string[];
  className?: string;
}

export function Marquee({ items, className }: MarqueeProps) {
  const sequence = useMemo(() => {
    if (items.length === 0) {
      return copy.system.marqueeFallback;
    }
    return items;
  }, [items]);

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
