"use client";

import { useState, useEffect } from "react";
import { Users, Activity, DollarSign, PieChart, Shield, ShieldOff } from "lucide-react";
import { Card, Btn, Spinner } from "@/components/ui";
import { admin } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

export default function AdminPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    loadData();
  }, [page]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, u] = await Promise.all([
        admin.stats(),
        admin.users(page),
      ]);
      setStats(s);
      setUsers(u);
    } catch (e: any) {
      setError(e.message || "Failed to load admin data. You may not have admin access.");
    } finally {
      setLoading(false);
    }
  };

  const handleChangePlan = async (userId: string, planCode: string) => {
    try {
      await admin.changeUserPlan(userId, planCode);
      loadData();
    } catch (e: any) {
      alert(e.message || "Failed to change plan");
    }
  };

  const handleToggleAdmin = async (userId: string) => {
    try {
      await admin.toggleAdmin(userId);
      loadData();
    } catch (e: any) {
      alert(e.message || "Failed to toggle admin");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="w-8 h-8" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-24">
        <p className="text-red-600 mb-4">{error}</p>
        <p className="text-sm text-gray-500">Admin access is required to view this page.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>

      {/* Stats grid */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <Users size={20} className="text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Users</p>
                <p className="text-xl font-bold text-gray-900">{stats.users}</p>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                <Activity size={20} className="text-emerald-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Requests</p>
                <p className="text-xl font-bold text-gray-900">{stats.total_requests?.toLocaleString()}</p>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                <DollarSign size={20} className="text-amber-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Total Cost</p>
                <p className="text-xl font-bold text-gray-900">${((stats.total_cost_cents || 0) / 100).toFixed(2)}</p>
              </div>
            </div>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-violet-100 rounded-lg flex items-center justify-center">
                <PieChart size={20} className="text-violet-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Projects</p>
                <p className="text-xl font-bold text-gray-900">{stats.projects}</p>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Plan distribution */}
      {stats?.plan_distribution && Object.keys(stats.plan_distribution).length > 0 && (
        <Card className="p-5">
          <h3 className="font-semibold text-gray-900 mb-3">Plan Distribution</h3>
          <div className="flex gap-6">
            {Object.entries(stats.plan_distribution).map(([plan, count]: any) => (
              <div key={plan} className="text-center">
                <p className="text-2xl font-bold text-gray-900">{count}</p>
                <p className="text-sm text-gray-500">{plan}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Users table */}
      {users && (
        <Card className="p-5">
          <h3 className="font-semibold text-gray-900 mb-4">Users ({users.total})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="py-2 px-3 text-left text-gray-400 font-medium text-xs uppercase">Email</th>
                  <th className="py-2 px-3 text-left text-gray-400 font-medium text-xs uppercase">Name</th>
                  <th className="py-2 px-3 text-left text-gray-400 font-medium text-xs uppercase">Plan</th>
                  <th className="py-2 px-3 text-left text-gray-400 font-medium text-xs uppercase">Admin</th>
                  <th className="py-2 px-3 text-left text-gray-400 font-medium text-xs uppercase">Joined</th>
                  <th className="py-2 px-3 text-left text-gray-400 font-medium text-xs uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.users.map((u: any) => (
                  <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                    <td className="py-2 px-3 text-gray-900">{u.email}</td>
                    <td className="py-2 px-3 text-gray-600">{u.name || "—"}</td>
                    <td className="py-2 px-3">
                      <select
                        value={u.plan === "Free" ? "plan_free" : u.plan === "Pro" ? "plan_pro" : "plan_max"}
                        onChange={(e) => handleChangePlan(u.id, e.target.value)}
                        className="text-xs border border-gray-200 rounded px-2 py-1"
                      >
                        <option value="plan_free">Free</option>
                        <option value="plan_pro">Pro</option>
                        <option value="plan_max">Max</option>
                      </select>
                    </td>
                    <td className="py-2 px-3">
                      {u.is_admin ? (
                        <span className="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
                          <Shield size={12} /> Admin
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">User</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-gray-500 text-xs">
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2 px-3">
                      <button
                        onClick={() => handleToggleAdmin(u.id)}
                        className="text-xs text-indigo-600 hover:text-indigo-700 font-medium"
                        title={u.is_admin ? "Remove admin" : "Make admin"}
                      >
                        {u.is_admin ? <ShieldOff size={14} /> : <Shield size={14} />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {users.pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <Btn
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Btn>
              <span className="text-sm text-gray-500">
                Page {page} of {users.pages}
              </span>
              <Btn
                variant="secondary"
                size="sm"
                disabled={page >= users.pages}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Btn>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
