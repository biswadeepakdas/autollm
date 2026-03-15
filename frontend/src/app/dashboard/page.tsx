"use client";

import { DollarSign, TrendingDown, Activity, Clock } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import { Card, Badge, StatCard, UsageBar, Spinner } from "@/components/ui";
import { useProject } from "@/contexts/ProjectContext";
import { useApiData } from "@/hooks/useApiData";
import { stats, projects as projectsApi } from "@/lib/api";
import { fmt, fmtK, COLORS } from "@/lib/format";

export default function OverviewPage() {
  const { current: project } = useProject();

  const { data: overview, loading } = useApiData(
    project ? () => stats.overview(project.id) : null,
    [project?.id]
  );

  const { data: usage } = useApiData(
    project ? () => projectsApi.usage(project.id) : null,
    [project?.id]
  );

  if (!project) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <Card className="p-12 text-center">
          <p className="text-gray-500">No project selected. Create your first project in Settings.</p>
        </Card>
      </div>
    );
  }

  if (loading || !overview) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="w-8 h-8" />
      </div>
    );
  }

  const { daily = [], top_models = [], totals = {} } = overview;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1 text-sm">Your LLM usage and optimization overview for the last 30 days.</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={DollarSign}
          label="Total LLM spend"
          value={fmt(totals.cost_cents || 0)}
          trend={totals.cost_trend}
          accent="#ef4444"
          bg="#fef2f2"
        />
        <StatCard
          icon={TrendingDown}
          label="Potential savings"
          value={fmt(totals.savings_cents || 0)}
          sub={totals.cost_cents ? `${Math.round((totals.savings_cents / totals.cost_cents) * 100)}% of total spend` : undefined}
          accent="#10b981"
          bg="#ecfdf5"
        />
        <StatCard
          icon={Activity}
          label="Total requests"
          value={fmtK(totals.request_count || 0)}
          trend={totals.request_trend}
          accent="#6366f1"
          bg="#eef2ff"
        />
        <StatCard
          icon={Clock}
          label="Avg latency"
          value={`${totals.avg_latency_ms || 0}ms`}
          sub={totals.p95_latency_ms ? `p95: ${totals.p95_latency_ms}ms` : undefined}
          accent="#06b6d4"
          bg="#ecfeff"
        />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 p-6">
          <h3 className="font-semibold text-gray-900 mb-1">Spend vs. potential savings</h3>
          <p className="text-xs text-gray-400 mb-4">Daily breakdown over the last 30 days</p>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={daily} margin={{ top: 5, right: 5, bottom: 5, left: -10 }}>
              <defs>
                <linearGradient id="cG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ef4444" stopOpacity={0.12} />
                  <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="sG" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} interval={4} />
              <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} tickFormatter={(v: number) => `$${(v / 100).toFixed(0)}`} />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: "1px solid #e5e7eb", boxShadow: "0 4px 16px rgba(0,0,0,.08)", fontSize: 13 }}
                formatter={(v: number) => [fmt(v)]}
              />
              <Area type="monotone" dataKey="cost_cents" stroke="#ef4444" fill="url(#cG)" strokeWidth={2} name="Spend" />
              <Area type="monotone" dataKey="savings_cents" stroke="#10b981" fill="url(#sG)" strokeWidth={2} name="Savings" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-1">Spend by model</h3>
          <p className="text-xs text-gray-400 mb-3">Cost distribution across providers</p>
          {top_models.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={top_models}
                    dataKey="cost_cents"
                    nameKey="model"
                    cx="50%"
                    cy="50%"
                    outerRadius={72}
                    innerRadius={46}
                    paddingAngle={3}
                    strokeWidth={0}
                  >
                    {top_models.map((_: any, i: number) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => fmt(v)} contentStyle={{ borderRadius: 12, border: "1px solid #e5e7eb", fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2.5 mt-1">
                {top_models.map((m: any, i: number) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                      <span className="text-gray-600 truncate">{m.model}</span>
                    </div>
                    <span className="font-semibold text-gray-900 tabular-nums">{fmt(m.cost_cents)}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-sm text-gray-400 text-center py-12">No data yet</p>
          )}
        </Card>
      </div>

      {/* Plan usage */}
      {usage && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="font-semibold text-gray-900">Plan usage this month</h3>
            <Badge variant="info">{usage?.plan?.name || "Free"} plan</Badge>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <UsageBar label="Monthly requests" current={usage?.usage?.requests?.current || 0} max={usage?.usage?.requests?.limit || 5000} />
            <UsageBar label="Projects" current={usage?.usage?.projects?.current || 0} max={usage?.usage?.projects?.limit || 1} />
            <UsageBar label="Features (this project)" current={usage?.usage?.features?.current || 0} max={usage?.usage?.features?.limit || 5} />
          </div>
        </Card>
      )}
    </div>
  );
}
