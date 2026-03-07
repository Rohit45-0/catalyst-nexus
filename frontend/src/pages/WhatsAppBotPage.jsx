import { useState, useEffect } from "react";
import axios from "axios";
import { getCurrentUser } from "../services/auth";
import { Copy, Check, Clock, Calendar, CheckSquare, BarChart, TrendingUp, Sparkles, Store, Scissors, UtensilsCrossed, ShoppingCart, GraduationCap, Globe, BookOpen, RefreshCw, FileText, Zap } from "lucide-react";

const PLUGINS_API = import.meta.env.VITE_PLUGINS_API_URL || "https://web-production-ba9e.up.railway.app";

export default function WhatsAppBotPage() {
    const [botConfig, setBotConfig] = useState(null);
    const [slots, setSlots] = useState({
        slot_duration_minutes: 15,
        max_capacity_per_slot: 1,
        working_hours: {
            monday: [{ start: "09:00", end: "17:00" }],
            tuesday: [{ start: "09:00", end: "17:00" }],
            wednesday: [{ start: "09:00", end: "17:00" }],
            thursday: [{ start: "09:00", end: "17:00" }],
            friday: [{ start: "09:00", end: "17:00" }],
            saturday: [],
            sunday: []
        }
    });

    const [analytics, setAnalytics] = useState(null);
    const [hasCopied, setHasCopied] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const [loading, setLoading] = useState(true);
    const [user, setUser] = useState(null);

    const loadBotConfig = async (currentUser) => {
        try {
            const res = await axios.get(`${PLUGINS_API}/api/v1/whatsapp/bot-config`, {
                headers: { 'user-id': currentUser.id }
            });
            if (res.data.data) {
                setBotConfig(res.data.data);
                loadSlotsConfig(res.data.data.id);
                loadAnalytics(res.data.data.id, currentUser.id);
            }
        } catch (err) {
            console.error("Failed to load bot config", err);
        } finally {
            setLoading(false);
        }
    };

    const loadAnalytics = async (botId, userId) => {
        try {
            const res = await axios.get(`${PLUGINS_API}/api/v1/dashboard/analytics?bot_config_id=${botId}&user_id=${userId}`);
            if (res.data.data) {
                setAnalytics(res.data.data);
            }
        } catch (err) {
            console.error("Failed to load analytics", err);
        }
    };

    const loadSlotsConfig = async (botId) => {
        try {
            const res = await axios.get(`${PLUGINS_API}/api/v1/slots/config/${botId}`);
            if (res.data.data) {
                setSlots(res.data.data);
            }
        } catch (err) {
            console.error("Failed to load slots", err);
        }
    };

    const createBot = async () => {
        try {
            setLoading(true);
            const res = await axios.post(`${PLUGINS_API}/api/v1/whatsapp/bot-config`, {
                user_id: user.id,
                phone_number_id: "1025937603933608", // Meta Test Number ID for now
                owner_phone_number: "",
                business_display_name: "My Business",
                use_case_type: "restaurant"
            });
            setBotConfig(res.data.data);
            loadSlotsConfig(res.data.data.id);
        } catch (err) {
            console.error(err);
            alert("Failed to create bot.");
        } finally {
            setLoading(false);
        }
    };

    const saveSlotConfig = async () => {
        try {
            await axios.post(`${PLUGINS_API}/api/v1/slots/config`, {
                user_id: user.id,
                bot_config_id: botConfig.id,
                ...slots
            });
            alert("Working hours saved!");
        } catch (err) {
            console.error(err);
            alert("Failed to save rules.");
        }
    };

    const syncKnowledgeBase = async () => {
        try {
            setSyncing(true);
            const res = await axios.post(`${PLUGINS_API}/api/v1/knowledge/sync/${botConfig.id}`);
            alert(res.data.message || "Sync successful!");
        } catch (err) {
            console.error(err);
            alert("Failed to sync knowledge base. Make sure your Google account is connected.");
        } finally {
            setSyncing(false);
        }
    };

    const useCaseOptions = [
        { key: "restaurant", label: "Restaurant / Mess", icon: UtensilsCrossed, color: "text-orange-400", border: "border-orange-500/30", bg: "bg-orange-500/10" },
        { key: "salon", label: "Salon / Parlour", icon: Scissors, color: "text-pink-400", border: "border-pink-500/30", bg: "bg-pink-500/10" },
        { key: "tiffin", label: "Tiffin / Meals", icon: Store, color: "text-green-400", border: "border-green-500/30", bg: "bg-green-500/10" },
        { key: "kirana", label: "Kirana / Grocery", icon: ShoppingCart, color: "text-blue-400", border: "border-blue-500/30", bg: "bg-blue-500/10" },
        { key: "coaching", label: "Coaching / Tuition", icon: GraduationCap, color: "text-yellow-400", border: "border-yellow-500/30", bg: "bg-yellow-500/10" },
        { key: "general", label: "General Business", icon: Globe, color: "text-neutral-400", border: "border-neutral-500/30", bg: "bg-neutral-500/10" },
    ];

    const updateUseCase = async (newUseCase) => {
        // Optimistic UI Update: change it visually instantly!
        const previousUseCase = botConfig.use_case_type;
        setBotConfig({ ...botConfig, use_case_type: newUseCase });

        try {
            await axios.post(`${PLUGINS_API}/api/v1/whatsapp/bot-config`, {
                user_id: user.id,
                phone_number_id: botConfig.phone_number_id,
                owner_phone_number: botConfig.owner_phone_number || "",
                business_display_name: botConfig.business_display_name || "My Business",
                use_case_type: newUseCase,
                is_active: true,
            });
        } catch (err) {
            console.error(err);
            // Revert on failure
            setBotConfig({ ...botConfig, use_case_type: previousUseCase });
            alert("Failed to update business type.");
        }
    };

    useEffect(() => {
        getCurrentUser().then(res => {
            setUser(res);
            loadBotConfig(res);
        }).catch(err => {
            console.error(err);
            setLoading(false);
        });
    }, []);

    if (loading) return <div className="p-8 text-neutral-400">Loading...</div>;

    return (
        <div className="flex-1 overflow-auto bg-black p-8">
            <div className="max-w-5xl mx-auto space-y-8">

                {/* Header */}
                <div>
                    <h1 className="text-3xl font-light text-white mb-2">WhatsApp Bot Manager</h1>
                    <p className="text-neutral-400">Configure your AI assistant, connect your calendar, and manage slots.</p>
                </div>

                {!botConfig ? (
                    <div className="bg-neutral-900/50 border border-neutral-800 rounded-2xl p-8 text-center">
                        <h2 className="text-xl font-medium text-white mb-4">You don't have a bot yet</h2>
                        <p className="text-neutral-400 mb-6">Create your dedicated WhatsApp AI to start automating bookings and customer service.</p>
                        <button
                            onClick={createBot}
                            className="px-6 py-3 bg-white text-black rounded-lg font-medium hover:bg-neutral-200 transition-colors"
                        >
                            Initialize My WhatsApp Bot
                        </button>
                    </div>
                ) : (
                    <div className="space-y-6">

                        {/* Top Analytics Banner */}
                        {analytics && (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
                                    <h3 className="text-neutral-400 text-sm font-medium mb-2 flex items-center gap-2">
                                        <TrendingUp size={16} className="text-blue-400" />
                                        Total Footfalls / Users
                                    </h3>
                                    <p className="text-3xl font-light text-white">{analytics.total_conversations}</p>
                                    <p className="text-xs text-neutral-500 mt-2">Active WhatsApp Chats</p>
                                </div>
                                <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
                                    <h3 className="text-neutral-400 text-sm font-medium mb-2 flex items-center gap-2">
                                        <BarChart size={16} className="text-orange-400" />
                                        Peak Hours
                                    </h3>
                                    <div className="space-y-1 mt-2">
                                        {analytics.peak_hours.map((hourStr, i) => (
                                            <p key={i} className="text-lg font-light text-white flex justify-between">
                                                <span>{hourStr.split(' ')[0]} {hourStr.split(' ')[1]}</span>
                                                <span className="text-sm text-neutral-500">{hourStr.split('(')[1].replace(')', '')}</span>
                                            </p>
                                        ))}
                                    </div>
                                </div>
                                <div className="bg-neutral-900/40 border border-[#8b5cf6]/30 rounded-2xl p-6 relative overflow-hidden group">
                                    <div className="absolute inset-0 bg-gradient-to-br from-[#8b5cf6]/10 to-transparent pointer-events-none" />
                                    <h3 className="text-[#a78bfa] text-sm font-medium mb-3 flex items-center gap-2 relative z-10">
                                        <Sparkles size={16} />
                                        AI Profile Insights
                                    </h3>
                                    <p className="text-sm font-light text-neutral-300 leading-relaxed max-h-24 overflow-y-auto relative z-10">
                                        {analytics.ai_summary}
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Business Type Selector */}
                        <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
                            <h2 className="text-lg font-medium text-white mb-1 flex items-center gap-2">
                                <Store size={18} className="text-purple-400" />
                                Business Type
                            </h2>
                            <p className="text-sm text-neutral-400 mb-4">Select your business type. This changes the AI's personality and how it talks to your customers.</p>
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                                {useCaseOptions.map(opt => {
                                    const Icon = opt.icon;
                                    const isActive = botConfig.use_case_type === opt.key;
                                    return (
                                        <button
                                            key={opt.key}
                                            onClick={() => updateUseCase(opt.key)}
                                            className={`flex flex-col items-center gap-2 p-4 rounded-xl border transition-all duration-200 ${isActive
                                                ? `${opt.bg} ${opt.border} ring-1 ring-white/10`
                                                : "bg-black border-neutral-800 hover:border-neutral-600 hover:bg-neutral-900"
                                                }`}
                                        >
                                            <Icon size={22} className={isActive ? opt.color : "text-neutral-500"} />
                                            <span className={`text-xs font-medium text-center leading-tight ${isActive ? "text-white" : "text-neutral-500"}`}>
                                                {opt.label}
                                            </span>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

                            {/* Left Column: Calendar & Integrations */}
                            <div className="space-y-6">

                                {/* Google Calendar Card */}
                                <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
                                    <div className="flex justify-between items-start mb-6">
                                        <div>
                                            <h2 className="text-lg font-medium text-white mb-1 flex items-center gap-2">
                                                <Calendar size={18} className="text-blue-400" />
                                                Integrations (Calendar & Docs)
                                            </h2>
                                            <p className="text-sm text-neutral-400">Connect Google to manage bookings and your bot's training doc.</p>
                                        </div>
                                    </div>

                                    {botConfig.has_calendar ? (
                                        <div className="flex items-center gap-3 text-sm text-green-400 bg-green-500/10 border border-green-500/20 p-4 rounded-xl mb-4">
                                            <CheckSquare size={18} />
                                            Google Account Connected
                                        </div>
                                    ) : (
                                        <button
                                            onClick={() => window.open(`${PLUGINS_API}/api/v1/calendar/connect/${botConfig.id}`, '_blank')}
                                            className="w-full flex justify-center items-center gap-2 px-4 py-3 bg-neutral-800 hover:bg-neutral-700 text-white rounded-xl transition-colors border border-neutral-700 mb-4"
                                        >
                                            <img src="https://www.google.com/favicon.ico" className="w-4 h-4" alt="Google" />
                                            Connect Google Account
                                        </button>
                                    )}

                                    {/* Knowledge Base Section */}
                                    <div className="pt-6 border-t border-neutral-800">
                                        <div className="flex items-center gap-2 mb-4">
                                            <BookOpen size={18} className="text-purple-400" />
                                            <span className="text-sm font-medium text-white">AI Knowledge Base</span>
                                        </div>

                                        {botConfig.google_doc_id ? (
                                            <div className="grid grid-cols-2 gap-3">
                                                <button
                                                    onClick={() => window.open(`https://docs.google.com/document/d/${botConfig.google_doc_id}/edit`, '_blank')}
                                                    className="flex justify-center items-center gap-2 px-3 py-2.5 bg-neutral-800 hover:bg-neutral-700 text-xs text-neutral-300 rounded-lg transition-colors border border-neutral-700"
                                                >
                                                    <FileText size={14} />
                                                    Edit Doc
                                                </button>
                                                <button
                                                    onClick={syncKnowledgeBase}
                                                    disabled={syncing}
                                                    className={`flex justify-center items-center gap-2 px-3 py-2.5 rounded-lg text-xs transition-all ${syncing ? "bg-purple-500/20 text-purple-300 cursor-not-allowed" : "bg-purple-600 hover:bg-purple-500 text-white"
                                                        }`}
                                                >
                                                    <RefreshCw size={14} className={syncing ? "animate-spin" : ""} />
                                                    {syncing ? "Syncing..." : "Sync Brain"}
                                                </button>
                                            </div>
                                        ) : (
                                            <p className="text-xs text-neutral-500 italic">Connect Google to generate your training document.</p>
                                        )}
                                    </div>
                                </div>

                                {/* WhatsApp Official Connection */}
                                <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
                                    <div className="flex justify-between items-center mb-4">
                                        <h2 className="text-lg font-medium text-white flex items-center gap-2">
                                            <Zap size={18} className="text-green-400" />
                                            WhatsApp Connection
                                        </h2>
                                        <span className="px-2 py-0.5 bg-green-500/10 text-green-500 text-[10px] rounded border border-green-500/20 uppercase font-bold tracking-wider">Active</span>
                                    </div>
                                    <p className="text-sm text-neutral-400 mb-6">Your official number is connected via Meta Cloud API.</p>

                                    <div className="p-4 bg-black rounded-xl border border-neutral-800 space-y-3">
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-neutral-500">Phone Number ID</span>
                                            <span className="text-neutral-300 font-mono">{botConfig.phone_number_id}</span>
                                        </div>
                                        <div className="flex justify-between items-center text-xs">
                                            <span className="text-neutral-500">Status</span>
                                            <span className="text-green-400 flex items-center gap-1">
                                                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                                                Live & Accepting Messages
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                {/* Bot Testing Info */}
                                <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6">
                                    <h2 className="text-lg font-medium text-white mb-4">Test Your Bot</h2>
                                    <div className="space-y-4">
                                        <div>
                                            <label className="text-xs text-neutral-500 uppercase tracking-wider font-semibold mb-2 block">WhatsApp Sandbox Number</label>
                                            <div className="flex bg-black border border-neutral-800 rounded-lg p-3 justify-between items-center group">
                                                <code className="text-neutral-300 font-mono text-sm">+1 555 087 1974</code>
                                                <button
                                                    onClick={() => {
                                                        navigator.clipboard.writeText("+15550871974");
                                                        setHasCopied(true);
                                                        setTimeout(() => setHasCopied(false), 2000);
                                                    }}
                                                    className="text-neutral-500 hover:text-white transition-colors"
                                                >
                                                    {hasCopied ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
                                                </button>
                                            </div>
                                        </div>
                                        <p className="text-sm text-neutral-400">
                                            Message this number from your personal phone to text your AI.
                                        </p>
                                    </div>
                                </div>

                            </div>

                            {/* Right Column: Slot Configurations */}
                            <div className="bg-neutral-900 border border-neutral-800 rounded-2xl p-6 flex flex-col">
                                <h2 className="text-lg font-medium text-white mb-1 flex items-center gap-2">
                                    <Clock size={18} className="text-orange-400" />
                                    Slot Engine Rules
                                </h2>
                                <p className="text-sm text-neutral-400 mb-6">Define your mathematical working hours. AI will cross-reference this with your Google Calendar.</p>

                                <div className="space-y-4 flex-1">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs text-neutral-500 uppercase font-semibold mb-1 block">Slot Duration (Mins)</label>
                                            <input
                                                type="number"
                                                value={slots.slot_duration_minutes}
                                                onChange={(e) => setSlots({ ...slots, slot_duration_minutes: parseInt(e.target.value) })}
                                                className="w-full bg-black border border-neutral-800 rounded-lg p-3 text-white focus:border-neutral-500 outline-none"
                                            />
                                        </div>
                                        <div>
                                            <label className="text-xs text-neutral-500 uppercase font-semibold mb-1 block">Max Capacity</label>
                                            <input
                                                type="number"
                                                value={slots.max_capacity_per_slot}
                                                onChange={(e) => setSlots({ ...slots, max_capacity_per_slot: parseInt(e.target.value) })}
                                                className="w-full bg-black border border-neutral-800 rounded-lg p-3 text-white focus:border-neutral-500 outline-none"
                                            />
                                        </div>
                                    </div>

                                    <div className="pt-4 border-t border-neutral-800">
                                        <label className="text-xs text-neutral-500 uppercase font-semibold mb-3 block">Weekly Schedule</label>

                                        {Object.keys(slots.working_hours).map(day => (
                                            <div key={day} className="flex items-center justify-between mb-2">
                                                <span className="text-sm text-neutral-300 capitalize w-24">{day}</span>
                                                {slots.working_hours[day].length > 0 ? (
                                                    <span className="text-sm font-mono text-neutral-400">
                                                        {slots.working_hours[day].map(b => `${b.start}-${b.end}`).join(", ")}
                                                    </span>
                                                ) : (
                                                    <span className="text-sm text-neutral-600 italic">Closed</span>
                                                )}
                                            </div>
                                        ))}
                                        <p className="mt-4 text-xs text-neutral-500">Note: Advanced UI editor for multiple blocks (e.g., Lunch breaks) coming soon.</p>
                                    </div>
                                </div>

                                <div className="pt-6 border-t border-neutral-800 mt-auto">
                                    <button
                                        onClick={saveSlotConfig}
                                        className="w-full px-4 py-3 bg-white text-black font-medium rounded-xl hover:bg-neutral-200 transition-colors"
                                    >
                                        Save Configuration
                                    </button>
                                </div>

                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
