import { useState, useEffect, useCallback } from "react";
import {
  Settings, User, Bell, Shield, Wrench, ChevronRight, ChevronDown,
  Loader2, Utensils, Scissors, Stethoscope, ShoppingCart,
  GraduationCap, Dumbbell, PackageOpen, Zap, Save,
  MapPin, CloudSun, BarChart3, Receipt, Users, Calendar,
  Star, PartyPopper, QrCode, CreditCard, ClipboardList,
  Eye, MailCheck, Check
} from "lucide-react";
import { getCurrentUser } from "../services/auth";
import { apiRequest } from "../services/api";

// ═══════════════════════════════════════════════════════════════════════════
//  Tool Definitions per Vertical
// ═══════════════════════════════════════════════════════════════════════════

const VERTICAL_TOOLS = {
  core: {
    label: "Core Booking Tools",
    icon: Calendar,
    color: "from-neutral-700 to-neutral-500",
    bgLight: "bg-neutral-50",
    textColor: "text-neutral-600",
    borderColor: "border-neutral-200",
    tools: [
      { id: "check_available_slots", label: "Check Availability", description: "Let AI check your Google Calendar for free slots", icon: Eye, default: true },
      { id: "book_slot", label: "Instant Booking", description: "Allow AI to book slots into your calendar", icon: Check, default: true },
      { id: "check_customer_bookings", label: "My Bookings", description: "Let customers ask 'when is my appointment?'", icon: ClipboardList, default: true },
      { id: "cancel_bookings", label: "Cancellations", description: "Allow customers to cancel their own appointments", icon: Zap, default: false },
    ]
  },
  restaurant: {
    label: "Restaurant / Mess",
    icon: Utensils,
    color: "from-orange-500 to-amber-500",
    bgLight: "bg-orange-50",
    textColor: "text-orange-600",
    borderColor: "border-orange-200",
    tools: [
      { id: "get_menu", label: "Live Menu", description: "Show menu from Google Sheets in real-time", icon: ClipboardList, default: true },
      { id: "check_item_availability", label: "Item Availability", description: "Check if a specific dish is available right now", icon: Check, default: true },
      { id: "create_order", label: "Order Taking", description: "Create and track customer orders automatically", icon: Receipt, default: true },
      { id: "get_order_history", label: "Order History", description: "Let customers reorder with 'same as last time'", icon: BarChart3, default: false },
      { id: "check_weather_and_suggest", label: "Weather Promos", description: "Auto-suggest rain/cold day promotions", icon: CloudSun, default: false },
      { id: "check_delivery_distance", label: "Delivery Distance", description: "Calculate distance and delivery charges", icon: MapPin, default: false },
    ]
  },
  tiffin: {
    label: "Tiffin Service",
    icon: PackageOpen,
    color: "from-green-500 to-emerald-500",
    bgLight: "bg-green-50",
    textColor: "text-green-600",
    borderColor: "border-green-200",
    tools: [
      { id: "get_todays_menu", label: "Today's Menu", description: "Auto-display today's lunch and dinner", icon: ClipboardList, default: true },
      { id: "create_subscription", label: "Subscriptions", description: "Create daily/weekly tiffin subscriptions", icon: Users, default: true },
      { id: "pause_subscription", label: "Pause/Resume", description: "Let customers pause during travel or holidays", icon: Calendar, default: true },
      { id: "resume_subscription", label: "Auto Resume", description: "Automatically resume after pause period ends", icon: Zap, default: true },
      { id: "check_delivery_distance", label: "Delivery Range", description: "Check if address is within delivery area", icon: MapPin, default: false },
    ]
  },
  salon: {
    label: "Salon / Parlour",
    icon: Scissors,
    color: "from-pink-500 to-rose-500",
    bgLight: "bg-pink-50",
    textColor: "text-pink-600",
    borderColor: "border-pink-200",
    tools: [
      { id: "get_salon_slots", label: "Staff Scheduling", description: "Show available slots per staff member", icon: Calendar, default: true },
      { id: "book_salon_appointment", label: "Auto Booking", description: "Book appointments directly from WhatsApp", icon: Check, default: true },
      { id: "get_loyalty_status", label: "Loyalty Program", description: "Track visits, tiers (Bronze→Platinum), and rewards", icon: Star, default: false },
    ]
  },
  clinic: {
    label: "Doctor / Clinic",
    icon: Stethoscope,
    color: "from-blue-500 to-cyan-500",
    bgLight: "bg-blue-50",
    textColor: "text-blue-600",
    borderColor: "border-blue-200",
    tools: [
      { id: "generate_token", label: "Queue Token", description: "Generate token numbers with estimated wait times", icon: QrCode, default: true },
      { id: "get_queue_status", label: "Live Queue", description: "Show current queue length and active token", icon: Users, default: true },
    ]
  },
  kirana: {
    label: "Kirana / Grocery",
    icon: ShoppingCart,
    color: "from-yellow-500 to-orange-500",
    bgLight: "bg-yellow-50",
    textColor: "text-yellow-600",
    borderColor: "border-yellow-200",
    tools: [
      { id: "search_catalog", label: "Product Search", description: "Search inventory by name with stock info", icon: Eye, default: true },
      { id: "get_udhar_balance", label: "Udhar / Khata", description: "Credit ledger — track customer balances", icon: CreditCard, default: true },
      { id: "check_delivery_distance", label: "Home Delivery", description: "Distance and delivery charge estimation", icon: MapPin, default: false },
    ]
  },
  coaching: {
    label: "Coaching / Tuition",
    icon: GraduationCap,
    color: "from-violet-500 to-purple-500",
    bgLight: "bg-violet-50",
    textColor: "text-violet-600",
    borderColor: "border-violet-200",
    tools: [
      { id: "get_attendance_report", label: "Attendance", description: "Monthly attendance reports per student", icon: ClipboardList, default: true },
      { id: "get_pending_fees", label: "Fee Tracking", description: "Show pending fee invoices to students/parents", icon: Receipt, default: true },
    ]
  },
  gym: {
    label: "Gym / Yoga Studio",
    icon: Dumbbell,
    color: "from-red-500 to-rose-500",
    bgLight: "bg-red-50",
    textColor: "text-red-600",
    borderColor: "border-red-200",
    tools: [
      { id: "check_membership", label: "Membership Status", description: "Show plan, days remaining, and streak", icon: BarChart3, default: true },
      { id: "get_class_schedule", label: "Class Schedule", description: "Upcoming classes with availability", icon: Calendar, default: true },
      { id: "book_class", label: "Class Booking", description: "Book spots with waitlist support", icon: Check, default: false },
    ]
  },
};

