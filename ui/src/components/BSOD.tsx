import { t } from "../strings/t";

interface BsodProps {
  title?: string;
  message?: string;
}

export function BSOD({ title, message }: BsodProps) {
  return (
    <div className="flex min-h-[60vh] flex-col items-start justify-center rounded-card border border-alert-red/40 bg-[#05080f] p-8 text-left">
      <p className="text-xs uppercase tracking-[0.4em] text-alert-red">{t("system.status.error")}</p>
      <h2 className="mt-3 text-2xl font-semibold">{title ?? t("system.errors.bsodTitle")}</h2>
      <p className="mt-4 max-w-xl font-mono text-sm text-clinical-white/70">
        {message ?? t("system.errors.bsodBody")}
      </p>
      <div className="mt-6 font-mono text-xs text-clinical-white/50">{t("system.errors.errorCode")}</div>
    </div>
  );
}
