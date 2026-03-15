/** Format cents to dollar string, e.g. 4230 → "$42.30" */
export function fmt(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}

/** Format large numbers, e.g. 12480 → "12.5K" */
export function fmtK(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

/** Chart color palette */
export const COLORS = ["#6366f1", "#06b6d4", "#f59e0b", "#ef4444", "#10b981"];
