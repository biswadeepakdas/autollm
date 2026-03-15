"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { BarChart3, Layers, Lightbulb, Settings, CreditCard, LogOut, Zap, X, Shield } from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";
import { useProject } from "@/contexts/ProjectContext";

const navItems = [
  { href: "/dashboard", label: "Overview", icon: BarChart3 },
  { href: "/dashboard/features", label: "Features", icon: Layers },
  { href: "/dashboard/suggestions", label: "Suggestions", icon: Lightbulb, badgeKey: "suggestions" },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
  { href: "/dashboard/pricing", label: "Pricing", icon: CreditCard },
];

interface SidebarProps {
  mobileOpen: boolean;
  setMobileOpen: (open: boolean) => void;
  suggestionCount?: number;
}

export function Sidebar({ mobileOpen, setMobileOpen, suggestionCount = 0 }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { current: project } = useProject();

  const handleLogout = async () => {
    await logout();
    window.location.href = "/login";
  };

  const inner = (
    <div className="flex flex-col h-full">
      {/* Brand */}
      <div className="p-5 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-gray-900 rounded-xl flex items-center justify-center">
            <Zap size={17} className="text-white" />
          </div>
          <div>
            <span className="font-bold text-gray-900 text-lg leading-none tracking-tight">AutoLLM</span>
            <p className="text-[10px] text-gray-400 tracking-widest font-semibold">COST OPTIMIZER</p>
          </div>
        </div>
        {mobileOpen && (
          <button onClick={() => setMobileOpen(false)} className="lg:hidden text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        )}
      </div>

      {/* Project name */}
      {project && (
        <div className="px-6 pt-4 pb-1">
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">{project.name}</p>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 px-3 space-y-0.5 py-1">
        {navItems.map((item) => {
          const active = item.href === "/dashboard"
            ? pathname === "/dashboard"
            : (pathname ?? "").startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
                active
                  ? "bg-gray-900 text-white shadow-sm"
                  : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <item.icon size={18} />
              {item.label}
              {item.badgeKey === "suggestions" && suggestionCount > 0 && (
                <span
                  className={`ml-auto text-xs px-2 py-0.5 rounded-full font-semibold ${
                    active ? "bg-white/20 text-white" : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {suggestionCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User */}
      {user && (
        <div className="p-4 border-t border-gray-100">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-9 h-9 bg-indigo-100 rounded-full flex items-center justify-center text-sm font-bold text-indigo-600">
              {(user.name || user.email)[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">{user.name || "User"}</p>
              <p className="text-xs text-gray-400 truncate">{user.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-sm font-medium text-gray-500 hover:text-red-600 hover:bg-red-50 transition-all duration-150"
          >
            <LogOut size={16} />
            Sign out
          </button>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop */}
      <aside className="hidden lg:block w-64 bg-white border-r border-gray-100 h-screen sticky top-0 flex-shrink-0">
        {inner}
      </aside>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div className="w-72 bg-white h-full shadow-2xl">{inner}</div>
          <div className="flex-1 bg-black/30" onClick={() => setMobileOpen(false)} />
        </div>
      )}
    </>
  );
}
