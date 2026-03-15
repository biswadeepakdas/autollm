"use client";

import { useState } from "react";
import { Plus, Activity, DollarSign, TrendingDown, Clock, Code, Settings, ToggleLeft, ToggleRight } from "lucide-react";
import { Card, Btn, Spinner } from "@/components/ui";
import { useProject } from "@/contexts/ProjectContext";
import { useApiData } from "@/hooks/useApiData";
import { features as featuresApi } from "@/lib/api";
import { fmt, fmtK } from "@/lib/format";

export default function FeaturesPage() {
  const { current: project } = useProject();
  const { data: featureList, loading, reload } = useApiData(
    project ? () => featuresApi.list(project.id) : null,
    [project?.id]
  );
  const [autos, setAutos] = useState<Record<string, boolean>>({});
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");

  const toggleAuto = async (featureId: string, currentVal: boolean) => {
    if (!project) return;
    const next = !currentVal;
    setAutos((p) => ({ ...p, [featureId]: next }));
    try {
      await featuresApi.updateSettings(project.id, featureId, { auto_mode: next });
    } catch {
      setAutos((p) => ({ ...p, [featureId]: currentVal }));
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!project || !newName.trim()) return;
    setCreating(true);
    try {
      await featuresApi.create(project.id, newName.trim());
      setNewName("");
      reload();
    } catch {
      // handle error
    } finally {
      setCreating(false);
    }
  };

  if (!project) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900">Features</h1>
        <Card className="p-12 text-center">
          <p className="text-gray-500">Create a project first to manage features.</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Features</h1>
          <p className="text-gray-500 text-sm mt-1">Each feature in your app that calls an LLM. Toggle Auto mode per feature.</p>
        </div>
      </div>

      {/* Create feature form */}
      <Card className="p-4">
        <form onSubmit={handleCreate} className="flex items-center gap-3">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="New feature name (e.g. Chat Support)"
            className="flex-1 px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition"
          />
          <Btn type="submit" disabled={creating || !newName.trim()}>
            <Plus size={16} />{creating ? "Adding..." : "Add feature"}
          </Btn>
        </form>
      </Card>

      {loading ? (
        <div className="flex justify-center py-12"><Spinner className="w-8 h-8" /></div>
      ) : (
        <div className="space-y-3">
          {(featureList || []).map((f: any) => {
            const autoOn = autos[f.id] ?? f.auto_mode ?? false;
            return (
              <Card key={f.id} className="p-5 hover:border-gray-200 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2 flex-wrap">
                      <h3 className="font-semibold text-gray-900">{f.name}</h3>
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-gray-100 text-gray-500 text-xs font-mono">
                        <Code size={10} />{f.slug}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm text-gray-500">
                      <span className="flex items-center gap-1.5">
                        <Activity size={14} className="text-gray-400" />{fmtK(f.request_count || 0)} requests
                      </span>
                      <span className="flex items-center gap-1.5">
                        <DollarSign size={14} className="text-gray-400" />{fmt(f.cost_cents || 0)} spent
                      </span>
                      <span className="flex items-center gap-1.5 text-emerald-600">
                        <TrendingDown size={14} />{fmt(f.savings_cents || 0)} saveable
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Clock size={14} className="text-gray-400" />{f.avg_latency_ms || 0}ms avg
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 flex-shrink-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-gray-400">Auto</span>
                      <button onClick={() => toggleAuto(f.id, autoOn)} className="focus:outline-none">
                        {autoOn
                          ? <ToggleRight size={30} className="text-emerald-500" />
                          : <ToggleLeft size={30} className="text-gray-300 hover:text-gray-400 transition" />}
                      </button>
                    </div>
                    <Btn variant="ghost" size="sm"><Settings size={14} /></Btn>
                  </div>
                </div>
              </Card>
            );
          })}

          {(featureList || []).length === 0 && (
            <Card className="py-16 text-center">
              <Activity size={36} className="mx-auto text-gray-300 mb-3" />
              <p className="text-gray-500">No features yet.</p>
              <p className="text-sm text-gray-400 mt-1">Features are auto-created when your SDK sends its first request, or add one above.</p>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
