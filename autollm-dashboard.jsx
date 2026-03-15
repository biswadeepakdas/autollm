import { useState } from "react";
import {
  BarChart3, Zap, Shield, ArrowRight, Check, X,
  Settings, CreditCard, LogOut, Plus, Trash2, Key, Eye, EyeOff,
  TrendingDown, AlertTriangle, Lightbulb,
  Activity, DollarSign, Clock, ToggleLeft, ToggleRight,
  Layers, Code, Sparkles, Lock, ChevronRight, Menu
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from "recharts";

/* ═══════════════════════════════════════════════════════════════════════════
   MOCK DATA
   ═══════════════════════════════════════════════════════════════════════ */

const USER = { name: "Biswadeepak", email: "biswadeepakdas@gmail.com" };

const seed = (i) => Math.abs(Math.sin(i * 9301 + 49297) % 1);
const DAILY = Array.from({ length: 30 }, (_, i) => ({
  date: `Mar ${i + 1}`,
  requests: Math.floor(800 + seed(i) * 1200),
  cost: +(5 + seed(i + 10) * 15).toFixed(2),
  savings: +(2 + seed(i + 20) * 8).toFixed(2),
}));

const FEATURES = [
  { id: "1", name: "Onboarding Summary", slug: "onboarding-summary", requests: 12480, cost_cents: 4230, savings_cents: 1890, avg_latency_ms: 420 },
  { id: "2", name: "Chat Support", slug: "chat-support", requests: 8920, cost_cents: 8710, savings_cents: 3200, avg_latency_ms: 680 },
  { id: "3", name: "Doc Analysis", slug: "doc-analysis", requests: 3100, cost_cents: 12400, savings_cents: 5100, avg_latency_ms: 1240 },
  { id: "4", name: "Email Drafts", slug: "email-drafts", requests: 6700, cost_cents: 1890, savings_cents: 940, avg_latency_ms: 350 },
  { id: "5", name: "Code Review", slug: "code-review", requests: 2100, cost_cents: 9800, savings_cents: 4300, avg_latency_ms: 1800 },
];

const MODELS = [
  { provider: "openai", model: "gpt-4.1", count: 14200, cost_cents: 18400 },
  { provider: "anthropic", model: "claude-sonnet-4", count: 8400, cost_cents: 12800 },
  { provider: "openai", model: "gpt-4.1-mini", count: 6800, cost_cents: 2100 },
  { provider: "gemini", model: "gemini-2.5-flash", count: 3900, cost_cents: 890 },
];

const INITIAL_SUGGESTIONS = [
  { id: "s1", type: "model_downgrade", title: "Switch Chat Support from gpt-4.1 to gpt-4.1-mini", description: "Chat Support averages 280 tokens/prompt — well under the threshold for gpt-4.1. Switching to gpt-4.1-mini could save ~$32/month with comparable quality for short prompts.", estimated_savings_cents: 3200, confidence: 0.87, status: "pending", priority: 90 },
  { id: "s2", type: "token_cap", title: "Set a 2,048 token cap on Doc Analysis", description: "Completions range from 400 to 8,200 tokens. Setting a cap at 2,048 (p95) would prevent outlier costs without affecting 95% of requests.", estimated_savings_cents: 1800, confidence: 0.78, status: "pending", priority: 70 },
  { id: "s3", type: "budget_alert", title: "On track to exceed monthly budget by $45", description: "You've spent $186 in 15 days. At this rate, you'll hit $372 by month end — $45 over your $327 budget. Consider enabling Auto mode to reduce costs automatically.", estimated_savings_cents: 4500, confidence: 0.92, status: "pending", priority: 100 },
  { id: "s4", type: "provider_mix", title: "Try Gemini 2.5 Flash for Email Drafts", description: "A cross-provider switch from gpt-4.1-mini to gemini-2.5-flash could save ~$8/month. Test quality with a small percentage of traffic first.", estimated_savings_cents: 800, confidence: 0.65, status: "pending", priority: 40 },
];

const PLANS = [
  { name: "Free", code: "plan_free", price: 0, monthly_request_limit: 5000, max_projects: 1, max_features: 5, auto_mode: false, support: "Community" },
  { name: "Pro", code: "plan_pro", price: 49, monthly_request_limit: 100000, max_projects: 5, max_features: 50, auto_mode: true, support: "Email" },
  { name: "Max", code: "plan_max", price: 149, monthly_request_limit: 1000000, max_projects: 20, max_features: 200, auto_mode: true, support: "Priority" },
];

const COLORS = ["#6366f1", "#06b6d4", "#f59e0b", "#ef4444", "#10b981"];
const fmt = (cents) => `$${(cents / 100).toFixed(2)}`;
const fmtK = (n) => n >= 1000000 ? `${(n / 1000000).toFixed(1)}M` : n >= 1000 ? `${(n / 1000).toFixed(1)}K` : String(n);

/* ═══════════════════════════════════════════════════════════════════════════
   DESIGN SYSTEM — tiny reusable components
   ═══════════════════════════════════════════════════════════════════════ */

function Card({ children, className = "", onClick }) {
  return (
    <div className={`bg-white rounded-2xl border border-gray-100 shadow-sm ${className}`} onClick={onClick}>
      {children}
    </div>
  );
}

const badgeStyles = {
  default: "bg-gray-100 text-gray-700",
  success: "bg-emerald-50 text-emerald-700",
  warning: "bg-amber-50 text-amber-700",
  danger: "bg-red-50 text-red-700",
  info: "bg-indigo-50 text-indigo-700",
};

function Badge({ children, variant = "default" }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${badgeStyles[variant]}`}>
      {children}
    </span>
  );
}

const btnVariants = {
  primary: "bg-gray-900 text-white hover:bg-gray-800 shadow-sm",
  secondary: "bg-white text-gray-700 border border-gray-200 hover:bg-gray-50",
  ghost: "text-gray-500 hover:text-gray-900 hover:bg-gray-100",
  success: "bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm",
};
const btnSizes = {
  sm: "px-3 py-1.5 text-xs gap-1.5",
  md: "px-4 py-2 text-sm gap-2",
  lg: "px-5 py-2.5 text-sm gap-2",
};

function Btn({ children, variant = "primary", size = "md", className = "", disabled, onClick }) {
  return (
    <button
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center font-semibold rounded-xl transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed ${btnVariants[variant]} ${btnSizes[size]} ${className}`}
    >
      {children}
    </button>
  );
}

