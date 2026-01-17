import { useContext, useEffect, useMemo, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { HudContext } from "../App";
import { BSOD } from "../components/BSOD";
import { SlotCard } from "../components/SlotCard";
import { loadToday } from "../lib/data";
import type { TodayIssue } from "../lib/types";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.18
    }
  }
};

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring",
      damping: 18,
      stiffness: 140
    }
  }
};

export function TodayRoute() {
  const hudContext = useContext(HudContext);
  const [issue, setIssue] = useState<TodayIssue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    let active = true;
    loadToday()
      .then((data) => {
        if (!active) return;
        setIssue(data);
        const batchId = data.run_id ? data.run_id.toUpperCase() : data.date;
        const marqueeItems = data.picks.map((pick) => `${pick.title} — ${pick.artist_credit}`);
        hudContext?.updateHud({
          batchId,
          status: "OK",
          marqueeItems
        });
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
        hudContext?.updateHud({ status: "ERROR" });
      });
    return () => {
      active = false;
    };
  }, [hudContext]);

  const headerText = useMemo(() => {
    if (!issue) {
      return "Calibrating today\u2019s triage";
    }
    return `${issue.date} · Theme ${issue.theme_of_day}`;
  }, [issue]);

  if (error) {
    return <BSOD message={`TODAY JSON load failed: ${error}`} />;
  }

  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <p className="text-xs uppercase tracking-[0.4em] text-clinical-white/60">Today</p>
        <h1 className="text-3xl font-semibold uppercase tracking-tightish">{headerText}</h1>
        <p className="font-mono text-sm text-clinical-white/60">
          Diagnostic pipeline engaged. Three capsules are compiled in sequence for immediate intake.
        </p>
      </div>
      {issue ? (
        <motion.div
          className="grid gap-6 md:grid-cols-3"
          variants={prefersReducedMotion ? undefined : containerVariants}
          initial={prefersReducedMotion ? undefined : "hidden"}
          animate={prefersReducedMotion ? undefined : "show"}
        >
          {issue.picks.map((pick) => (
            <motion.div key={pick.slot} variants={prefersReducedMotion ? undefined : cardVariants}>
              <SlotCard pick={pick} />
            </motion.div>
          ))}
        </motion.div>
      ) : (
        <div className="hud-border rounded-card bg-panel-900/60 p-6 font-mono text-sm text-clinical-white/60">
          Loading intake stream...
        </div>
      )}
    </section>
  );
}
