import { useT } from "../lib/ui-settings";

interface BsodProps {
  title?: string;
  message?: string;
}

export function BSOD({ title, message }: BsodProps) {
  const tx = useT();
  return (
    <div className="flex min-h-[60vh] flex-col items-start justify-center rounded-card border border-alert-red/40 bg-[#05080f] p-8 text-left">
      <p className="ui-kicker text-alert-red">{tx("system.status.error")}</p>
      <h2 className="mt-3 text-2xl font-semibold">{title ?? tx("system.errors.bsodTitle")}</h2>
      <p className="mt-4 max-w-xl font-mono text-sm text-clinical-white/70">
        {message ?? tx("system.errors.bsodBody")}
      </p>
      <div className="mt-6 font-mono text-xs text-clinical-white/50">{tx("system.errors.errorCode")}</div>
    </div>
  );
}
