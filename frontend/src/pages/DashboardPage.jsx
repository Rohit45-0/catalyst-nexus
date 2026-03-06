import { useEffect, useState } from "react";
import { getAnalyticsDashboard, getServiceHealth } from "../services/campaigns";
import {
  TrendingUp,
  Users,
  MousePointerClick,
  Megaphone,
  CheckCircle2,
  XCircle,
  ArrowUpRight,
  Plus,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

function MetricCard({ label, value, change, icon: Icon, color = "neutral" }) {
  const colors = {
    neutral: "bg-neutral-50 text-neutral-600",
    blue: "bg-blue-50 text-blue-600",
    emerald: "bg-emerald-50 text-emerald-600",
    violet: "bg-violet-50 text-violet-600",
  };
  return (
    <div className="cn-card group">
      <div className="flex items-start justify-between mb-4">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon size={18} strokeWidth={1.75} />
        </div>
        {change !== undefined && (
          <span className="text-xs font-medium text-emerald-600 flex items-center gap-0.5">
            <ArrowUpRight size={12} />
            {change}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-neutral-900 tracking-tight mb-1">{value}</p>
      <p className="text-sm text-neutral-500">{label}</p>
    </div>
  );
}

function StatusRow({ label, ok }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-neutral-100 last:border-0">
      <span className="text-sm text-neutral-700 font-medium">{label}</span>
      <div className={`flex items-center gap-1.5 text-xs font-medium ${ok ? "text-emerald-600" : "text-red-500"}`}>
        {ok ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
        {ok ? "Operational" : "Offline"}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState({});
  const [health, setHealth] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    getAnalyticsDashboard(30).then((r) => setSummary(r?.summary || {})).catch(() => { });
    getServiceHealth().then(setHealth).catch(() =>
      setHealth({ api: { ok: false }, analytics: { ok: false } })
    );
  }, []);

  const metrics = [
    { label: "Total Campaigns", value: summary.total_campaigns ?? 0, icon: Megaphone, color: "violet", change: 12 },
    { label: "Total Reach", value: (summary.total_reach ?? 0).toLocaleString(), icon: Users, color: "blue", change: 8 },
    { label: "Engagement", value: (summary.total_engagement ?? 0).toLocaleString(), icon: TrendingUp, color: "emerald", change: 23 },
    { label: "Click-Throughs", value: (summary.total_clicks ?? 0).toLocaleString(), icon: MousePointerClick, color: "neutral", change: 5 },
  ];

  return (
    <div className="p-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-xl font-semibold text-neutral-900 tracking-tight">Mission Control</h1>
          <p className="text-sm text-neutral-500 mt-0.5">Your campaign performance at a glance</p>
        </div>
        <button onClick={() => navigate("/campaigns")} className="btn-primary">
          <Plus size={16} strokeWidth={2} />
          New Campaign
        </button>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {metrics.map((m) => (
          <MetricCard key={m.label} {...m} />
        ))}
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* System Health */}
        <div className="cn-card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-neutral-900">System Health</h2>
            <span className="cn-badge-success">All Systems</span>
          </div>
          <StatusRow label="Core API" ok={health?.api?.ok} />
          <StatusRow label="Analytics Engine" ok={health?.analytics?.ok} />
          <StatusRow label="AI Models" ok={true} />
          <StatusRow label="Media Pipeline" ok={true} />
        </div>

        {/* Quick Actions */}
        <div className="cn-card">
          <h2 className="text-sm font-semibold text-neutral-900 mb-4">Quick Actions</h2>
          <div className="space-y-2">
            {[
              { label: "Launch new campaign", sub: "AI-powered video & poster generation", path: "/campaigns" },
              { label: "Analyze competitors", sub: "Scan top players in your niche", path: "/competitor-intel" },
              { label: "View content library", sub: "Browse all generated assets", path: "/content-library" },
            ].map((action) => (
              <button
                key={action.label}
                onClick={() => navigate(action.path)}
                className="w-full flex items-center justify-between p-3 rounded-lg border border-neutral-200 hover:border-neutral-900 hover:bg-neutral-50 transition-all duration-100 text-left group"
              >
                <div>
                  <p className="text-sm font-medium text-neutral-900">{action.label}</p>
                  <p className="text-xs text-neutral-500 mt-0.5">{action.sub}</p>
                </div>
                <ArrowUpRight size={15} className="text-neutral-300 group-hover:text-neutral-900 transition-colors" />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
