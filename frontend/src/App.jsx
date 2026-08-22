import React, { useState, useEffect } from "react";
import { Award, Users, Settings, LogOut, KeyRound, Info } from "lucide-react";
import { toast } from "sonner";
import OrgPerformance from "./components/OrgPerformance";
import Subordinates from "./components/Subordinates";
import Configurator from "./components/Configurator";

const AVATAR_GRADIENTS = [
  "linear-gradient(135deg, #5c73d9 0%, #121854 100%)",
  "linear-gradient(135deg, #7c3aed 0%, #2e1065 100%)",
  "linear-gradient(135deg, #0ea5e9 0%, #0c1f5a 100%)",
  "linear-gradient(135deg, #10b981 0%, #064e3b 100%)",
  "linear-gradient(135deg, #f59e0b 0%, #78350f 100%)",
  "linear-gradient(135deg, #ec4899 0%, #500724 100%)",
  "linear-gradient(135deg, #14b8a6 0%, #134e4a 100%)",
  "linear-gradient(135deg, #6366f1 0%, #1e1b4b 100%)",
];

function getInitials(name = "") {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function getAvatarGradient(name = "") {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  }
  return AVATAR_GRADIENTS[hash % AVATAR_GRADIENTS.length];
}

export default function App() {
  const [user, setUser] = useState(null); // Logged in user profile
  const [token, setToken] = useState("");
  const [activeTab, setActiveTab] = useState("dashboard");

  const [notifications, setNotifications] = useState([]);
  const [showNotifs, setShowNotifs] = useState(false);

  useEffect(() => {
    if (user && user.id) {
      fetch(`${import.meta.env.VITE_API_URL}/api/v1/notifications?user_id=${user.id}`)
        .then(res => res.json())
        .then(data => {
          if (data.status === 'success') {
            setNotifications(data.data);
          }
        })
        .catch(console.error);
    }
  }, [user]);

  const markAsRead = async (id) => {
    try {
      await fetch(`${import.meta.env.VITE_API_URL}/api/v1/notifications/${id}/read`, { method: 'PUT' });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (e) { console.error(e); }
  };

  const [subTargetId, setSubTargetId] = useState(null);

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
      localStorage.setItem("hris_token", data.hris_token || ""); // Store HRIS token
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
              <label className="form-label" htmlFor="login-username">Username / NIK</label>
              <input
                id="login-username"
                type="text"
                className="form-input"
                value={usernameInput}
                onChange={handleUsernameChange}
                placeholder="01.05.13.500"
                autoComplete="username"
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: "24px" }}>
              <label className="form-label" htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                className="form-input"
                value={passwordInput}
                onChange={(e) => setPasswordInput(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
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

            <p className="text-xs text-muted" style={{ marginTop: 16, lineHeight: 1.6 }}>
              Data performa Anda disinkronkan otomatis dari Jira, GitLab, dan HRIS setiap beberapa menit.
            </p>
          </form>
        </div>
      </div>
    );
  }

  // Check privileges:
  // - Subordinates menu visible to anyone who is a manager/supervisor or has subordinates
  const hasSubordinatesMenu = user.hasSubordinates || user.roles.includes("ROLE_ADMIN") || user.roles.includes("MANAGER") || user.roles.includes("SUPERVISOR");

  // - Configurator menu visible to MANAGER/SUPERVISOR/ROLE_ADMIN or anyone with subordinates
  const hasConfiguratorMenu = user.roles.includes("ROLE_ADMIN") || user.roles.includes("MANAGER") || user.roles.includes("SUPERVISOR") || user.hasSubordinates;

  return (
    <div className="app-container">
      {/* Sidebar */}
      <nav className="sidebar">
        <div className="brand-logo-container">
          <img
            src="/logo-removebg-preview.png"
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
              role="link"
              tabIndex={0}
              aria-label="Dashboard"
              title="Ringkasan performa seluruh tim di bawah kendali Anda"
            >
              <Award size={18} />
              <span>Dashboard</span>
            </div>
          </li>

          {hasSubordinatesMenu && (
            <li>
              <div
                className={`menu-item ${activeTab === "subordinates" ? "active" : ""}`}
                onClick={() => { setActiveTab("subordinates"); setSubTargetId(null); }}
                role="link"
                tabIndex={0}
                aria-label="Subordinate"
                title="Kelola dan evaluasi KPI seluruh anggota tim di bawah kendali Anda"
              >
                <Users size={18} />
                <span>Subordinate</span>
              </div>
            </li>
          )}

          {hasConfiguratorMenu && (
            <li>
              <div
                className={`menu-item ${activeTab === "configurator" ? "active" : ""}`}
                onClick={() => setActiveTab("configurator")}
                role="link"
                tabIndex={0}
                aria-label="Matrix Config"
                title="Atur matriks KPI, formula dinamis, dan integrasi Jira/GitLab"
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
            <div
              style={{
                position: "relative",
                width: 52,
                height: 52,
                borderRadius: "50%",
                background: getAvatarGradient(user.fullName),
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#ffffff",
                fontWeight: 700,
                fontSize: getInitials(user.fullName).length > 1 ? 15 : 19,
                letterSpacing: "0.5px",
                fontFamily: "var(--font-headings, 'Poppins', sans-serif)",
                flexShrink: 0,
                boxShadow:
                  "0 6px 16px rgba(18, 24, 84, 0.28), inset 0 1px 0 rgba(255,255,255,0.35)",
                border: "2.5px solid rgba(255,255,255,0.9)",
              }}
              title={user.fullName}
            >
              {getInitials(user.fullName)}
              <span
                style={{
                  position: "absolute",
                  bottom: 0,
                  right: 0,
                  width: 13,
                  height: 13,
                  borderRadius: "50%",
                  background: "#10b981",
                  border: "2.5px solid #ffffff",
                  boxShadow: "0 2px 6px rgba(16, 185, 129, 0.55)",
                }}
              />
            </div>
            <div className="user-details" style={{ minWidth: 0 }}>
              <h5 style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{user.fullName}</h5>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 2 }}>
                {user.roles.slice(0, 2).map(r => (
                  <span key={r} className="status-pill live" style={{ fontSize: "9px", padding: "1px 7px", textTransform: "none", letterSpacing: 0 }}>
                    {r.replace(/^ROLE_/, "")}
                  </span>
                ))}
              </div>
              {user.nik && <p className="table-meta" style={{ marginTop: 3 }}>NIK {user.nik}</p>}
            </div>
          </div>

          <button
            className="btn-logout"
            onClick={handleLogout}
            title="Keluar dari portal KPI"
          >
            <LogOut size={14} /> Log Out
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        {activeTab === "dashboard" && <OrgPerformance userId={user.id} onOpenMemberDetail={(id) => { setSubTargetId(id); setActiveTab("subordinates"); }} />}
        {activeTab === "subordinates" && <Subordinates supervisorId={user.id} initialMemberId={subTargetId} onResetTarget={() => setSubTargetId(null)} />}
        {activeTab === "configurator" && <Configurator />}
      </main>
    </div>
  );
}
