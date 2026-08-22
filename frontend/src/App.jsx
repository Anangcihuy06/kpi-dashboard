import React, { useState, useEffect } from "react";
import { Award, Users, Settings, LogOut, KeyRound, User, ArrowRight, ChevronLeft } from "lucide-react";
import { toast } from "sonner";
import OrgPerformance from "./components/OrgPerformance";
import Subordinates from "./components/Subordinates";
import Configurator from "./components/Configurator";

function getInitials(name = "") {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export default function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [subTargetId, setSubTargetId] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

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
          } else {
            // Session invalid — clear it
            localStorage.removeItem("kpi_user");
            localStorage.removeItem("kpi_token");
          }
        })
        .catch(() => {
          // Fallback: use cached session if backend unreachable
          setUser(parsedUser);
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
      <div className="auth-premium-bold">
        <div className="auth-background-bold">
          <div className="gradient-mesh" />
          <div className="floating-shape shape-1" />
          <div className="floating-shape shape-2" />
          <div className="floating-shape shape-3" />
        </div>
        
        <div className="login-card-premium-bold">
          <div className="logo-container-glow">
            <img
              src="/logo-removebg-preview.png"
              alt="ATI Business Group Logo"
              className="logo-premium"
            />
          </div>
          
          <h2 className="auth-title-bold">KPI Dashboard Portal</h2>
          <p className="auth-subtitle-bold">Enterprise Performance Management System</p>

          <form onSubmit={handleRealLogin}>
            <div className="input-group-bold">
              <label className="input-label-bold" htmlFor="login-username">Corporate ID</label>
              <div className="input-wrapper-bold">
                <input
                  id="login-username"
                  type="text"
                  className="input-premium-bold"
                  value={usernameInput}
                  onChange={handleUsernameChange}
                  placeholder="01.05.13.500"
                  autoComplete="username"
                  required
                />
                <div className="input-icon-glow">
                  <User size={20} />
                </div>
              </div>
            </div>

            <div className="input-group-bold">
              <label className="input-label-bold" htmlFor="login-password">Password</label>
              <div className="input-wrapper-bold">
                <input
                  id="login-password"
                  type="password"
                  className="input-premium-bold"
                  value={passwordInput}
                  onChange={(e) => setPasswordInput(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
                <div className="input-icon-glow">
                  <KeyRound size={20} />
                </div>
              </div>
            </div>

            <button type="submit" className="btn-primary-bold" disabled={loginLoading}>
              {loginLoading ? (
                <span style={{ display: "flex", alignItems: "center", gap: "8px", justifyContent: "center" }}>
                  <span className="spinner" style={{ width: "16px", height: "16px", border: "2px solid rgba(255,255,255,0.3)", borderTop: "2px solid #fff", borderRadius: "50%", animation: "spin 0.8s linear infinite", display: "inline-block" }}></span>
                  Authenticating with HRIS...
                </span>
              ) : (
                <span className="btn-text">
                  Sign In to Portal
                  <ArrowRight size={18} />
                </span>
              )}
            </button>

            <p className="text-xs text-muted" style={{ marginTop: 24, lineHeight: 1.6, textAlign: 'center', opacity: 0.7 }}>
              Performance data is automatically synchronized from Jira, GitLab, and HRIS
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
      {/* Bold Premium Sidebar */}
      <nav className={`sidebar-premium-bold ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar-header-bold">
          <div className="logo-container-glow" style={{ margin: '0 0 16px 0', padding: '12px', width: 'fit-content' }}>
            <img
              src="/logo-removebg-preview.png"
              alt="ATI Logo"
              style={{ width: "40px", height: "40px" }}
            />
          </div>
          {!sidebarCollapsed && (
            <div>
              <h3 className="brand-name-bold">ATI Dashboard</h3>
              <p className="brand-tagline-bold">KPI Tracking System</p>
            </div>
          )}
        </div>

        <div className="menu-container-bold">
          <div className="menu-items-bold">
            <button
              className={`menu-item-bold ${activeTab === "dashboard" ? "active" : ""}`}
              onClick={() => setActiveTab("dashboard")}
              title="Ringkasan performa seluruh tim di bawah kendali Anda"
            >
              <div className="menu-icon-glow">
                <Award size={20} />
              </div>
              {!sidebarCollapsed && <span className="menu-label">Dashboard</span>}
              <div className="menu-indicator" />
              <div className="menu-shine" />
            </button>

            {hasSubordinatesMenu && (
              <button
                className={`menu-item-bold ${activeTab === "subordinates" ? "active" : ""}`}
                onClick={() => { setActiveTab("subordinates"); setSubTargetId(null); }}
                title="Kelola dan evaluasi KPI seluruh anggota tim di bawah kendali Anda"
              >
                <div className="menu-icon-glow">
                  <Users size={20} />
                </div>
                {!sidebarCollapsed && <span className="menu-label">Subordinate</span>}
                <div className="menu-indicator" />
                <div className="menu-shine" />
              </button>
            )}

            {hasConfiguratorMenu && (
              <button
                className={`menu-item-bold ${activeTab === "configurator" ? "active" : ""}`}
                onClick={() => setActiveTab("configurator")}
                title="Atur matriks KPI, formula dinamis, dan integrasi Jira/GitLab"
              >
                <div className="menu-icon-glow">
                  <Settings size={20} />
                </div>
                {!sidebarCollapsed && <span className="menu-label">Matrix Config</span>}
                <div className="menu-indicator" />
                <div className="menu-shine" />
              </button>
            )}
          </div>
        </div>

        {/* Collapse/Expand Toggle Button */}
        <button
          className="sidebar-toggle-btn"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          title={sidebarCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          <ChevronLeft size={20} />
        </button>

        {/* Bold User Profile Section */}
        <div className="sidebar-footer-bold">
          <div className="user-profile-bold">
            <div className="user-avatar-glow">
              <span className="avatar-initials">
                {getInitials(user.fullName)}
              </span>
              <div className="avatar-status-dot" />
            </div>
            {!sidebarCollapsed && (
              <div className="user-info-bold">
                <h4 className="user-name-bold">{user.fullName}</h4>
                <p className="user-role-bold">{user.roles[0]?.replace(/^ROLE_/, "")}</p>
              </div>
            )}
          </div>
          
          <button
            className="logout-btn-bold"
            onClick={handleLogout}
            title="Keluar dari portal KPI"
          >
            <LogOut size={18} />
            {!sidebarCollapsed && <span>Log Out</span>}
            <div className="btn-glow" />
          </button>
        </div>
      </nav>

      {/* Bold Premium Main Content Area */}
      <main className="main-content" style={{ 
        marginLeft: sidebarCollapsed ? '80px' : '320px',
        transition: 'margin-left 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)',
        background: 'radial-gradient(at 80% 0%, rgba(64, 89, 198, 0.08) 0%, transparent 50%), radial-gradient(at 0% 100%, rgba(102, 122, 209, 0.06) 0%, transparent 50%), linear-gradient(180deg, #f8fafc 0%, #e8edfc 100%)',
        backgroundAttachment: 'fixed'
      }}>
        {activeTab === "dashboard" && <OrgPerformance userId={user.id} onOpenMemberDetail={(id) => { setSubTargetId(id); setActiveTab("subordinates"); }} />}
        {activeTab === "subordinates" && <Subordinates supervisorId={user.id} initialMemberId={subTargetId} onResetTarget={() => setSubTargetId(null)} />}
        {activeTab === "configurator" && <Configurator />}
      </main>
    </div>
  );
}
