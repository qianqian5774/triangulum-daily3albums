import { useReducedMotion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { FLAGS } from "../config/flags";

interface BsodProps {
  title?: string;
  message?: string;
}

export function BSOD({ title, message }: BsodProps) {
  const { t } = useTranslation();
  const prefersReducedMotion = useReducedMotion();
  return (
    <div
      className={`flex min-h-[60vh] flex-col items-start justify-center rounded-card border border-alert-red/40 bg-[#05080f] p-8 text-left ${
        FLAGS.organicGlitch && !prefersReducedMotion ? "glitch-once" : ""
      }`}
    >
      <p className="text-xs uppercase tracking-[0.4em] text-alert-red">{t("system.error.title")}</p>
      <h2 className="mt-3 text-2xl font-semibold">{title ?? t("system.error.title")}</h2>
      <p className="mt-4 max-w-xl font-mono text-sm text-clinical-white/70">
        {message ?? t("system.error.message")}
      </p>
      <div className="mt-6 font-mono text-xs text-clinical-white/50">{t("system.error.code")}</div>
    </div>
  );
}
