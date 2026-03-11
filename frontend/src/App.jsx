import { useState, useCallback } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import AppShell from "./components/AppShell";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import HomePage from "./pages/HomePage";
import DashboardPage from "./pages/DashboardPage";
import CreateCampaignPage from "./pages/CreateCampaignPage";
import CompetitorIntelPage from "./pages/CompetitorIntelPage";
import ContentLibraryPage from "./pages/ContentLibraryPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import AssistantPage from "./pages/AssistantPage";
import SettingsPage from "./pages/SettingsPage";
import CreditsPage from "./pages/CreditsPage";
import ProductIntakePage from "./pages/ProductIntakePage";
import MarketScoutPage from "./pages/MarketScoutPage";
import LandingPage from "./pages/LandingPage";
import { getAccessToken, clearAccessToken } from "./services/auth";

// Auth context via simple prop drilling — no external lib needed
function ProtectedRoute({ isAuthed, children }) {
  if (!isAuthed) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const [isAuthed, setIsAuthed] = useState(() => !!getAccessToken());

  const handleLogin = useCallback(() => {
    setIsAuthed(true);
  }, []);

  const handleLogout = useCallback(() => {
    clearAccessToken();
    setIsAuthed(false);
  }, []);

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
      <Route path="/register" element={<RegisterPage onLogin={handleLogin} />} />

      <Route
        element={
          <ProtectedRoute isAuthed={isAuthed}>
            <AppShell onLogout={handleLogout} />
          </ProtectedRoute>
        }
      >
        <Route path="home" element={<HomePage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="campaigns" element={<CreateCampaignPage />} />
        <Route path="competitor-intel" element={<CompetitorIntelPage />} />
        <Route path="content-library" element={<ContentLibraryPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="assistant" element={<AssistantPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="product-intake" element={<ProductIntakePage />} />
        <Route path="market-scout" element={<MarketScoutPage />} />
        <Route path="credits" element={<CreditsPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
