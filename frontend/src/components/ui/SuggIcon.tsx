import { TrendingDown, Shield, AlertTriangle, Layers, Trash2, Lightbulb } from "lucide-react";

const mapping: Record<string, { icon: any; color: string; bg: string }> = {
  model_downgrade: { icon: TrendingDown, color: "text-indigo-600", bg: "bg-indigo-50" },
  token_cap: { icon: Shield, color: "text-cyan-600", bg: "bg-cyan-50" },
  budget_alert: { icon: AlertTriangle, color: "text-amber-600", bg: "bg-amber-50" },
  provider_mix: { icon: Layers, color: "text-violet-600", bg: "bg-violet-50" },
  low_value_cut: { icon: Trash2, color: "text-red-600", bg: "bg-red-50" },
};

export function SuggIcon({ type }: { type: string }) {
  const { icon: Icon, color, bg } = mapping[type] || { icon: Lightbulb, color: "text-gray-600", bg: "bg-gray-50" };
  return (
    <div className={`p-2.5 rounded-xl flex-shrink-0 ${bg}`}>
      <Icon size={18} className={color} />
    </div>
  );
}
