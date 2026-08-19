import React, { useState, useEffect } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, Cell
} from "recharts";
import {
  Award, Users, TrendingUp, Clock, UserCheck, RefreshCw,
  ChevronDown, ChevronRight, ArrowLeft, AlertTriangle, Crown
} from "lucide-react";
import Dashboard from "./Dashboard";

const SCORE_GRADIENT = ["#12ccab", "#4f8cff", "#8b5cf6", "#f59e0b", "#ef4444"];

const fmt = (n, digits = 0) =>
  Number(n || 0).toLocaleString("id-ID", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

const AVATAR_COLORS = ["#4f8cff", "#12ccab", "#8b5cf6", "#f59e0b", "#ef4444", "#0ea5e9", "#14b8a6", "#6366f1"];

const avatarColor = (name) => {
  let h = 0;
  const s = name || "";
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return AVATAR_COLORS[h % AVATAR_COLORS.length];
};

const initialsOf = (name, nik) => {
  const src = (name || "").trim();
  if (!src) return (nik || "").slice(0, 2).toUpperCase() || "?";
  const parts = src.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
};

function buildOrgTree(members) {
  const byId = {};
  members.forEach(m => { byId[m.user_id] = { ...m, children: [] }; });
  const roots = [];
  members.forEach(m => {
    const parent = byId[m.supervisor_id];
    if (parent && parent.user_id !== m.user_id) {
      parent.children.push(byId[m.user_id]);
    } else {
      roots.push(byId[m.user_id]);
    }
  });
  return roots;
}

function flattenTree(nodes, depth = 1) {
  const out = [];
  nodes.forEach(n => {
    out.push({ node: n, depth });
    out.push(...flattenTree(n.children, depth + 1));
  });
  return out;
}

export default function OrgPerformance({ userId, onOpenMemberDetail }) {
  const [members, setMembers] = useState([]);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncStatus, setSyncStatus] = useState({ last_sync_time: null, is_syncing: false });
  const [expanded, setExpanded] = useState({});
  const [detailMember, setDetailMember] = useState(null);

  const rootId = String(userId || "");

  useEffect(() => {
    fetchSyncStatus();
    const syncInterval = setInterval(fetchSyncStatus, 30000);
    return () => clearInterval(syncInterval);
  }, []);

  useEffect(() => {
    if (rootId) fetchPerformance();
  }, [rootId, selectedYear]);

  const fetchSyncStatus = async () => {
    try {
      const response = await fetch(import.meta.env.VITE_API_URL + "/api/v1/sync/status");
      const status = await response.json();
      setSyncStatus(status);
    } catch (err) {
      console.error("Gagal mengambil status sync:", err);
    }
  };

  const fetchPerformance = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/kpi/team-yearly?user_id=${rootId}&year=${selectedYear}`,
        { cache: "no-store" }
      );
      if (!response.ok) throw new Error("Gagal mengambil data tim");
      const result = await response.json();
      if (result.status === "success") {
        setMembers(result.data || []);
      } else {
        setMembers([]);
      }
    } catch (err) {
      setError(err.message);
      setMembers([]);
    } finally {
      setLoading(false);
    }
  };

  const formatLastSyncTime = () => {
    if (!syncStatus.last_sync_time) return "Belum pernah disinkronisasi";
    const syncTime = new Date(syncStatus.last_sync_time);
    const now = new Date();
    const diffMins = Math.floor((now - syncTime) / 60000);
    if (diffMins < 1) return "Baru saja";
    if (diffMins < 60) return `${diffMins} menit yang lalu`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} jam yang lalu`;
    return `${Math.floor(diffHours / 24)} hari yang lalu`;
  };

  const syncPillClass = syncStatus.is_syncing ? "syncing" : "live";
  const syncPillLabel = syncStatus.is_syncing ? "Sinkronisasi berjalan" : "Data terbaru";

  const renderHeader = () => (
    <div className="header-ui">
      <div>
        <span className="hero-eyebrow">Organizational Performance</span>
        <h2>Dashboard Tim</h2>
        <p style={{ color: "var(--color-text-muted)", fontSize: "14px", margin: 0 }}>
          {members.length > 0
            ? `${members.length} anggota tim (mencakup seluruh bawahan hingga level terbawah)`
            : "Ringkasan performa seluruh bawahan Anda"}
        </p>
        <div className="status-strip">
          <span className={`status-pill ${syncPillClass}`}>
            <RefreshCw size={11} className={syncStatus.is_syncing ? "animate-spin" : ""} />
            {syncPillLabel}
          </span>
          <span>Terakhir diperbarui: <strong>{formatLastSyncTime()}</strong></span>
        </div>
      </div>
      <div className="filter-group" style={{ display: "flex", justifyContent: "flex-end", alignItems: "flex-end" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label className="form-label" style={{ fontWeight: 600, fontSize: "11px", color: "var(--color-text-muted)" }}>
            Periode Evaluasi
          </label>
          <select
            className="select-control"
            value={selectedYear}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            aria-label="Pilih tahun evaluasi"
          >
            {[2025, 2026, 2027].map(y => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );

  if (detailMember) {
    return (
      <div>
        <button
          className="btn-outline"
          onClick={() => setDetailMember(null)}
          style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}
        >
          <ArrowLeft size={16} /> Kembali ke Dashboard Tim
        </button>
        <Dashboard userId={detailMember} isSelf={false} />
      </div>
    );
  }

  if (loading) {
    return (
      <div>
        {renderHeader()}
        <div className="stats-grid">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="stat-card" style={{ minHeight: 108 }}>
              <div className="skeleton-block" style={{ width: 56, height: 56, borderRadius: "50%", flexShrink: 0 }} />
              <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
                <div className="skeleton-block" style={{ width: "60%", height: 26 }} />
                <div className="skeleton-block" style={{ width: "40%", height: 12 }} />
              </div>
            </div>
          ))}
        </div>
        <div className="card" style={{ height: 320 }}>
          <div className="skeleton-block" style={{ width: "45%", height: 22, marginBottom: 20 }} />
          <div className="skeleton-block" style={{ width: "100%", height: 220 }} />
        </div>
        <div className="text-muted text-sm" style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8 }}>
          <RefreshCw className="animate-spin" size={14} /> Memuat performa tim...
        </div>
      </div>
    );
  }

  if (error || members.length === 0) {
    return (
      <div>
        {renderHeader()}
        <div className="empty-state" style={{ marginTop: 20, background: "#fff", borderRadius: "var(--radius-lg)", border: "1px solid #fecaca", boxShadow: "var(--shadow-md)" }}>
          <div className="empty-icon" style={{ background: "#fee2e2", color: "#b91c1c" }}>
            <Award size={24} />
          </div>
          <h4>Belum Ada Data Tim</h4>
          <p>
            {error || "Anggota tim belum tersedia untuk periode terpilih. Data akan muncul otomatis setelah disinkronkan dari HRIS."}
          </p>
          <button className="btn-primary" onClick={fetchPerformance} style={{ marginTop: 8 }}>
            <RefreshCw size={16} /> Muat Ulang
          </button>
        </div>
      </div>
    );
  }

  const directCount = members.filter(m => String(m.supervisor_id) === rootId).length;
  const indirectCount = members.length - directCount;

  const avg = (key) => {
    const vals = members.map(m => Number(m.kpi_scores?.[key]) || 0);
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
  };
  const avgOverall = avg("overall");
  const topPerformer = [...members].sort((a, b) =>
    (Number(b.kpi_scores?.overall) || 0) - (Number(a.kpi_scores?.overall) || 0)
  )[0];

  const totalAtt = members.reduce((s, m) => s + (m.summary?.total_attendance_days || 0), 0);
  const totalLate = members.reduce((s, m) => s + (m.summary?.total_late_count || 0), 0);
  const attPct = totalAtt > 0 ? ((totalAtt - totalLate) / totalAtt) * 100 : 100;

  const monthly = {};
  members.forEach(m => {
    (m.daily_breakdown || []).forEach(day => {
      if (!day.date || day.overall_score == null) return;
      const key = day.date.substring(0, 7);
      if (!monthly[key]) monthly[key] = { sum: 0, n: 0 };
      monthly[key].sum += day.overall_score;
      monthly[key].n += 1;
    });
  });
  const trendData = Object.keys(monthly)
    .sort()
    .map(k => ({
      name: new Date(k + "-01").toLocaleString("default", { month: "short" }),
      Score: parseFloat((monthly[k].sum / monthly[k].n).toFixed(2))
    }));

  const catData = [
    { name: "Delivery", value: parseFloat(avg("delivery").toFixed(1)) },
    { name: "Engineering", value: parseFloat(avg("engineering").toFixed(1)) },
    { name: "Effort", value: parseFloat(avg("effort").toFixed(1)) },
    { name: "Quality", value: parseFloat(avg("quality").toFixed(1)) },
  ];

  const leaderboard = [...members]
    .sort((a, b) => (Number(b.kpi_scores?.overall) || 0) - (Number(a.kpi_scores?.overall) || 0))
    .slice(0, 8)
    .map(m => ({
      name: (m.full_name || "").split(" ").slice(0, 2).join(" ") || m.nik,
      Score: Number(m.kpi_scores?.overall) || 0,
    }));

  const tree = buildOrgTree(members);
  const flat = flattenTree(tree);

  const toggleNode = (id) => setExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  const isNodeExpanded = (id) => !!expanded[id];

  return (
    <div>
      {renderHeader()}

      {/* Stat cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "rgba(255,255,255,0.9)", borderRadius: "16px", width: 56, height: 56, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-primary)" }}>
            <Users size={24} />
          </div>
          <div className="stat-info">
            <h4>Total Tim</h4>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span className="metric-value">{fmt(members.length)}</span>
              {indirectCount > 0 && <span className="table-meta">{fmt(directCount)} direct · {fmt(indirectCount)} indirect</span>}
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: "rgba(255,255,255,0.9)", borderRadius: "16px", width: 56, height: 56, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--color-secondary)" }}>
            <TrendingUp size={24} />
          </div>
          <div className="stat-info">
            <h4>Rata-rata Score</h4>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span className="metric-value">{fmt(avgOverall, 1)}</span>
              <span className="table-meta">dari 5 pilar</span>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: "rgba(255,255,255,0.9)", borderRadius: "16px", width: 56, height: 56, display: "flex", alignItems: "center", justifyContent: "center", color: "#8b5cf6" }}>
            <Crown size={24} />
          </div>
          <div className="stat-info">
            <h4>Top Performer</h4>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span className="metric-value">{topPerformer ? (topPerformer.full_name || "—").split(" ").slice(0, 2).join(" ") : "—"}</span>
              <span className="table-meta">{topPerformer ? fmt(topPerformer.kpi_scores?.overall, 1) : ""}</span>
            </div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: "rgba(255,255,255,0.9)", borderRadius: "16px", width: 56, height: 56, display: "flex", alignItems: "center", justifyContent: "center", color: "#12ccab" }}>
            <UserCheck size={24} />
          </div>
          <div className="stat-info">
            <h4>Kehadiran Tim</h4>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span className="metric-value">{fmt(attPct, 1)}%</span>
              <span className="table-meta">{fmt(totalLate)}x late</span>
            </div>
          </div>
        </div>
      </div>

      {/* Trend chart */}
      <div className="card" style={{ marginBottom: "var(--space-6)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
          <TrendingUp size={18} style={{ color: "var(--color-primary)" }} />
          <h3 style={{ margin: 0, fontSize: "var(--text-lg)", fontWeight: 700 }}>Tren Performa Tim</h3>
          <span className="table-meta">rata-rata score per bulan</span>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={trendData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="scoreFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.5} />
                <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.25)" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} width={40} />
            <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 8px 24px rgba(15,23,42,0.08)", fontSize: 13 }} />
            <Legend wrapperStyle={{ fontSize: 13 }} />
            <Line type="monotone" dataKey="Score" stroke="var(--color-primary)" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 6 }} fill="url(#scoreFill)" />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Category + Leaderboard */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "var(--space-6)", marginBottom: "var(--space-6)" }}>
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <Award size={18} style={{ color: "var(--color-secondary)" }} />
            <h3 style={{ margin: 0, fontSize: "var(--text-lg)", fontWeight: 700 }}>Skor per Kategori</h3>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={catData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="catFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-secondary)" stopOpacity={0.9} />
                  <stop offset="100%" stopColor="var(--color-secondary)" stopOpacity={0.35} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.25)" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 12, fill: "#64748b" }} axisLine={false} tickLine={false} width={40} />
              <Tooltip cursor={{ fill: "rgba(148,163,184,0.08)" }} contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 8px 24px rgba(15,23,42,0.08)", fontSize: 13 }} />
              <Bar dataKey="value" name="Score" fill="url(#catFill)" radius={[6, 6, 0, 0]} maxBarSize={48} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <Crown size={18} style={{ color: "#8b5cf6" }} />
            <h3 style={{ margin: 0, fontSize: "var(--text-lg)", fontWeight: 700 }}>Top Performers</h3>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={leaderboard} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.25)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11, fill: "#64748b" }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#475569" }} axisLine={false} tickLine={false} width={110} />
              <Tooltip cursor={{ fill: "rgba(148,163,184,0.08)" }} contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 8px 24px rgba(15,23,42,0.08)", fontSize: 13 }} />
              <Bar dataKey="Score" name="Score" radius={[0, 6, 6, 0]} maxBarSize={20}>
                {leaderboard.map((_, idx) => (
                  <Cell key={idx} fill={SCORE_GRADIENT[idx % SCORE_GRADIENT.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Org tree */}
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12, padding: "var(--space-4) var(--space-6) 0" }}>
          <Users size={18} style={{ color: "var(--color-primary)" }} />
          <h3 style={{ margin: 0, fontSize: "var(--text-lg)", fontWeight: 700 }}>Hierarki Tim</h3>
          <span className="table-meta">klik untuk expand · klik Detail untuk lihat performa</span>
        </div>

        {flat.map(({ node, depth }) => {
          const hasChildren = node.children.length > 0;
          const isExpanded = isNodeExpanded(node.user_id);
          const attDays = node.summary?.total_attendance_days || 0;
          const lateCount = node.summary?.total_late_count || 0;
          const pDay = node.period?.day_count || 1;
          const latePct = (lateCount / Math.max(pDay, 1)) * 100;
          const score = node.kpi_scores?.overall;

          return (
            <div
              key={node.user_id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "10px 24px",
                borderTop: "1px solid #f1f5f9",
                transition: "background 0.2s",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(79,140,255,0.04)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              <div style={{ width: depth * 22, flexShrink: 0 }} />
              {hasChildren ? (
                <button
                  onClick={() => toggleNode(node.user_id)}
                  className="btn-outline"
                  aria-label={isExpanded ? "Collapse" : "Expand"}
                  style={{ padding: 4, width: 28, height: 28, display: "flex", alignItems: "center", justifyContent: "center" }}
                >
                  {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>
              ) : (
                <div style={{ width: 28, flexShrink: 0 }} />
              )}

              <div
                title={node.full_name || node.nik}
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: "50%",
                  background: avatarColor(node.full_name),
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: 12,
                  flexShrink: 0,
                  textTransform: "uppercase",
                  boxShadow: "0 1px 3px rgba(15,23,42,0.2)",
                }}
              >
                {initialsOf(node.full_name, node.nik)}
              </div>

              <div style={{ flex: "1 1 auto", minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                  <span style={{ fontWeight: 700, color: "var(--color-primary)", fontSize: 14 }}>
                    {node.full_name || "—"}
                  </span>
                  {node.has_subordinates && (
                    <span className="badge badge-primary" style={{ fontSize: 10 }}>Lead</span>
                  )}
                  {depth === 1 ? (
                    <span className="badge badge-success" style={{ fontSize: 10 }}>Direct</span>
                  ) : (
                    <span className="badge badge-info" style={{ fontSize: 10 }}>Indirect Lv.{depth}</span>
                  )}
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 2, flexWrap: "wrap" }}>
                  <span className="table-meta">{node.nik}</span>
                  <span className="table-meta" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <Clock size={11} /> {fmt(attDays)} hari &middot; {fmt(lateCount)}x late ({fmt(latePct, 1)}%)
                  </span>
                </div>
              </div>

              <div style={{ textAlign: "right", minWidth: 64 }}>
                <div style={{ fontWeight: 800, fontSize: 16, color: score != null && score < 40 ? "#b91c1c" : "var(--color-primary)" }}>
                  {score != null ? fmt(score, 1) : "N/A"}
                </div>
                <div className="table-meta">overall</div>
              </div>

              <button
                className="btn-outline"
                onClick={() => (onOpenMemberDetail ? onOpenMemberDetail(node.user_id) : setDetailMember(node.user_id))}
                style={{ padding: "6px 14px", fontSize: 12, whiteSpace: "nowrap" }}
              >
                Detail
              </button>
            </div>
          );
        })}

        {flat.length === 0 && (
          <div className="empty-state" style={{ margin: 0 }}>
            <div className="empty-icon">
              <AlertTriangle size={24} />
            </div>
            <h4>Tidak ada anggota untuk ditampilkan</h4>
            <p>Tunggu sinkronisasi HRIS atau cek periode evaluasi.</p>
          </div>
        )}
      </div>
    </div>
  );
}