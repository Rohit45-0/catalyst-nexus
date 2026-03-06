import { useState, useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { clearAccessToken, getCurrentUser } from "../services/auth";
import {
  Home,
  LayoutDashboard,
  Megaphone,
  Users,
  Library,
  BarChart2,
  Bot,
  Settings,
  Plus,
  LogOut,
  Zap,
  Package,
  Globe,
  Coins,
  Wallet,
} from "lucide-react";
import clsx from "clsx";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/campaigns", icon: Megaphone, label: "Campaigns" },
  { to: "/market-scout", icon: Globe, label: "Market Scout" },
  { to: "/whatsapp-bot", icon: Bot, label: "WhatsApp Bot Manager" },
  { to: "/content-library", icon: Library, label: "Content Library" },
];

const bottomItems = [
  { to: "/credits", icon: Wallet, label: "Credits & Billing" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

function SidebarLink({ to, icon: Icon, label, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      title={label}
      className={({ isActive }) =>
        clsx(
          "flex items-center justify-center w-11 h-11 rounded-xl transition-all duration-100 cursor-pointer",
          isActive
            ? "bg-neutral-900 text-white"
            : "text-neutral-400 hover:bg-neutral-100 hover:text-neutral-900"
        )
      }
    >
      <Icon size={22} strokeWidth={1.75} />
    </NavLink>
  );
}

export default function AppShell({ onLogout }) {
  const navigate = useNavigate();
  const [balance, setBalance] = useState(null);

  const logout = () => {
    onLogout?.();
    navigate("/login");
  };

  useEffect(() => {
    getCurrentUser()
      .then((user) => setBalance(user.wallet_balance))
      .catch((err) => {
        // If the token is invalid or the user was deleted, the backend returns 401
        // `api.js` intercepts this and throws "Session expired."
        // We should clear the token and kick them to the login screen.
        console.warn("Auth check failed:", err.message);
        logout();
      });
  }, []);

  return (
    <div className="flex h-screen bg-white overflow-hidden">
      {/* Icon-only Sidebar */}
      <aside className="flex flex-col items-center w-18 border-r border-neutral-200 bg-white py-4 gap-1 flex-shrink-0" style={{ width: '72px' }}>
        {/* Logo / Brand */}
        <div className="flex items-center justify-center w-11 h-11 bg-neutral-900 rounded-xl mb-3 cursor-pointer" onClick={() => navigate("/")}>
          <Zap size={20} className="text-white" strokeWidth={2.5} />
        </div>

        {/* Create Button */}
        <button
          onClick={() => navigate("/campaigns")}
          title="New Campaign"
          className="flex items-center justify-center w-11 h-11 rounded-xl border-2 border-dashed border-neutral-300 text-neutral-400 hover:border-neutral-900 hover:text-neutral-900 transition-all duration-100 mb-3"
        >
          <Plus size={20} strokeWidth={2} />
        </button>

        {/* Nav Items */}
        <nav className="flex flex-col gap-0.5 flex-1">
          {navItems.map((item) => (
            <SidebarLink key={item.to} {...item} />
          ))}
        </nav>

        {/* Bottom Items */}
        <div className="flex flex-col gap-0.5 mt-auto">
          {bottomItems.map((item) => (
            <SidebarLink key={item.to} {...item} />
          ))}
          <button
            onClick={logout}
            title="Logout"
            className="flex items-center justify-center w-11 h-11 rounded-xl text-neutral-400 hover:bg-red-50 hover:text-red-600 transition-all duration-100"
          >
            <LogOut size={22} strokeWidth={1.75} />
          </button>
          {balance !== null && (
            <div
              title={`Balance: $${(balance / 100).toFixed(2)} — click to top up`}
              onClick={() => navigate("/credits")}
              className={`mt-2 mb-2 flex flex-col items-center justify-center w-11 py-1 rounded-xl cursor-pointer shadow-sm border transition-all ${balance < 100
                ? "bg-red-50 text-red-600 border-red-200 hover:bg-red-100"
                : "bg-green-50 text-green-700 border-green-100 hover:bg-green-100"
                }`}
            >
              <Coins size={14} strokeWidth={2.5} className="mb-0.5" />
              <span className="text-[10px] font-bold leading-none">${(balance / 100).toFixed(2)}</span>
            </div>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto bg-white">
        <Outlet />
      </main>
    </div>
  );
}