// ═══════════════════════════════════════════════════════════════════════════
//  Toggle Switch Component (Claude-inspired)
// ═══════════════════════════════════════════════════════════════════════════

function ToolToggle({ id, label, description, icon: Icon, enabled, onToggle, accentColor }) {
  return (
    <div
      className={`group flex items-center justify-between py-3 px-3 rounded-lg transition-all duration-150 ${enabled ? "bg-neutral-50" : "hover:bg-neutral-25"
        }`}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200 ${enabled
          ? `bg-gradient-to-br ${accentColor} text-white shadow-sm`
          : "bg-neutral-100 text-neutral-400"
          }`}>
          <Icon size={14} strokeWidth={2} />
        </div>
        <div className="min-w-0">
          <p className={`text-[13px] font-medium transition-colors ${enabled ? "text-neutral-900" : "text-neutral-600"}`}>
            {label}
          </p>
          <p className="text-[11px] text-neutral-400 leading-tight mt-0.5 truncate max-w-[240px]">
            {description}
          </p>
        </div>
      </div>
      <button
        id={`tool-toggle-${id}`}
        onClick={() => onToggle(id)}
        className={`relative flex-shrink-0 w-9 h-[20px] rounded-full transition-all duration-200 cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-neutral-400 ${enabled
          ? "bg-neutral-900"
          : "bg-neutral-200 hover:bg-neutral-300"
          }`}
        role="switch"
        aria-checked={enabled}
        aria-label={`Toggle ${label}`}
      >
        <span
          className={`absolute top-[2px] left-[2px] w-4 h-4 bg-white rounded-full shadow-sm transition-transform duration-200 ease-in-out ${enabled ? "translate-x-[16px]" : ""
            }`}
        />
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
//  Vertical Group Component (Collapsible)
// ═══════════════════════════════════════════════════════════════════════════

function VerticalGroup({ verticalKey, vertical, toolStates, onToggle, onToggleAll }) {
  const [expanded, setExpanded] = useState(false);

  const tools = vertical.tools;
  const enabledCount = tools.filter(t => toolStates[t.id]).length;
  const allEnabled = enabledCount === tools.length;
  const IconComp = vertical.icon;

  return (
    <div className={`border rounded-xl overflow-hidden transition-all duration-200 ${expanded ? `${vertical.borderColor} shadow-sm` : "border-neutral-150 hover:border-neutral-300"
      }`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-neutral-50/50 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center bg-gradient-to-br ${vertical.color} text-white shadow-sm`}>
            <IconComp size={15} strokeWidth={2} />
          </div>
          <div className="text-left">
            <p className="text-[13px] font-semibold text-neutral-800">{vertical.label}</p>
            <p className="text-[11px] text-neutral-400">
              {enabledCount}/{tools.length} tools active
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {/* Mini pill showing active count */}
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${enabledCount > 0
            ? `${vertical.bgLight} ${vertical.textColor}`
            : "bg-neutral-100 text-neutral-400"
            }`}>
            {enabledCount > 0 ? `${enabledCount} ON` : "ALL OFF"}
          </span>
          <ChevronDown
            size={14}
            className={`text-neutral-400 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
          />
        </div>
      </button>

      {/* Expandable tool list */}
      <div className={`transition-all duration-300 ease-in-out overflow-hidden ${expanded ? "max-h-[800px] opacity-100" : "max-h-0 opacity-0"
        }`}>
        <div className="px-3 pb-3 border-t border-neutral-100">
          {/* Toggle All row */}
          <div className="flex items-center justify-between py-2.5 px-3 mt-1">
            <p className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
              Toggle all
            </p>
            <button
              onClick={() => onToggleAll(verticalKey, !allEnabled)}
              className={`text-[11px] font-medium px-2.5 py-1 rounded-md transition-colors cursor-pointer ${allEnabled
                ? "bg-neutral-900 text-white hover:bg-neutral-700"
                : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                }`}
            >
              {allEnabled ? "Disable All" : "Enable All"}
            </button>
          </div>

          {/* Individual tool toggles */}
          <div className="space-y-0.5">
            {tools.map(tool => (
              <ToolToggle
                key={tool.id}
                {...tool}
                enabled={!!toolStates[tool.id]}
                onToggle={onToggle}
                accentColor={vertical.color}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
//  Original Settings Sections
// ═══════════════════════════════════════════════════════════════════════════

const baseSections = [
  {
    icon: User,
    label: "Profile",
    description: "Manage your account and campaign defaults",
    fields: [
      { id: "full_name", label: "Full Name", type: "text", placeholder: "Your name" },
      { id: "email", label: "Email", type: "email", placeholder: "you@company.com", readOnly: true },
    ],
  },
  {
    icon: Wrench,
    label: "AI Tools",
    description: "Control which tools your WhatsApp AI bot can use",
    isToolsSection: true,
  },
  {
    icon: Bell,
    label: "Notifications",
    description: "Configure alert preferences",
    fields: [],
    toggles: [
      { id: "notify_campaigns", label: "Campaign updates", description: "Get notified when campaigns complete" },
      { id: "notify_weekly", label: "Weekly digest", description: "Summary of your performance" },
    ],
  },
  {
    icon: Shield,
    label: "Security",
    description: "Password and authentication",
    fields: [
      { id: "password", label: "New Password", type: "password", placeholder: "••••••••" },
    ],
  },
];

function NotificationToggle({ label, description }) {
  const [on, setOn] = useState(false);
  return (
    <div className="flex items-center justify-between py-3 border-b border-neutral-100 last:border-0">
      <div>
        <p className="text-sm font-medium text-neutral-900">{label}</p>
        <p className="text-xs text-neutral-500 mt-0.5">{description}</p>
      </div>
      <button
        onClick={() => setOn(!on)}
        className={`relative w-10 h-5 rounded-full transition-colors duration-200 cursor-pointer ${on ? "bg-neutral-900" : "bg-neutral-200"}`}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow-xs transition-transform duration-200 ${on ? "translate-x-5" : ""}`}
        />
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════
//  Main Settings Page
// ═══════════════════════════════════════════════════════════════════════════

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState("Profile");
  const [formData, setFormData] = useState({});
  const [saving, setSaving] = useState(false);
  const [toolsSaving, setToolsSaving] = useState(false);
  const [msg, setMsg] = useState({ text: "", type: "" });

  // Tool states: { tool_id: boolean }
  const [toolStates, setToolStates] = useState(() => {
    // Initialize all tools with their default state
    const defaults = {};
    Object.values(VERTICAL_TOOLS).forEach(v => {
      v.tools.forEach(t => { defaults[t.id] = t.default; });
    });
    return defaults;
  });
  const [toolsLoaded, setToolsLoaded] = useState(false);

  const PLUGINS_API = import.meta.env.VITE_PLUGINS_API_URL || "https://web-production-ba9e.up.railway.app";
  const PLUGINS_FRONTEND = import.meta.env.VITE_PLUGINS_FRONTEND_URL || "http://localhost:5174";

  useEffect(() => {
    getCurrentUser().then(user => {
      if (user) setFormData(user);
    }).catch(console.error);

    // Load tool preferences from the backend
    const token = localStorage.getItem("cn_access_token");
    if (token) {
      fetch(`${PLUGINS_API}/api/v1/whatsapp/tool-preferences`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data?.data?.enabled_tools && Object.keys(data.data.enabled_tools).length > 0) {
            setToolStates(prev => ({ ...prev, ...data.data.enabled_tools }));
          }
          setToolsLoaded(true);
        })
        .catch(() => setToolsLoaded(true));
    } else {
      setToolsLoaded(true);
    }
  }, []);

  const handleChange = (id, value) => {
    setFormData(prev => ({ ...prev, [id]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMsg({ text: "", type: "" });
    try {
      const { email, id, ...updates } = formData;
      await apiRequest("/auth/me", {
        method: "PUT",
        body: JSON.stringify(updates),
      });
      setMsg({ text: "Settings saved successfully", type: "success" });
    } catch (err) {
      setMsg({ text: err.message || "Failed to save settings", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const handleToolToggle = useCallback((toolId) => {
    setToolStates(prev => ({ ...prev, [toolId]: !prev[toolId] }));
  }, []);

  const handleToggleAll = useCallback((verticalKey, enable) => {
    setToolStates(prev => {
      const next = { ...prev };
      VERTICAL_TOOLS[verticalKey].tools.forEach(t => { next[t.id] = enable; });
      return next;
    });
  }, []);

  const handleSaveTools = async () => {
    setToolsSaving(true);
    setMsg({ text: "", type: "" });
    try {
      const token = localStorage.getItem("cn_access_token");
      const res = await fetch(`${PLUGINS_API}/api/v1/whatsapp/tool-preferences`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ enabled_tools: toolStates }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to save");
      }

      const data = await res.json();
      setMsg({
        text: `Tool preferences saved! ${data.enabled_count}/${data.total_count} tools active.`,
        type: "success",
      });
    } catch (err) {
      setMsg({ text: err.message || "Failed to save tool preferences", type: "error" });
    } finally {
      setToolsSaving(false);
    }
  };

  const section = baseSections.find((s) => s.label === activeSection);

  // Count total active tools for sidebar badge
  const activeToolCount = Object.values(toolStates).filter(Boolean).length;
  const totalToolCount = Object.values(VERTICAL_TOOLS).reduce((sum, v) => sum + v.tools.length, 0);

  return (
    <div className="p-8 animate-fade-in">
      <div className="mb-8">
        <h1 className="text-xl font-semibold text-neutral-900 tracking-tight">Settings</h1>
        <p className="text-sm text-neutral-500 mt-0.5">Manage your account and preferences</p>
      </div>

      <div className="flex gap-6 max-w-5xl">
        {/* Sidebar nav */}
        <div className="w-48 flex-shrink-0">
          <nav className="space-y-0.5">
            {baseSections.map(({ label, icon: Icon, isToolsSection }) => (
              <button
                key={label}
                onClick={() => {
                  setActiveSection(label);
                  setMsg({ text: "", type: "" });
                }}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-100 ${activeSection === label
                  ? "bg-neutral-900 text-white"
                  : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
                  }`}
              >
                <Icon size={15} strokeWidth={1.75} />
                <span className="flex-1 text-left">{label}</span>
                {isToolsSection && (
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${activeSection === label
                    ? "bg-white/20 text-white"
                    : "bg-neutral-100 text-neutral-500"
                    }`}>
                    {activeToolCount}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {/* Message toast */}
          {msg.text && (
            <div className={`mb-4 px-3 py-2 rounded-lg text-sm flex items-center gap-2 ${msg.type === "success"
              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
              : "bg-red-50 text-red-700 border border-red-200"
              }`}>
              {msg.type === "success" && <Check size={14} />}
              {msg.text}
            </div>
          )}

          {/* Standard Section Card */}
          {!section?.isToolsSection && (
            <div className="cn-card">
              <div className="flex items-center gap-2 mb-6 border-b border-neutral-100 pb-4">
                {section && <section.icon size={18} className="text-neutral-400" strokeWidth={1.75} />}
                <div>
                  <h2 className="text-sm font-semibold text-neutral-900">{section?.label}</h2>
                  <p className="text-xs text-neutral-500">{section?.description}</p>
                </div>
              </div>

              {section?.fields?.length > 0 && (
                <div className="space-y-4 mb-6">
                  <div className="grid grid-cols-2 gap-4">
                    {section.fields.map((f) => (
                      <div key={f.id} className={f.type === "password" ? "col-span-2" : "col-span-1"}>
                        <label className="block text-xs font-medium text-neutral-700 mb-1.5">{f.label}</label>
                        <input
                          type={f.type}
                          placeholder={f.placeholder}
                          className={`cn-input w-full ${f.readOnly ? "bg-neutral-50 cursor-not-allowed text-neutral-500" : ""}`}
                          value={formData[f.id] || ""}
                          onChange={(e) => handleChange(f.id, e.target.value)}
                          readOnly={f.readOnly}
                        />
                      </div>
                    ))}
                  </div>
                  <button onClick={handleSave} disabled={saving} className="btn-primary mt-4">
                    {saving ? <Loader2 size={16} className="animate-spin mr-2" /> : null}
                    Save changes
                  </button>
                </div>
              )}

              {section?.toggles?.length > 0 && (
                <div>
                  {section.toggles.map((t) => (
                    <NotificationToggle key={t.id} {...t} />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* AI Tools Section */}
          {section?.isToolsSection && (
            <div className="cn-card">
              <div className="flex items-center gap-2 mb-6 border-b border-neutral-100 pb-4">
                <Zap size={18} className="text-neutral-400" strokeWidth={1.75} />
                <div>
                  <h2 className="text-sm font-semibold text-neutral-900">AI Tools Moved</h2>
                  <p className="text-xs text-neutral-500">Bot tool configuration now lives inside the Plugins dashboard (5174).</p>
                </div>
              </div>

              <div className="space-y-4">
                <p className="text-sm text-neutral-600">
                  Use the Plugins bot manager to configure tool access for your WhatsApp AI bot. This keeps all bot runtime settings in one place.
                </p>
                <div className="flex items-center justify-between rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3">
                  <div>
                    <p className="text-xs text-neutral-500">Destination</p>
                    <p className="text-sm font-medium text-neutral-800">Plugins Dashboard / Bot Manager</p>
                  </div>
                  <button
                    onClick={() => window.open(`${PLUGINS_FRONTEND}/dashboard`, "_blank")}
                    className="btn-primary !py-2 !px-4 !text-[12px]"
                  >
                    Open 5174
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
