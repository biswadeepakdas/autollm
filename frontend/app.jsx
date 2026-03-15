import { useState, useEffect, useCallback } from "react";
import {
  BarChart3, Zap, Shield, ArrowRight, ArrowUpRight, Check, X,
  Settings, CreditCard, LogOut, Plus, Trash2, Key, Eye, EyeOff,
  TrendingDown, TrendingUp, AlertTriangle, Lightbulb, ChevronDown,
  Activity, DollarSign, Clock, Server, ToggleLeft, ToggleRight,
  Layers, Code, ExternalLink, Menu, ChevronRight, Sparkles, Lock
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from "recharts";

// ── Mock data for demo ──────────────────────────────────────────────────────
const MOCK_USER = { name: "Biswadeepak", email: "biswadeepakdas@gmail.com", plan_name: "Pro", plan_code: "plan_pro" };
const MOCK_DAILY = Array.from({ length: 30 }, (_, i) => ({
  date: `Mar ${i + 1}`, requests: Math.floor(800 + Math.random() * 1200),
  cost: +(5 + Math.random() * 15).toFixed(2), savings: +(2 + Math.random() * 8).toFixed(2),
}));
const MOCK_FEATURES = [
  { id: "1", name: "Onboarding Summary", slug: "onboarding-summary", requests: 12480, cost_cents: 4230, savings_cents: 1890, avg_latency_ms: 420 },
  { id: "2", name: "Chat Support", slug: "chat-support", requests: 8920, cost_cents: 8710, savings_cents: 3200, avg_latency_ms: 680 },
  { id: "3", name: "Doc Analysis", slug: "doc-analysis", requests: 3100, cost_cents: 12400, savings_cents: 5100, avg_latency_ms: 1240 },
  { id: "4", name: "Email Drafts", slug: "email-drafts", requests: 6700, cost_cents: 1890, savings_cents: 940, avg_latency_ms: 350 },
  { id: "5", name: "Code Review", slug: "code-review", requests: 2100, cost_cents: 9800, savings_cents: 4300, avg_latency_ms: 1800 },
];
const MOCK_MODELS = [
  { provider: "openai", model: "gpt-4.1", count: 14200, cost_cents: 18400 },
  { provider: "anthropic", model: "claude-sonnet-4-20250514", count: 8400, cost_cents: 12800 },
  { provider: "openai", model: "gpt-4.1-mini", count: 6800, cost_cents: 2100 },
  { provider: "gemini", model: "gemini-2.5-flash", count: 3900, cost_cents: 890 },
];
const MOCK_SUGGESTIONS = [
  { id: "s1", type: "model_downgrade", title: "Switch Chat Support from gpt-4.1 to gpt-4.1-mini", description: "Chat Support averages 280 tokens/prompt — well below the threshold for gpt-4.1. Switching to gpt-4.1-mini could save ~$32/month with comparable quality.", estimated_savings_cents: 3200, confidence: 0.87, status: "pending", priority: 90 },
  { id: "s2", type: "token_cap", title: "Set a 2,048 token cap on Doc Analysis", description: "Completions range from 400 to 8,200 tokens. Setting a cap at 2,048 (p95) prevents outlier costs without affecting 95% of requests.", estimated_savings_cents: 1800, confidence: 0.78, status: "pending", priority: 70 },
  { id: "s3", type: "budget_alert", title: "On track to exceed monthly budget by $45", description: "You've spent $186 in 15 days. At this rate, you'll hit $372 by month end — $45 over your $327 budget.", estimated_savings_cents: 4500, confidence: 0.92, status: "pending", priority: 100 },
  { id: "s4", type: "provider_mix", title: "Try Gemini 2.5 Flash for Email Drafts", description: "Cross-provider switch from gpt-4.1-mini to gemini-2.5-flash could save ~$8/month. Test with a small traffic percentage first.", estimated_savings_cents: 800, confidence: 0.65, status: "pending", priority: 40 },
];
const PLANS = [
  { name: "Free", code: "plan_free", price: 0, monthly_request_limit: 5000, max_projects: 1, max_features_per_project: 5, auto_mode_enabled: false },
  { name: "Pro", code: "plan_pro", price: 49, monthly_request_limit: 100000, max_projects: 5, max_features_per_project: 50, auto_mode_enabled: true },
  { name: "Max", code: "plan_max", price: 149, monthly_request_limit: 1000000, max_projects: 20, max_features_per_project: 200, auto_mode_enabled: true },
];

const COLORS = ["#6366f1", "#06b6d4", "#f59e0b", "#ef4444", "#10b981", "#8b5cf6"];

const fmt = (cents) => `$${(cents / 100).toFixed(2)}`;
const fmtK = (n) => n >= 1000000 ? `${(n/1000000).toFixed(1)}M` : n >= 1000 ? `${(n/1000).toFixed(1)}K` : n;

// ── Reusable Components ─────────────────────────────────────────────────────

function Card({ children, className = "", ...props }) {
  return <div className={`bg-white rounded-2xl border border-gray-100 shadow-sm ${className}`} {...props}>{children}</div>;
}

function Badge({ children, variant = "default" }) {
  const styles = {
    default: "bg-gray-100 text-gray-700",
    success: "bg-emerald-50 text-emerald-700",
    warning: "bg-amber-50 text-amber-700",
    danger: "bg-red-50 text-red-700",
    info: "bg-indigo-50 text-indigo-700",
    purple: "bg-violet-50 text-violet-700",
  };
  return <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles[variant]}`}>{children}</span>;
}

function Button({ children, variant = "primary", size = "md", className = "", ...props }) {
  const base = "inline-flex items-center justify-center font-medium rounded-xl transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2";
  const variants = {
    primary: "bg-gray-900 text-white hover:bg-gray-800 focus:ring-gray-500 shadow-sm",
    secondary: "bg-white text-gray-700 border border-gray-200 hover:bg-gray-50 focus:ring-gray-300",
    ghost: "text-gray-600 hover:text-gray-900 hover:bg-gray-100 focus:ring-gray-300",
    danger: "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500",
    success: "bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500",
  };
  const sizes = { sm: "px-3 py-1.5 text-sm gap-1.5", md: "px-4 py-2 text-sm gap-2", lg: "px-6 py-3 text-base gap-2" };
  return <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props}>{children}</button>;
}

function StatCard({ icon: Icon, label, value, subvalue, trend, color = "gray" }) {
  const colorMap = { gray: "bg-gray-50", indigo: "bg-indigo-50", emerald: "bg-emerald-50", amber: "bg-amber-50", red: "bg-red-50", cyan: "bg-cyan-50" };
  const iconColors = { gray: "text-gray-600", indigo: "text-indigo-600", emerald: "text-emerald-600", amber: "text-amber-600", red: "text-red-600", cyan: "text-cyan-600" };
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between">
        <div className={`p-2.5 rounded-xl ${colorMap[color]}`}><Icon size={20} className={iconColors[color]} /></div>
        {trend && <span className={`text-xs font-medium ${trend > 0 ? "text-red-500" : "text-emerald-500"}`}>{trend > 0 ? "+" : ""}{trend}%</span>}
      </div>
      <div className="mt-3">
        <p className="text-2xl font-bold text-gray-900 tracking-tight">{value}</p>
        <p className="text-sm text-gray-500 mt-0.5">{label}</p>
        {subvalue && <p className="text-xs text-gray-400 mt-1">{subvalue}</p>}
      </div>
    </Card>
  );
}

function UsageBar({ label, current, max, unit = "" }) {
  const pct = Math.min((current / max) * 100, 100);
  const isNear = pct > 80;
  const isOver = pct >= 100;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">{label}</span>
        <span className={`font-medium ${isOver ? "text-red-600" : isNear ? "text-amber-600" : "text-gray-900"}`}>
          {fmtK(current)} / {fmtK(max)}{unit}
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${isOver ? "bg-red-500" : isNear ? "bg-amber-400" : "bg-indigo-500"}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function SuggestionIcon({ type }) {
  const map = {
    model_downgrade: { icon: TrendingDown, color: "text-indigo-600 bg-indigo-50" },
    token_cap: { icon: Shield, color: "text-cyan-600 bg-cyan-50" },
    budget_alert: { icon: AlertTriangle, color: "text-amber-600 bg-amber-50" },
    provider_mix: { icon: Layers, color: "text-violet-600 bg-violet-50" },
    low_value_cut: { icon: Trash2, color: "text-red-600 bg-red-50" },
  };
  const { icon: Icon, color } = map[type] || { icon: Lightbulb, color: "text-gray-600 bg-gray-50" };
  return <div className={`p-2.5 rounded-xl ${color}`}><Icon size={18} /></div>;
}

// ── Auth Screen ─────────────────────────────────────────────────────────────

function AuthScreen({ onLogin }) {
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPw, setShowPw] = useState(false);

  const handleSubmit = (e) => { e.preventDefault(); onLogin(); };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-10 h-10 bg-gray-900 rounded-xl flex items-center justify-center"><Zap size={20} className="text-white" /></div>
            <span className="text-2xl font-bold text-gray-900 tracking-tight">AutoLLM</span>
          </div>
          <p className="text-gray-500">Auto mode for your SaaS LLM bill</p>
        </div>
        <Card className="p-8">
          <div className="flex bg-gray-100 rounded-xl p-1 mb-6">
            <button onClick={() => setMode("login")} className={`flex-1 py-2 text-sm font-medium rounded-lg transition ${mode === "login" ? "bg-white shadow-sm text-gray-900" : "text-gray-500"}`}>Sign in</button>
            <button onClick={() => setMode("register")} className={`flex-1 py-2 text-sm font-medium rounded-lg transition ${mode === "register" ? "bg-white shadow-sm text-gray-900" : "text-gray-500"}`}>Create account</button>
          </div>
          <button className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-200 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-50 transition mb-4">
            <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            Continue with Google
          </button>
          <div className="relative my-6"><div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-200" /></div><div className="relative flex justify-center text-xs"><span className="px-3 bg-white text-gray-400">or continue with email</span></div></div>
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && <div><label className="block text-sm font-medium text-gray-700 mb-1">Name</label><input type="text" value={name} onChange={e => setName(e.target.value)} className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none" placeholder="Your name" /></div>}
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Email</label><input type="email" value={email} onChange={e => setEmail(e.target.value)} className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none" placeholder="you@company.com" required /></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Password</label><div className="relative"><input type={showPw ? "text" : "password"} value={password} onChange={e => setPassword(e.target.value)} className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none pr-10" placeholder="Min. 8 characters" required /><button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">{showPw ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></div>
            <Button variant="primary" size="lg" className="w-full">{mode === "login" ? "Sign in" : "Create account"}<ArrowRight size={16} /></Button>
          </form>
        </Card>
        <p className="text-center text-xs text-gray-400 mt-6">By continuing, you agree to AutoLLM's Terms of Service and Privacy Policy.</p>
      </div>
    </div>
  );
}

// ── Sidebar ─────────────────────────────────────────────────────────────────

function Sidebar({ page, setPage, onLogout }) {
  const navItems = [
    { id: "overview", label: "Overview", icon: BarChart3 },
    { id: "features", label: "Features", icon: Layers },
    { id: "suggestions", label: "Suggestions", icon: Lightbulb },
    { id: "settings", label: "Settings", icon: Settings },
    { id: "pricing", label: "Pricing", icon: CreditCard },
  ];
  return (
    <aside className="w-64 bg-white border-r border-gray-100 flex flex-col h-screen sticky top-0">
      <div className="p-5 border-b border-gray-100">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 bg-gray-900 rounded-xl flex items-center justify-center"><Zap size={18} className="text-white" /></div>
          <div><span className="font-bold text-gray-900 text-lg tracking-tight">AutoLLM</span><p className="text-[10px] text-gray-400 -mt-0.5 tracking-wide">COST OPTIMIZER</p></div>
        </div>
      </div>
      <div className="px-3 py-2"><p className="px-3 py-2 text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Dashboard</p></div>
      <nav className="flex-1 px-3 space-y-0.5">
        {navItems.map(item => (
          <button key={item.id} onClick={() => setPage(item.id)} className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${page === item.id ? "bg-gray-900 text-white shadow-sm" : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"}`}>
            <item.icon size={18} />{item.label}
            {item.id === "suggestions" && <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${page === "suggestions" ? "bg-white/20 text-white" : "bg-amber-100 text-amber-700"}`}>4</span>}
          </button>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-100">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 bg-indigo-100 rounded-full flex items-center justify-center text-sm font-bold text-indigo-600">B</div>
          <div className="flex-1 min-w-0"><p className="text-sm font-medium text-gray-900 truncate">{MOCK_USER.name}</p><p className="text-xs text-gray-400 truncate">{MOCK_USER.email}</p></div>
        </div>
        <div className="flex items-center justify-between">
          <Badge variant="info">Pro plan</Badge>
          <button onClick={onLogout} className="text-gray-400 hover:text-gray-600 transition"><LogOut size={16} /></button>
        </div>
      </div>
    </aside>
  );
}

// ── Overview Page ───────────────────────────────────────────────────────────

function OverviewPage() {
  const totalCost = MOCK_DAILY.reduce((s, d) => s + d.cost, 0);
  const totalSavings = MOCK_DAILY.reduce((s, d) => s + d.savings, 0);
  const totalReqs = MOCK_DAILY.reduce((s, d) => s + d.requests, 0);
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 mt-1">Your LLM usage and optimization overview for the last 30 days.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={DollarSign} label="Total LLM spend" value={`$${totalCost.toFixed(2)}`} trend={12} color="red" />
        <StatCard icon={TrendingDown} label="Potential savings" value={`$${totalSavings.toFixed(2)}`} subvalue={`${((totalSavings / totalCost) * 100).toFixed(0)}% of spend`} color="emerald" />
        <StatCard icon={Activity} label="Total requests" value={fmtK(totalReqs)} trend={-5} color="indigo" />
        <StatCard icon={Clock} label="Avg latency" value="580ms" subvalue="p95: 1,240ms" color="cyan" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Spend vs. potential savings</h3>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={MOCK_DAILY} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
              <defs>
                <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#ef4444" stopOpacity={0.1} /><stop offset="100%" stopColor="#ef4444" stopOpacity={0} /></linearGradient>
                <linearGradient id="saveGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#10b981" stopOpacity={0.15} /><stop offset="100%" stopColor="#10b981" stopOpacity={0} /></linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} tickFormatter={v => `$${v}`} />
              <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e5e7eb", boxShadow: "0 4px 12px rgba(0,0,0,.08)" }} formatter={(v) => [`$${v.toFixed(2)}`, '']} />
              <Area type="monotone" dataKey="cost" stroke="#ef4444" fill="url(#costGrad)" strokeWidth={2} name="Spend" />
              <Area type="monotone" dataKey="savings" stroke="#10b981" fill="url(#saveGrad)" strokeWidth={2} name="Savings" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Spend by model</h3>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={MOCK_MODELS} dataKey="cost_cents" nameKey="model" cx="50%" cy="50%" outerRadius={80} innerRadius={50} paddingAngle={3} strokeWidth={0}>
                {MOCK_MODELS.map((_, i) => <Cell key={i} fill={COLORS[i]} />)}
              </Pie>
              <Tooltip formatter={v => fmt(v)} contentStyle={{ borderRadius: 12, border: "1px solid #e5e7eb" }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-2">
            {MOCK_MODELS.map((m, i) => (
              <div key={i} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full" style={{ background: COLORS[i] }} /><span className="text-gray-600">{m.model}</span></div>
                <span className="font-medium text-gray-900">{fmt(m.cost_cents)}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Plan usage</h3>
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

// ── Features Page ───────────────────────────────────────────────────────────

function FeaturesPage() {
  const [autoStates, setAutoStates] = useState({});
  const toggle = (id) => setAutoStates(prev => ({ ...prev, [id]: !prev[id] }));
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">Features</h1><p className="text-gray-500 mt-1">Each feature in your app that uses an LLM. Configure Auto mode per feature.</p></div>
        <Button><Plus size={16} />Add feature</Button>
      </div>
      <div className="space-y-3">
        {MOCK_FEATURES.map(f => (
          <Card key={f.id} className="p-5 hover:border-gray-200 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="font-semibold text-gray-900">{f.name}</h3>
                  <Badge variant="default"><Code size={10} className="mr-1" />{f.slug}</Badge>
                </div>
                <div className="flex items-center gap-6 text-sm text-gray-500">
                  <span className="flex items-center gap-1.5"><Activity size={14} />{fmtK(f.requests)} requests</span>
                  <span className="flex items-center gap-1.5"><DollarSign size={14} />{fmt(f.cost_cents)} spent</span>
                  <span className="flex items-center gap-1.5 text-emerald-600"><TrendingDown size={14} />{fmt(f.savings_cents)} saveable</span>
                  <span className="flex items-center gap-1.5"><Clock size={14} />{f.avg_latency_ms}ms avg</span>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-gray-500">Auto mode</span>
                  <button onClick={() => toggle(f.id)} className="transition-colors">
                    {autoStates[f.id] ? <ToggleRight size={28} className="text-emerald-500" /> : <ToggleLeft size={28} className="text-gray-300" />}
                  </button>
                </div>
                <Button variant="ghost" size="sm"><Settings size={14} /></Button>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Suggestions Page ────────────────────────────────────────────────────────

function SuggestionsPage() {
  const [items, setItems] = useState(MOCK_SUGGESTIONS);
  const dismiss = (id) => setItems(prev => prev.filter(s => s.id !== id));
  const accept = (id) => setItems(prev => prev.map(s => s.id === id ? { ...s, status: "accepted" } : s));
  const pending = items.filter(s => s.status === "pending");
  const totalSavings = pending.reduce((s, i) => s + i.estimated_savings_cents, 0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold text-gray-900">Suggestions</h1><p className="text-gray-500 mt-1">AI-generated recommendations to reduce your LLM costs.</p></div>
        {totalSavings > 0 && (
          <Card className="px-5 py-3 bg-emerald-50 border-emerald-100">
            <div className="flex items-center gap-3"><Sparkles size={18} className="text-emerald-600" /><div><p className="text-sm font-semibold text-emerald-800">{fmt(totalSavings)}/month saveable</p><p className="text-xs text-emerald-600">{pending.length} pending suggestions</p></div></div>
          </Card>
        )}
      </div>
      <div className="space-y-3">
        {items.map(s => (
          <Card key={s.id} className={`p-5 ${s.status === "accepted" ? "bg-emerald-50 border-emerald-100" : ""}`}>
            <div className="flex gap-4">
              <SuggestionIcon type={s.type} />
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-4 mb-1">
                  <h3 className="font-semibold text-gray-900">{s.title}</h3>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className="text-sm font-bold text-emerald-600">{fmt(s.estimated_savings_cents)}/mo</span>
                    <Badge variant={s.confidence > 0.8 ? "success" : s.confidence > 0.6 ? "warning" : "default"}>{(s.confidence * 100).toFixed(0)}% conf.</Badge>
                  </div>
                </div>
                <p className="text-sm text-gray-500 mb-3">{s.description}</p>
                {s.status === "pending" ? (
                  <div className="flex items-center gap-2">
                    <Button variant="primary" size="sm" onClick={() => accept(s.id)}><Check size={14} />Apply suggestion</Button>
                    <Button variant="ghost" size="sm" onClick={() => dismiss(s.id)}><X size={14} />Dismiss</Button>
                  </div>
                ) : (
                  <Badge variant="success"><Check size={12} className="mr-1" />Applied</Badge>
                )}
              </div>
            </div>
          </Card>
        ))}
        {items.length === 0 && (
          <Card className="p-12 text-center">
            <Lightbulb size={32} className="mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500">No suggestions right now. Keep logging requests and we'll find savings for you.</p>
          </Card>
        )}
      </div>
    </div>
  );
}

// ── Settings Page ───────────────────────────────────────────────────────────

function SettingsPage() {
  const [globalAuto, setGlobalAuto] = useState(true);
  const [budget, setBudget] = useState("327");
  const [maxTokens, setMaxTokens] = useState("4096");

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold text-gray-900">Settings</h1><p className="text-gray-500 mt-1">Project configuration, API keys, and Auto mode controls.</p></div>

      <Card className="p-6">
        <h3 className="font-semibold text-gray-900 mb-1">Auto mode</h3>
        <p className="text-sm text-gray-500 mb-4">When enabled, AutoLLM will automatically route requests to cheaper models and enforce token caps while preserving quality.</p>
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div className="flex items-center gap-3"><Zap size={20} className={globalAuto ? "text-emerald-500" : "text-gray-400"} /><div><p className="font-medium text-gray-900">Global Auto mode</p><p className="text-xs text-gray-500">Applies to all features unless overridden</p></div></div>
          <button onClick={() => setGlobalAuto(!globalAuto)}>{globalAuto ? <ToggleRight size={32} className="text-emerald-500" /> : <ToggleLeft size={32} className="text-gray-300" />}</button>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Budget & limits</h3>
          <div className="space-y-4">
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Monthly budget</label><div className="relative"><span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span><input type="number" value={budget} onChange={e => setBudget(e.target.value)} className="w-full pl-7 pr-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none" /></div><p className="text-xs text-gray-400 mt-1">Get alerts when you're on track to exceed this</p></div>
            <div><label className="block text-sm font-medium text-gray-700 mb-1">Default max tokens</label><input type="number" value={maxTokens} onChange={e => setMaxTokens(e.target.value)} className="w-full px-3.5 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-gray-900 focus:border-transparent outline-none" /><p className="text-xs text-gray-400 mt-1">Applied to new features by default</p></div>
          </div>
        </Card>

        <Card className="p-6">
          <h3 className="font-semibold text-gray-900 mb-4">API keys</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
              <div className="flex items-center gap-3"><Key size={16} className="text-gray-400" /><div><p className="text-sm font-medium text-gray-900">Default</p><p className="text-xs text-gray-400 font-mono">allm_a8xK...j2mP</p></div></div>
              <div className="flex items-center gap-2"><Badge variant="success">Active</Badge><Button variant="ghost" size="sm"><Trash2 size={14} /></Button></div>
            </div>
          </div>
          <Button variant="secondary" size="sm" className="mt-3"><Plus size={14} />Generate new key</Button>
        </Card>
      </div>

      <Card className="p-6">
        <h3 className="font-semibold text-gray-900 mb-4">Connected accounts</h3>
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
          <div className="flex items-center gap-3">
            <svg className="w-6 h-6" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            <div><p className="text-sm font-medium text-gray-900">Google</p><p className="text-xs text-gray-400">biswadeepakdas@gmail.com</p></div>
          </div>
          <Badge variant="success">Connected</Badge>
        </div>
      </Card>
    </div>
  );
}

// ── Pricing Page ────────────────────────────────────────────────────────────

function PricingPage() {
  const currentPlan = "plan_pro";
  return (
    <div className="space-y-6">
      <div className="text-center"><h1 className="text-2xl font-bold text-gray-900">Plans & pricing</h1><p className="text-gray-500 mt-1">Start free. Upgrade when your LLM bill needs it.</p></div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl mx-auto">
        {PLANS.map(plan => {
          const isCurrent = plan.code === currentPlan;
          const isPopular = plan.code === "plan_pro";
          return (
            <Card key={plan.code} className={`p-6 relative ${isPopular ? "border-2 border-gray-900 shadow-lg" : ""} ${isCurrent ? "ring-2 ring-indigo-500 ring-offset-2" : ""}`}>
              {isPopular && <div className="absolute -top-3 left-1/2 -translate-x-1/2"><span className="bg-gray-900 text-white text-xs font-bold px-3 py-1 rounded-full">Most popular</span></div>}
              <div className="text-center mb-6">
                <h3 className="text-lg font-bold text-gray-900">{plan.name}</h3>
                <div className="mt-3"><span className="text-4xl font-bold text-gray-900">${plan.price}</span><span className="text-gray-500 text-sm">/month</span></div>
              </div>
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-2.5 text-sm"><Check size={16} className="text-emerald-500 flex-shrink-0" /><span className="text-gray-600">Up to <strong className="text-gray-900">{fmtK(plan.monthly_request_limit)}</strong> requests/month</span></div>
                <div className="flex items-center gap-2.5 text-sm"><Check size={16} className="text-emerald-500 flex-shrink-0" /><span className="text-gray-600"><strong className="text-gray-900">{plan.max_projects}</strong> project{plan.max_projects > 1 ? "s" : ""}</span></div>
                <div className="flex items-center gap-2.5 text-sm"><Check size={16} className="text-emerald-500 flex-shrink-0" /><span className="text-gray-600">Up to <strong className="text-gray-900">{plan.max_features_per_project}</strong> features per project</span></div>
                <div className={`flex items-center gap-2.5 text-sm ${plan.auto_mode_enabled ? "" : "opacity-50"}`}>{plan.auto_mode_enabled ? <Zap size={16} className="text-amber-500 flex-shrink-0" /> : <Lock size={16} className="text-gray-300 flex-shrink-0" />}<span className="text-gray-600">Auto mode {plan.auto_mode_enabled ? <strong className="text-gray-900">enabled</strong> : <span>(view suggestions only)</span>}</span></div>
                {plan.code === "plan_max" && <div className="flex items-center gap-2.5 text-sm"><Sparkles size={16} className="text-violet-500 flex-shrink-0" /><span className="text-gray-600">Priority processing</span></div>}
              </div>
              {isCurrent ? (
                <Button variant="secondary" className="w-full" disabled>Current plan</Button>
              ) : (
                <Button variant={isPopular ? "primary" : "secondary"} className="w-full">{plan.price === 0 ? "Downgrade" : plan.price < 149 ? "Upgrade" : "Upgrade"}<ArrowRight size={14} /></Button>
              )}
            </Card>
          );
        })}
      </div>
      <Card className="p-6 max-w-4xl mx-auto">
        <h3 className="font-semibold text-gray-900 mb-3">Plan comparison</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-gray-100"><th className="py-3 px-4 text-left text-gray-500 font-medium">Feature</th>{PLANS.map(p => <th key={p.code} className="py-3 px-4 text-center font-medium text-gray-900">{p.name}</th>)}</tr></thead>
            <tbody>
              {[
                ["Monthly requests", "5K", "100K", "1M"],
                ["Projects", "1", "5", "20"],
                ["Features per project", "5", "50", "200"],
                ["Auto mode", "View only", "Full", "Full"],
                ["Cost suggestions", "Basic", "All", "All + priority"],
                ["Support", "Community", "Email", "Priority email"],
              ].map(([label, ...vals], i) => (
                <tr key={i} className="border-b border-gray-50"><td className="py-3 px-4 text-gray-600">{label}</td>{vals.map((v, j) => <td key={j} className="py-3 px-4 text-center text-gray-900 font-medium">{v}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────────────────

export default function App() {
  const [authed, setAuthed] = useState(false);
  const [page, setPage] = useState("overview");

  if (!authed) return <AuthScreen onLogin={() => setAuthed(true)} />;

  const pages = { overview: OverviewPage, features: FeaturesPage, suggestions: SuggestionsPage, settings: SettingsPage, pricing: PricingPage };
  const PageComponent = pages[page] || OverviewPage;

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar page={page} setPage={setPage} onLogout={() => setAuthed(false)} />
      <main className="flex-1 p-8 max-w-6xl">{<PageComponent />}</main>
    </div>
  );
}
