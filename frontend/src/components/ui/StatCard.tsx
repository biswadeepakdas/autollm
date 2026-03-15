import { LucideIcon } from "lucide-react";
import { Card } from "./Card";

interface StatCardProps {
  icon: LucideIcon;
  label: string;
  value: string;
  sub?: string;
  trend?: number;
  accent?: string;
  bg?: string;
}

export function StatCard({ icon: Icon, label, value, sub, trend, accent = "#6366f1", bg = "#eef2ff" }: StatCardProps) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div className="p-2.5 rounded-xl" style={{ background: bg }}>
          <Icon size={20} style={{ color: accent }} />
        </div>
        {trend != null && (
          <span className={`text-xs font-semibold ${trend > 0 ? "text-red-500" : "text-emerald-500"}`}>
            {trend > 0 ? "+" : ""}{trend}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-gray-900 mt-3 tracking-tight">{value}</p>
      <p className="text-sm text-gray-500 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </Card>
  );
}