function StatCard({ icon: Icon, label, value, sub, trend, accent = "#6366f1", bg = "#eef2ff" }) {
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

function UsageBar({ label, current, max }) {
  const pct = Math.min((current / max) * 100, 100);
  const near = pct > 80;
  const over = pct >= 100;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className={`font-medium ${over ? "text-red-600" : near ? "text-amber-600" : "text-gray-900"}`}>
          {fmtK(current)} / {fmtK(max)}
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${over ? "bg-red-500" : near ? "bg-amber-400" : "bg-indigo-500"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function SuggIcon({ type }) {
  const m = {
    model_downgrade: { I: TrendingDown, c: "text-indigo-600", b: "bg-indigo-50" },
    token_cap: { I: Shield, c: "text-cyan-600", b: "bg-cyan-50" },
    budget_alert: { I: AlertTriangle, c: "text-amber-600", b: "bg-amber-50" },
    provider_mix: { I: Layers, c: "text-violet-600", b: "bg-violet-50" },
    low_value_cut: { I: Trash2, c: "text-red-600", b: "bg-red-50" },
  };
  const { I, c, b } = m[type] || { I: Lightbulb, c: "text-gray-600", b: "bg-gray-50" };
  return <div className={`p-2.5 rounded-xl flex-shrink-0 ${b}`}><I size={18} className={c} /></div>;
}

const GoogleSvg = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
);

/* ═══════════════════════════════════════════════════════════════════════════
   AUTH SCREEN
   ═══════════════════════════════════════════════════════════════════════ */

function AuthScreen({ onLogin }) {
  const [tab, setTab] = useState("login");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [name, setName] = useState("");
  const [showPw, setShowPw] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2.5 mb-3">
            <div className="w-11 h-11 bg-gray-900 rounded-2xl flex items-center justify-center shadow-lg">
              <Zap size={22} className="text-white" />
            </div>
            <span className="text-2xl font-extrabold text-gray-900 tracking-tight">AutoLLM</span>
          </div>
          <p className="text-gray-400 text-sm">Auto mode for your SaaS LLM bill</p>
        </div>

        <Card className="p-7">
          <div className="flex bg-gray-100 rounded-xl p-1 mb-6">
            {["login", "register"].map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex-1 py-2 text-sm font-semibold rounded-lg transition-all ${tab === t ? "bg-white shadow-sm text-gray-900" : "text-gray-400 hover:text-gray-600"}`}
              >
                {t === "login" ? "Sign in" : "Create account"}
              </button>
            ))}
          </div>

          <button
            onClick={onLogin}
            className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all"
          >
            <GoogleSvg /> Continue with Google
          </button>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200" /></div>
            <div className="relative flex justify-center"><span className="px-3 bg-white text-xs text-gray-400">or continue with email</span></div>
          </div>

          <form onSubmit={(e) => { e.preventDefault(); onLogin(); }} className="space-y-4">
            {tab === "register" && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Name</label>
                <input value={name} onChange={e => setName(e.target.value)} className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm outline-none transition" placeholder="Your name" />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm outline-none transition" placeholder="you@company.com" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Password</label>
              <div className="relative">
                <input type={showPw ? "text" : "password"} value={pw} onChange={e => setPw(e.target.value)} className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm outline-none transition pr-10" placeholder="Min. 8 characters" />
                <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <Btn variant="primary" size="lg" className="w-full">
              {tab === "login" ? "Sign in" : "Create account"}
              <ArrowRight size={16} />
            </Btn>
          </form>
        </Card>

        <p className="text-center text-xs text-gray-400 mt-6">
          By continuing, you agree to AutoLLM's Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   SIDEBAR
   ═══════════════════════════════════════════════════════════════════════ */

function Sidebar({ page, setPage, onLogout, mobileOpen, setMobileOpen }) {
  const items = [
    { id: "overview", label: "Overview", icon: BarChart3 },
    { id: "features", label: "Features", icon: Layers },
    { id: "suggestions", label: "Suggestions", icon: Lightbulb, badge: 4 },
    { id: "settings", label: "Settings", icon: Settings },
    { id: "pricing", label: "Pricing", icon: CreditCard },
  ];

  const inner = (
    <div className="flex flex-col h-full">
      <div className="p-5 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-gray-900 rounded-xl flex items-center justify-center">
            <Zap size={17} className="text-white" />
          </div>
          <div>
            <span className="font-bold text-gray-900 text-lg leading-none tracking-tight">AutoLLM</span>
            <p className="text-xs text-gray-400 tracking-widest font-semibold" style={{ fontSize: 10 }}>COST OPTIMIZER</p>
          </div>
        </div>
        {mobileOpen && (
          <button onClick={() => setMobileOpen(false)} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        )}
      </div>

      <div className="px-6 pt-4 pb-1">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider" style={{ fontSize: 11 }}>Dashboard</p>
      </div>

      <nav className="flex-1 px-3 space-y-0.5 py-1">
        {items.map(it => {
          const active = page === it.id;
          return (
            <button
              key={it.id}
              onClick={() => { setPage(it.id); setMobileOpen(false); }}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${active ? "bg-gray-900 text-white shadow-sm" : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"}`}
            >
              <it.icon size={18} />
              {it.label}
              {it.badge && (
                <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-semibold ${active ? "bg-white/20 text-white" : "bg-amber-100 text-amber-700"}`}>
                  {it.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-100">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 bg-indigo-100 rounded-full flex items-center justify-center text-sm font-bold text-indigo-600">
            {USER.name[0]}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">{USER.name}</p>
            <p className="text-xs text-gray-400 truncate">{USER.email}</p>
          </div>
        </div>
        <div className="flex items-center justify-between">
          <Badge variant="info">Pro plan</Badge>
          <button onClick={onLogout} className="text-gray-400 hover:text-gray-600 transition">
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:block w-64 bg-white border-r border-gray-100 h-screen sticky top-0 flex-shrink-0">
        {inner}
      </div>
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

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE — OVERVIEW
   ═══════════════════════════════════════════════════════════════════════ */

function OverviewPage() {
  const totalCost = DAILY.reduce((s, d) => s + d.cost, 0);
  const totalSavings = DAILY.reduce((s, d) => s + d.savings, 0);
  const totalReqs = DAILY.reduce((s, d) => s + d.requests, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1 text-sm">Your LLM usage and optimization overview for the last 30 days.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={DollarSign} label="Total LLM spend" value={`$${totalCost.toFixed(0)}`} trend={12} accent="#ef4444" bg="#fef2f2" />
        <StatCard icon={TrendingDown} label="Potential savings" value={`$${totalSavings.toFixed(0)}`} sub={`${Math.round((totalSavings / totalCost) * 100)}% of total spend`} accent="#10b981" bg="#ecfdf5" />
        <StatCard icon={Activity} label="Total requests" value={fmtK(totalReqs)} trend={-5} accent="#6366f1" bg="#eef2ff" />
        <StatCard icon={Clock} label="Avg latency" value="580ms" sub="p95: 1,240ms" accent="#06b6d4" bg="#ecfeff" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 p-6">
          <h3 className="font-semibold text-gray-900 mb-1">Spend vs. potential savings</h3>
          <p className="text-xs text-gray-400 mb-4">Daily breakdown over the last 30 days</p>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={DAILY} margin={{ top: 5, right: 5, bottom: 5, left: -10 }}>
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
              <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e5e7eb", boxShadow: "0 4px 16px rgba(0,0,0,.08)", fontSize: 13 }} formatter={(v) => [`$${Number(v).toFixed(2)}`]} />
              <Area type="monotone" dataKey="cost" stroke="#ef4444" fill="url(#cG)" strokeWidth={2} name="Spend" />
              <Area type="monotone" dataKey="savings" stroke="#10b981" fill="url(#sG)" strokeWidth={2} name="Savings" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-1">Spend by model</h3>
          <p className="text-xs text-gray-400 mb-3">Cost distribution across providers</p>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={MODELS} dataKey="cost_cents" nameKey="model" cx="50%" cy="50%" outerRadius={72} innerRadius={46} paddingAngle={3} strokeWidth={0}>
                {MODELS.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Pie>
              <Tooltip formatter={v => fmt(v)} contentStyle={{ borderRadius: 12, border: "1px solid #e5e7eb", fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2.5 mt-1">
            {MODELS.map((m, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: COLORS[i] }} />
                  <span className="text-gray-600 truncate">{m.model}</span>
                </div>
                <span className="font-semibold text-gray-900" style={{ fontVariantNumeric: "tabular-nums" }}>{fmt(m.cost_cents)}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="font-semibold text-gray-900">Plan usage this month</h3>
          <Badge variant="info">Pro plan</Badge>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <UsageBar label="Monthly requests" current={34200} max={100000} />
          <UsageBar label="Projects" current={3} max={5} />
          <UsageBar label="Features (this project)" current={5} max={50} />
        </div>
      </Card>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE — FEATURES
   ═══════════════════════════════════════════════════════════════════════ */

function FeaturesPage() {
  const [autos, setAutos] = useState({});
  const toggle = (id) => setAutos(p => ({ ...p, [id]: !p[id] }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Features</h1>
          <p className="text-gray-500 text-sm mt-1">Each feature in your app that calls an LLM. Toggle Auto mode per feature.</p>
        </div>
        <Btn><Plus size={16} />Add feature</Btn>
      </div>

      <div className="space-y-3">
        {FEATURES.map(f => (
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
                  <span className="flex items-center gap-1.5"><Activity size={14} className="text-gray-400" />{fmtK(f.requests)} requests</span>
                  <span className="flex items-center gap-1.5"><DollarSign size={14} className="text-gray-400" />{fmt(f.cost_cents)} spent</span>
                  <span className="flex items-center gap-1.5 text-emerald-600"><TrendingDown size={14} />{fmt(f.savings_cents)} saveable</span>
                  <span className="flex items-center gap-1.5"><Clock size={14} className="text-gray-400" />{f.avg_latency_ms}ms avg</span>
                </div>
              </div>

              <div className="flex items-center gap-4 flex-shrink-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-gray-400">Auto</span>
                  <button onClick={() => toggle(f.id)} className="focus:outline-none">
                    {autos[f.id]
                      ? <ToggleRight size={30} className="text-emerald-500" />
                      : <ToggleLeft size={30} className="text-gray-300 hover:text-gray-400 transition" />}
                  </button>
                </div>
                <Btn variant="ghost" size="sm"><Settings size={14} /></Btn>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE — SUGGESTIONS
   ═══════════════════════════════════════════════════════════════════════ */

function SuggestionsPage() {
  const [items, setItems] = useState(INITIAL_SUGGESTIONS);
  const dismiss = (id) => setItems(p => p.filter(s => s.id !== id));
  const accept = (id) => setItems(p => p.map(s => s.id === id ? { ...s, status: "accepted" } : s));
  const pending = items.filter(s => s.status === "pending");
  const totalSave = pending.reduce((s, i) => s + i.estimated_savings_cents, 0);

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
        {items.map(s => (
          <Card key={s.id} className={`p-5 transition-all ${s.status === "accepted" ? "bg-emerald-50/50 border-emerald-100" : ""}`}>
            <div className="flex gap-4">
              <SuggIcon type={s.type} />
              <div className="flex-1 min-w-0">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-1.5">
                  <h3 className="font-semibold text-gray-900 text-sm leading-snug">{s.title}</h3>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-sm font-bold text-emerald-600" style={{ fontVariantNumeric: "tabular-nums" }}>{fmt(s.estimated_savings_cents)}/mo</span>
                    <Badge variant={s.confidence > 0.8 ? "success" : s.confidence > 0.6 ? "warning" : "default"}>
                      {Math.round(s.confidence * 100)}%
                    </Badge>
                  </div>
                </div>
                <p className="text-sm text-gray-500 mb-3 leading-relaxed">{s.description}</p>
                {s.status === "pending" ? (
                  <div className="flex items-center gap-2">
                    <Btn variant="primary" size="sm" onClick={() => accept(s.id)}><Check size={14} />Apply</Btn>
                    <Btn variant="ghost" size="sm" onClick={() => dismiss(s.id)}><X size={14} />Dismiss</Btn>
                  </div>
                ) : (
                  <Badge variant="success"><Check size={12} />Applied</Badge>
                )}
              </div>
            </div>
          </Card>
        ))}

        {items.length === 0 && (
          <Card className="py-16 text-center">
            <Lightbulb size={36} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500">No suggestions right now.</p>
            <p className="text-sm text-gray-400 mt-1">Keep logging requests and we'll find savings for you.</p>
          </Card>
        )}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE — SETTINGS
   ═══════════════════════════════════════════════════════════════════════ */

function SettingsPage() {
  const [globalAuto, setGlobalAuto] = useState(true);
  const [budget, setBudget] = useState("327");
  const [maxTok, setMaxTok] = useState("4096");
  const [saved, setSaved] = useState(false);
  const save = () => { setSaved(true); setTimeout(() => setSaved(false), 2000); };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-500 text-sm mt-1">Project configuration, API keys, and Auto mode controls.</p>
        </div>
        <Btn variant={saved ? "success" : "primary"} onClick={save}>
          {saved ? <><Check size={16} />Saved</> : "Save changes"}
        </Btn>
      </div>

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
            {globalAuto ? <ToggleRight size={34} className="text-emerald-500" /> : <ToggleLeft size={34} className="text-gray-300" />}
          </button>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Budget & limits</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Monthly budget</label>
              <div className="relative">
                <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
                <input type="number" value={budget} onChange={e => setBudget(e.target.value)} className="w-full pl-7 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm outline-none transition" />
              </div>
              <p className="text-xs text-gray-400 mt-1.5">Get alerts when projected spend exceeds this amount</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Default max tokens</label>
              <input type="number" value={maxTok} onChange={e => setMaxTok(e.target.value)} className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm outline-none transition" />
              <p className="text-xs text-gray-400 mt-1.5">Applied to new features automatically</p>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">API keys</h3>
          <div className="space-y-3 mb-4">
            <div className="flex items-center justify-between p-3.5 bg-gray-50 rounded-xl">
              <div className="flex items-center gap-3">
                <Key size={16} className="text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Default</p>
                  <p className="text-xs text-gray-400 font-mono">allm_a8xK...j2mP</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="success">Active</Badge>
                <Btn variant="ghost" size="sm"><Trash2 size={14} /></Btn>
              </div>
            </div>
          </div>
          <Btn variant="secondary" size="sm"><Plus size={14} />Generate new key</Btn>
        </Card>
      </div>

      <Card className="p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Connected accounts</h3>
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div className="flex items-center gap-3">
            <GoogleSvg />
            <div>
              <p className="text-sm font-medium text-gray-900">Google</p>
              <p className="text-xs text-gray-400">{USER.email}</p>
            </div>
          </div>
          <Badge variant="success">Connected</Badge>
        </div>
      </Card>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   PAGE — PRICING
   ═══════════════════════════════════════════════════════════════════════ */

function PricingPage() {
  const current = "plan_pro";

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900">Plans & pricing</h1>
        <p className="text-gray-500 text-sm mt-1">Start free. Upgrade when your LLM bill needs it.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 max-w-4xl mx-auto">
        {PLANS.map(p => {
          const isCurrent = p.code === current;
          const isPop = p.code === "plan_pro";
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
                  <span className="text-4xl font-extrabold text-gray-900 tracking-tight">${p.price}</span>
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
                  <span className="text-gray-600">Up to <strong className="text-gray-900">{p.max_features}</strong> features/project</span>
                </div>
                <div className={`flex items-center gap-2.5 text-sm ${p.auto_mode ? "" : "opacity-50"}`}>
                  {p.auto_mode
                    ? <Zap size={16} className="text-amber-500 flex-shrink-0" />
                    : <Lock size={16} className="text-gray-300 flex-shrink-0" />}
                  <span className="text-gray-600">
                    Auto mode {p.auto_mode ? <strong className="text-gray-900">enabled</strong> : "(view only)"}
                  </span>
                </div>
                <div className="flex items-center gap-2.5 text-sm">
                  <Check size={16} className="text-emerald-500 flex-shrink-0" />
                  <span className="text-gray-600">{p.support} support</span>
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
                <Btn variant={isPop ? "primary" : "secondary"} className="w-full">
                  {p.price === 0 ? "Downgrade" : "Upgrade"}<ArrowRight size={14} />
                </Btn>
              )}
            </Card>
          );
        })}
      </div>

      <Card className="p-6 max-w-4xl mx-auto overflow-x-auto">
        <h3 className="font-semibold text-gray-900 mb-4">Full comparison</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="py-3 px-4 text-left text-gray-400 font-medium text-xs uppercase tracking-wide">Feature</th>
              {PLANS.map(p => (
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

/* ═══════════════════════════════════════════════════════════════════════════
   MAIN APP
   ═══════════════════════════════════════════════════════════════════════ */

export default function App() {
  const [authed, setAuthed] = useState(false);
  const [page, setPage] = useState("overview");
  const [mobileOpen, setMobileOpen] = useState(false);

  if (!authed) return <AuthScreen onLogin={() => setAuthed(true)} />;

  const pages = {
    overview: OverviewPage,
    features: FeaturesPage,
    suggestions: SuggestionsPage,
    settings: SettingsPage,
    pricing: PricingPage,
  };
  const Page = pages[page] || OverviewPage;

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar page={page} setPage={setPage} onLogout={() => setAuthed(false)} mobileOpen={mobileOpen} setMobileOpen={setMobileOpen} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile header */}
        <div className="lg:hidden flex items-center justify-between p-4 bg-white border-b border-gray-100">
          <button onClick={() => setMobileOpen(true)} className="text-gray-600"><Menu size={22} /></button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-gray-900 rounded-lg flex items-center justify-center"><Zap size={14} className="text-white" /></div>
            <span className="font-bold text-gray-900">AutoLLM</span>
          </div>
          <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center text-xs font-bold text-indigo-600">B</div>
        </div>

        <main className="flex-1 p-5 lg:p-8 max-w-6xl w-full">
          <Page />
        </main>
      </div>
    </div>
  );
}
