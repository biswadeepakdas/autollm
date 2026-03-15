"use client";

import { Check, X, Lightbulb, Sparkles } from "lucide-react";
import { Card, Badge, Btn, SuggIcon, Spinner } from "@/components/ui";
import { useProject } from "@/contexts/ProjectContext";
import { useApiData } from "@/hooks/useApiData";
import { suggestions as suggestionsApi } from "@/lib/api";
import { fmt } from "@/lib/format";

export default function SuggestionsPage() {
  const { current: project } = useProject();
  const { data: items, loading, reload, setData } = useApiData(
    project ? () => suggestionsApi.list(project.id) : null,
    [project?.id]
  );

  const handleAction = async (id: string, action: "accept" | "dismiss") => {
    if (!project) return;
    try {
      await suggestionsApi.update(project.id, id, action);
      if (action === "dismiss") {
        setData((items || []).filter((s: any) => s.id !== id));
      } else {
        setData((items || []).map((s: any) => s.id === id ? { ...s, status: "accepted" } : s));
      }
    } catch {
      reload();
    }
  };

  const pending = (items || []).filter((s: any) => s.status === "pending");
  const totalSave = pending.reduce((s: number, i: any) => s + (i.estimated_savings_cents || 0), 0);

  if (!project) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Suggestions</h1>
        <Card className="p-12 text-center">
          <p className="text-gray-500">Create a project first to see suggestions.</p>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="w-8 h-8" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Suggestions</h1>
          <p className="text-gray-500 text-sm mt-1">Cost-saving recommendations based on your actual LLM usage patterns.</p>
        </div>
        {totalSave > 0 && (
          <div className="flex items-center gap-3 px-5 py-3 bg-emerald-50 border border-emerald-100 rounded-2xl">
            <Sparkles size={18} className="text-emerald-600" />
            <div>
              <p className="text-sm font-bold text-emerald-800">{fmt(totalSave)}/mo saveable</p>
              <p className="text-xs text-emerald-600">{pending.length} pending suggestions</p>
            </div>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {(items || []).map((s: any) => (
          <Card key={s.id} className={`p-5 transition-all ${s.status === "accepted" ? "bg-emerald-50/50 border-emerald-100" : ""}`}>
            <div className="flex gap-4">
              <SuggIcon type={s.type} />
              <div className="flex-1 min-w-0">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-1.5">
                  <h3 className="font-semibold text-gray-900 text-sm leading-snug">{s.title}</h3>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-sm font-bold text-emerald-600 tabular-nums">{fmt(s.estimated_savings_cents || 0)}/mo</span>
                    <Badge variant={s.confidence > 0.8 ? "success" : s.confidence > 0.6 ? "warning" : "default"}>
                      {Math.round((s.confidence || 0) * 100)}%
                    </Badge>
                  </div>
                </div>
                <p className="text-sm text-gray-500 mb-3 leading-relaxed">{s.description}</p>
                {s.status === "pending" ? (
                  <div className="flex items-center gap-2">
                    <Btn variant="primary" size="sm" onClick={() => handleAction(s.id, "accept")}>
                      <Check size={14} />Apply
                    </Btn>
                    <Btn variant="ghost" size="sm" onClick={() => handleAction(s.id, "dismiss")}>
                      <X size={14} />Dismiss
                    </Btn>
                  </div>
                ) : (
                  <Badge variant="success"><Check size={12} />Applied</Badge>
                )}
              </div>
            </div>
          </Card>
        ))}

        {(items || []).length === 0 && (
          <Card className="py-16 text-center">
            <Lightbulb size={36} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500">No suggestions right now.</p>
            <p className="text-sm text-gray-400 mt-1">Keep logging requests and we&apos;ll find savings for you.</p>
          </Card>
        )}
      </div>
    </div>
  );
}
