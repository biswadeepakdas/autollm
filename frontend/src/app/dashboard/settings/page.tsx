"use client";

import { useState, useEffect } from "react";
import { Zap, ToggleLeft, ToggleRight, Key, Plus, Trash2, Check, Eye, EyeOff, Copy } from "lucide-react";
import { Card, Badge, Btn, GoogleIcon, Spinner } from "@/components/ui";
import { useAuth } from "@/contexts/AuthContext";
import { useProject } from "@/contexts/ProjectContext";
import { useApiData } from "@/hooks/useApiData";
import { projects as projectsApi } from "@/lib/api";

export default function SettingsPage() {
  const { user, loginWithGoogle } = useAuth();
  const { current: project, createProject } = useProject();

  // Project settings
  const [globalAuto, setGlobalAuto] = useState(false);
  const [budget, setBudget] = useState("");
  const [maxTok, setMaxTok] = useState("");
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  // API keys
  const { data: keys, loading: keysLoading, reload: reloadKeys } = useApiData(
    project ? () => projectsApi.keys(project.id) : null,
    [project?.id]
  );
  const [newKey, setNewKey] = useState<string | null>(null);
  const [showKey, setShowKey] = useState(false);

  // New project creation
  const [newProjectName, setNewProjectName] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);

  // Load settings when project changes
  useEffect(() => {
    if (project) {
      // These would come from a settings endpoint
      setGlobalAuto(false);
      setBudget("327");
      setMaxTok("4096");
    }
  }, [project?.id]);

  const handleSave = async () => {
    if (!project) return;
    setSaving(true);
    try {
      await projectsApi.updateSettings(project.id, {
        auto_mode_global: globalAuto,
        monthly_budget_cents: Math.round(parseFloat(budget) * 100),
        default_max_tokens: parseInt(maxTok),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // handle error
    } finally {
      setSaving(false);
    }
  };

  const handleCreateKey = async () => {
    if (!project) return;
    try {
      const result = await projectsApi.createKey(project.id);
      setNewKey(result.raw_key);
      reloadKeys();
    } catch {
      // handle error
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;
    setCreatingProject(true);
    try {
      await createProject(newProjectName.trim());
      setNewProjectName("");
    } catch {
      // handle error
    } finally {
      setCreatingProject(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500 text-sm mt-1">Project configuration, API keys, and Auto mode controls.</p>
        </div>
        {project && (
          <Btn variant={saved ? "success" : "primary"} onClick={handleSave} disabled={saving}>
            {saved ? <><Check size={16} />Saved</> : saving ? "Saving..." : "Save changes"}
          </Btn>
        )}
      </div>

      {/* Create project if none exist */}
      {!project && (
        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-3">Create your first project</h3>
          <form onSubmit={handleCreateProject} className="flex items-center gap-3">
            <input
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="Project name (e.g. My SaaS App)"
              className="flex-1 px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition"
            />
            <Btn type="submit" disabled={creatingProject || !newProjectName.trim()}>
              <Plus size={16} />{creatingProject ? "Creating..." : "Create project"}
            </Btn>
          </form>
        </Card>
      )}

      {project && (
        <>
          {/* Auto mode */}
          <Card className="p-6">
            <h3 className="font-semibold text-gray-900 mb-1">Auto mode</h3>
            <p className="text-sm text-gray-500 mb-4">Automatically routes requests to cheaper models and enforces token caps while preserving quality.</p>
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
              <div className="flex items-center gap-3">
                <Zap size={20} className={globalAuto ? "text-emerald-500" : "text-gray-400"} />
                <div>
                  <p className="font-medium text-gray-900">Global Auto mode</p>
                  <p className="text-xs text-gray-500">Applies to all features unless overridden per-feature</p>
                </div>
              </div>
              <button onClick={() => setGlobalAuto(!globalAuto)} className="focus:outline-none">
                {globalAuto
                  ? <ToggleRight size={34} className="text-emerald-500" />
                  : <ToggleLeft size={34} className="text-gray-300" />}
              </button>
            </div>
          </Card>

          {/* Budget & API keys row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card className="p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Budget & limits</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Monthly budget</label>
                  <div className="relative">
                    <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                    <input
                      type="number"
                      value={budget}
                      onChange={(e) => setBudget(e.target.value)}
                      className="w-full pl-7 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition"
                    />
                  </div>
                  <p className="text-xs text-gray-400 mt-1.5">Get alerts when projected spend exceeds this amount</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Default max tokens</label>
                  <input
                    type="number"
                    value={maxTok}
                    onChange={(e) => setMaxTok(e.target.value)}
                    className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none transition"
                  />
                  <p className="text-xs text-gray-400 mt-1.5">Applied to new features automatically</p>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="font-semibold text-gray-900 mb-4">API keys</h3>

              {/* New key alert */}
              {newKey && (
                <div className="mb-4 p-3 bg-amber-50 border border-amber-100 rounded-xl">
                  <p className="text-sm font-medium text-amber-800 mb-2">Copy your API key now — it won&apos;t be shown again:</p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-xs bg-white px-3 py-2 rounded-lg border border-amber-200 break-all">
                      {showKey ? newKey : "••••••••••••••••••••"}
                    </code>
                    <button onClick={() => setShowKey(!showKey)} className="text-amber-600 hover:text-amber-800">
                      {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                    <button
                      onClick={() => { navigator.clipboard.writeText(newKey); }}
                      className="text-amber-600 hover:text-amber-800"
                    >
                      <Copy size={16} />
                    </button>
                  </div>
                </div>
              )}

              {keysLoading ? (
                <div className="flex justify-center py-4"><Spinner /></div>
              ) : (
                <div className="space-y-3 mb-4">
                  {(keys || []).map((k: any) => (
                    <div key={k.id} className="flex items-center justify-between p-3.5 bg-gray-50 rounded-xl">
                      <div className="flex items-center gap-3">
                        <Key size={16} className="text-gray-400" />
                        <div>
                          <p className="text-sm font-medium text-gray-900">{k.name || "API Key"}</p>
                          <p className="text-xs text-gray-400 font-mono">{k.key_prefix}...</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="success">Active</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <Btn variant="secondary" size="sm" onClick={handleCreateKey}>
                <Plus size={14} />Generate new key
              </Btn>
            </Card>
          </div>

          {/* Connected accounts */}
          <Card className="p-6">
            <h3 className="font-semibold text-gray-900 mb-4">Connected accounts</h3>
            {user?.oauth_providers?.includes("google") ? (
              <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                <div className="flex items-center gap-3">
                  <GoogleIcon />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Google</p>
                    <p className="text-xs text-gray-400">{user.email}</p>
                  </div>
                </div>
                <Badge variant="success">Connected</Badge>
              </div>
            ) : (
              <button
                onClick={loginWithGoogle}
                className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition w-full"
              >
                <GoogleIcon />
                <div className="text-left">
                  <p className="text-sm font-medium text-gray-900">Connect Google</p>
                  <p className="text-xs text-gray-400">Link your Google account for easy sign-in</p>
                </div>
              </button>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
