"use client";

import { Check, Zap, Lock, Sparkles, ArrowRight } from "lucide-react";
import { Card, Btn, Spinner } from "@/components/ui";
import { useApiData } from "@/hooks/useApiData";
import { billing } from "@/lib/api";
import { fmtK } from "@/lib/format";

export default function PricingPage() {
  const { data: plans, loading: plansLoading } = useApiData(() => billing.plans(), []);
  const { data: subscription, loading: subLoading } = useApiData(() => billing.subscription(), []);

  const currentCode = subscription?.code || "plan_free";
  const loading = plansLoading || subLoading;

  const handleChangePlan = async (planCode: string) => {
    try {
      await billing.changePlan(planCode);
      window.location.reload();
    } catch {
      // handle error
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="w-8 h-8" />
      </div>
    );
  }

  const planList = plans || [
    { name: "Free", code: "plan_free", price_monthly_cents: 0, monthly_request_limit: 5000, max_projects: 1, max_features_per_project: 5, auto_mode_enabled: false, support_tier: "Community" },
    { name: "Pro", code: "plan_pro", price_monthly_cents: 4900, monthly_request_limit: 100000, max_projects: 5, max_features_per_project: 50, auto_mode_enabled: true, support_tier: "Email" },
    { name: "Max", code: "plan_max", price_monthly_cents: 14900, monthly_request_limit: 1000000, max_projects: 20, max_features_per_project: 200, auto_mode_enabled: true, support_tier: "Priority" },
  ];

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900">Plans & pricing</h1>
        <p className="text-gray-500 text-sm mt-1">Start free. Upgrade when your LLM bill needs it.</p>
      </div>

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 max-w-4xl mx-auto">
        {planList.map((p: any) => {
          const isCurrent = p.code === currentCode;
          const isPop = p.code === "plan_pro";
          const price = Math.round((p.price_monthly_cents || 0) / 100);

          return (
            <Card
              key={p.code}
              className={`p-6 relative transition-shadow ${isPop ? "border-2 border-gray-900 shadow-lg" : ""} ${isCurrent ? "ring-2 ring-indigo-500 ring-offset-2" : ""}`}
            >
              {isPop && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="bg-gray-900 text-white text-xs font-bold px-3 py-1 rounded-full shadow">Most popular</span>
                </div>
              )}
              <div className="text-center mb-6 pt-1">
                <h3 className="text-lg font-bold text-gray-900">{p.name}</h3>
                <div className="mt-3">
                  <span className="text-4xl font-extrabold text-gray-900 tracking-tight">${price}</span>
                  <span className="text-gray-500 text-sm">/mo</span>
                </div>
              </div>
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-2.5 text-sm">
                  <Check size={16} className="text-emerald-500 flex-shrink-0" />
                  <span className="text-gray-600">Up to <strong className="text-gray-900">{fmtK(p.monthly_request_limit)}</strong> requests/mo</span>
                </div>
                <div className="flex items-center gap-2.5 text-sm">
                  <Check size={16} className="text-emerald-500 flex-shrink-0" />
                  <span className="text-gray-600"><strong className="text-gray-900">{p.max_projects}</strong> project{p.max_projects > 1 ? "s" : ""}</span>
                </div>
                <div className="flex items-center gap-2.5 text-sm">
                  <Check size={16} className="text-emerald-500 flex-shrink-0" />
                  <span className="text-gray-600">Up to <strong className="text-gray-900">{p.max_features_per_project}</strong> features/project</span>
                </div>
                <div className={`flex items-center gap-2.5 text-sm ${p.auto_mode_enabled ? "" : "opacity-50"}`}>
                  {p.auto_mode_enabled
                    ? <Zap size={16} className="text-amber-500 flex-shrink-0" />
                    : <Lock size={16} className="text-gray-300 flex-shrink-0" />}
                  <span className="text-gray-600">
                    Auto mode {p.auto_mode_enabled ? <strong className="text-gray-900">enabled</strong> : "(view only)"}
                  </span>
                </div>
                <div className="flex items-center gap-2.5 text-sm">
                  <Check size={16} className="text-emerald-500 flex-shrink-0" />
                  <span className="text-gray-600">{p.support_tier} support</span>
                </div>
                {p.code === "plan_max" && (
                  <div className="flex items-center gap-2.5 text-sm">
                    <Sparkles size={16} className="text-violet-500 flex-shrink-0" />
                    <span className="text-gray-600">Priority processing</span>
                  </div>
                )}
              </div>
              {isCurrent ? (
                <Btn variant="secondary" className="w-full" disabled>Current plan</Btn>
              ) : (
                <Btn
                  variant={isPop ? "primary" : "secondary"}
                  className="w-full"
                  onClick={() => handleChangePlan(p.code)}
                >
                  {price === 0 ? "Downgrade" : "Upgrade"}<ArrowRight size={14} />
                </Btn>
              )}
            </Card>
          );
        })}
      </div>

      {/* Comparison table */}
      <Card className="p-6 max-w-4xl mx-auto overflow-x-auto">
        <h3 className="font-semibold text-gray-900 mb-4">Full comparison</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="py-3 px-4 text-left text-gray-400 font-medium text-xs uppercase tracking-wide">Feature</th>
              {planList.map((p: any) => (
                <th key={p.code} className="py-3 px-4 text-center font-semibold text-gray-900">{p.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ["Monthly requests", "5K", "100K", "1M"],
              ["Projects", "1", "5", "20"],
              ["Features / project", "5", "50", "200"],
              ["Auto mode", "View only", "Full", "Full"],
              ["Cost suggestions", "Basic", "All", "All + priority"],
              ["Support", "Community", "Email", "Priority email"],
              ["Billing integration", "\u2014", "Stripe", "Stripe + invoices"],
            ].map(([label, ...vals], i) => (
              <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50 transition-colors">
                <td className="py-3 px-4 text-gray-600">{label}</td>
                {vals.map((v, j) => (
                  <td key={j} className="py-3 px-4 text-center text-gray-900 font-medium">{v}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
