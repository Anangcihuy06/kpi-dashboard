import React, { useState, useEffect } from "react";
import { Award, Users, Settings, LogOut, KeyRound, Info } from "lucide-react";
import { toast } from "sonner";
import Dashboard from "./components/Dashboard";
import Subordinates from "./components/Subordinates";
import Configurator from "./components/Configurator";

export default function App() {
  const [user, setUser] = useState(null); // Logged in user profile
  const [token, setToken] = useState("");
  const [activeTab, setActiveTab] = useState("dashboard");

  // Load session from localStorage on mount — verify locally (no HRIS call needed)
  useEffect(() => {
    const storedUser = localStorage.getItem("kpi_user");
    const storedToken = localStorage.getItem("kpi_token");
    if (storedUser && storedToken) {
      const parsedUser = JSON.parse(storedUser);
      // Quick local verify — instant, no HRIS round-trip
      fetch(`${import.meta.env.VITE_API_URL}/api/v1/auth/verify?user_id=${parsedUser.id}`)
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.status === "valid") {
            setUser(data.user);
            setToken(storedToken);
          } else {
            // Session invalid — clear it
            localStorage.removeItem("kpi_user");
            localStorage.removeItem("kpi_token");
          }
        })
        .catch(() => {
          // Fallback: use cached session if backend unreachable
          setUser(parsedUser);
          setToken(storedToken);
        });
    }
  }, []);

  // Real login form inputs
  const [usernameInput, setUsernameInput] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);

  const handleRealLogin = async (e) => {
    e.preventDefault();
    setLoginLoading(true);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s max

    try {
      const response = await fetch(import.meta.env.VITE_API_URL + "/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: usernameInput,
          password: passwordInput
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Autentikasi gagal");
      }

      const data = await response.json();
      setUser(data.user);
      setToken(data.token);
      localStorage.setItem("kpi_user", JSON.stringify(data.user));
      localStorage.setItem("kpi_token", data.token);
      setActiveTab("dashboard");
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === "AbortError") {
        toast.error("Server HRIS tidak merespons (timeout). Coba lagi.");
      } else {
        toast.error(err.message);
      }
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    setUser(null);
    setToken("");
    setUsernameInput("");
    setPasswordInput("");
    localStorage.removeItem("kpi_user");
    localStorage.removeItem("kpi_token");
  };

  const handleUsernameChange = (e) => {
    let val = e.target.value;
    // Only format if string only contains digits and dots
    if (/^[\d.]*$/.test(val)) {
      let raw = val.replace(/\./g, '');
      let formatted = '';
      if (raw.length > 0) formatted += raw.substring(0, 2);
      if (raw.length > 2) formatted += '.' + raw.substring(2, 4);
      if (raw.length > 4) formatted += '.' + raw.substring(4, 6);
      if (raw.length > 6) formatted += '.' + raw.substring(6);
      setUsernameInput(formatted);
    } else {
      setUsernameInput(val);
    }
  };

  if (!user) {
    return (
      <div className="auth-page">
        <div className="login-card">
          <img
            src="/logo-removebg-preview.png"
            alt="ATI Business Group Logo"
            className="login-header-logo"
          />
          <h2 className="form-title">KPI Dashboard Portal</h2>
          <p className="form-subtitle">Autentikasi menggunakan akun ATI Business Group Anda</p>

          <form onSubmit={handleRealLogin}>
            <div className="form-group">
              <label className="form-label">Username / NIK</label>
              <input
                type="text"
                className="form-input"
                value={usernameInput}
                onChange={handleUsernameChange}
                placeholder="01.05.13.500"
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: "32px" }}>
              <label className="form-label">Password</label>
              <input
                type="password"
                className="form-input"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loginLoading}>
              {loginLoading ? (
                <span style={{ display: "flex", alignItems: "center", gap: "8px", justifyContent: "center" }}>
                  <span className="spinner" style={{ width: "14px", height: "14px", border: "2px solid #fff3", borderTop: "2px solid #fff", borderRadius: "50%", animation: "spin 0.8s linear infinite", display: "inline-block" }}></span>
                  Menghubungi HRIS Server... (bisa 10-20 detik)
                </span>
              ) : "Sign In ke Portal"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Check privileges:
  // - Subordinates menu visible to anyone who is a manager/supervisor or has subordinates
  const hasSubordinatesMenu = user.hasSubordinates || user.roles.includes("ROLE_ADMIN") || user.roles.includes("MANAGER") || user.roles.includes("SUPERVISOR");

  // - Configurator menu visible to MANAGER or ROLE_ADMIN
  const hasConfiguratorMenu = user.roles.includes("ROLE_ADMIN") || user.roles.includes("MANAGER");

  return (
    <div className="app-container">
      {/* Sidebar */}
      <nav className="sidebar">
        <div className="brand-logo-container">
          <img
            src="https://atibusinessgroup.com/wp-content/uploads/2025/09/cropped-logo-ati-new-1-1-1-180x180.png"
            alt="ATI Logo"
            style={{ width: "32px", height: "32px" }}
          />
          <div>
            <span className="brand-name">ATI Dashboard</span>
            <div style={{ fontSize: "9px", color: "var(--color-tint)" }}>KPI Tracking System</div>
          </div>
        </div>

        <ul className="menu-list">
          <li>
            <div
              className={`menu-item ${activeTab === "dashboard" ? "active" : ""}`}
              onClick={() => setActiveTab("dashboard")}
            >
              <Award size={18} />
              <span>My Performance</span>
            </div>
          </li>

          {hasSubordinatesMenu && (
            <li>
              <div
                className={`menu-item ${activeTab === "subordinates" ? "active" : ""}`}
                onClick={() => setActiveTab("subordinates")}
              >
                <Users size={18} />
                <span>Hierarki Tim (Sub)</span>
              </div>
            </li>
          )}

          {hasConfiguratorMenu && (
            <li>
              <div
                className={`menu-item ${activeTab === "configurator" ? "active" : ""}`}
                onClick={() => setActiveTab("configurator")}
              >
                <Settings size={18} />
                <span>Matrix Config</span>
              </div>
            </li>
          )}
        </ul>

        {/* User Profile Summary at bottom of sidebar */}
        <div className="sidebar-footer">
          <div className="user-profile-header">
            <div className="user-avatar">
              {user.fullName.charAt(0)}
            </div>
            <div className="user-details">
              <h5>{user.fullName}</h5>
              <p>Role: {user.roles.join(", ")}</p>
            </div>
          </div>

          <button
            className="btn-logout"
            onClick={handleLogout}
          >
            <LogOut size={14} /> Log Out
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === "dashboard" && <Dashboard userId={user.id} isSelf={true} />}
        {activeTab === "subordinates" && <Subordinates supervisorId={user.id} />}
        {activeTab === "configurator" && <Configurator />}
      </main>
    </div>
  );
}
