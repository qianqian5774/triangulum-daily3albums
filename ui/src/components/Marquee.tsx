import { useMemo } from "react";
import { cn } from "../lib/cn";
import { useLocalizedCopy } from "../lib/ui-settings";

interface MarqueeProps {
  items: string[];
  className?: string;
}

export function Marquee({ items, className }: MarqueeProps) {
  const localizedCopy = useLocalizedCopy();
  const sequence = useMemo(() => {
    if (items.length === 0) {
      return localizedCopy.system.marqueeFallback;
    }
    return items;
  }, [items, localizedCopy.system.marqueeFallback]);

  const repeated = [...sequence, ...sequence];

  return (
    <div className={cn("overflow-hidden whitespace-nowrap", className)}>
      <div className="marquee">
        {repeated.map((item, index) => (
          <span
            key={`${item}-${index}`}
            className="text-[0.82rem] font-semibold uppercase tracking-[0.28em] text-clinical-white/78"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
