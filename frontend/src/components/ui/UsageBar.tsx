import { fmtK } from "@/lib/format";

interface UsageBarProps {
  label: string;
  current: number;
  max: number;
}

export function UsageBar({ label, current, max }: UsageBarProps) {
  const pct = Math.min((current / max) * 100, 100);
  const near = pct > 80;
  const over = pct >= 100;

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className={`font-medium ${over ? "text-red-600" : near ? "text-amber-600" : "text-gray-900"}`}>
          {fmtK(current)} / {fmtK(max)}
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${over ? "bg-red-500" : near ? "bg-amber-400" : "bg-indigo-500"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
