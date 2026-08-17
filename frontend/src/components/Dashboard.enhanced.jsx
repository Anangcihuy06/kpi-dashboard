import React, { useState, useEffect } from "react";
import { 
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from "recharts";
import { Award, TrendingUp, GitMerge, CheckSquare, Calendar, RefreshCw, Clock, UserCheck, Info } from "lucide-react";

export default function Dashboard({ userId, isSelf }) {
  const [data, setData] = useState(null);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncStatus, setSyncStatus] = useState({ last_sync_time: null, is_syncing: false });
  const [isTasksOpen, setIsTasksOpen] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetchSyncStatus();

    const syncInterval = setInterval(() => {
      fetchSyncStatus();
    }, 30000);

    return () => clearInterval(syncInterval);
  }, []);

  useEffect(() => {
    if (userId && mounted) {
      fetchPerformance();
    }
  }, [userId, selectedYear, mounted]);

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
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/kpi/yearly-performance?user_id=${userId}&year=${selectedYear}`);
      if (!response.ok) throw new Error("Gagal mengambil data KPI");
      const result = await response.json();
      if (result.status === "success") {
        setData(result.data);
      } else {
        setData(null);
      }
    } catch (err) {
      setError(err.message);
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

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} hari yang lalu`;
  };

  const renderHeader = () => (
    <div style={{ marginBottom: "32px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
        <div>
          <h1 style={{ fontSize: "32px", marginBottom: "8px", background: "var(--gradient-primary)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", backgroundClip: "text" }}>
            {isSelf ? "My Performance Dashboard" : `Dashboard: ${data?.full_name || "Anggota Tim"}`}
          </h1>
          <p style={{ color: "var(--color-text-muted)", fontSize: "14px", fontWeight: "500" }}>
            Divisi IT & Engineering | NIK: {userId === "482" ? "01.05.13.500" : "Bawahan"}
          </p>
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            marginTop: "12px",
            padding: "8px 16px",
            background: "var(--color-tint-light)",
            borderRadius: "var(--radius-full)",
            width: "fit-content"
          }}>
            <RefreshCw size={14} className={syncStatus.is_syncing ? "animate-spin" : ""} style={{ color: "var(--color-secondary)" }} />
            <span style={{ fontSize: "12px", fontWeight: "600", color: "var(--color-text-muted)" }}>
              Data disinkronisasi: <strong style={{ color: "var(--color-primary)" }}>{formatLastSyncTime()}</strong>
            </span>
          </div>
        </div>
        <div style={{ display: "flex", gap: "12px" }}>
          <select
            style={{
              padding: "12px 20px",
              border: "2px solid #e2e8f0",
              borderRadius: "var(--radius-md)",
              fontSize: "14px",
              fontWeight: "600",
              color: "var(--color-text-dark)",
              background: "var(--color-card-bg)",
              cursor: "pointer",
              transition: "var(--transition-base)",
              outline: "none"
            }}
            value={selectedYear}
            onChange={(e) => setSelectedYear(Number(e.target.value))}
            onFocus={(e) => e.target.style.borderColor = "var(--color-secondary)"}
            onBlur={(e) => e.target.style.borderColor = "#e2e8f0"}
          >
            {[2025, 2026, 2027].map(y => (
              <option key={y} value={y}>Tahun {y}</option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div style={{ animation: "fadeIn 0.4s ease-out" }}>
        {renderHeader()}
        <div className="card-premium" style={{ textAlign: "center", padding: "60px 40px" }}>
          <div style={{ marginBottom: "24px" }}>
            <RefreshCw className="animate-spin" size={48} style={{ color: "var(--color-secondary)", margin: "0 auto" }} />
          </div>
          <p style={{ fontSize: "18px", fontWeight: "600", color: "var(--color-text-muted)" }}>Memuat data performa tahunan...</p>
          <p style={{ fontSize: "14px", color: "var(--color-text-light)", marginTop: "8px" }}>Mohon tunggu sebentar</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ animation: "fadeIn 0.4s ease-out" }}>
        {renderHeader()}
        <div className="card-premium" style={{ 
          borderColor: "#fecaca", 
          backgroundColor: "#fef2f2", 
          color: "#b91c1c",
          display: "flex",
          alignItems: "center",
          gap: "16px",
          padding: "24px 32px"
        }}>
          <div style={{ 
            width: "48px", 
            height: "48px", 
            borderRadius: "50%", 
            background: "rgba(185, 28, 28, 0.1)", 
            display: "flex", 
            alignItems: "center", 
            justifyContent: "center" 
          }}>
            <Info size={24} style={{ color: "#b91c1c" }} />
          </div>
          <div>
            <h4 style={{ marginBottom: "4px", fontSize: "16px", fontWeight: "700" }}>Error Memuat Data</h4>
            <p style={{ fontSize: "14px", opacity: 0.9 }}>{error || "Data performa tahunan belum tersedia."}</p>
          </div>
        </div>
      </div>
    );
  }

  const monthlyData = {};
  if (data.daily_breakdown) {
    data.daily_breakdown.forEach(day => {
      const month = day.date.substring(0, 7);
      if (!monthlyData[month]) {
        monthlyData[month] = { count: 0, total_score: 0, commits: 0, mrs: 0, sp: 0, name: month };
      }
      monthlyData[month].count += 1;
      monthlyData[month].total_score += day.overall_score;
      monthlyData[month].commits += day.commit_count;
      monthlyData[month].mrs += day.mr_merged;
      monthlyData[month].sp += day.issues_completed;
    });
  }

  const trendData = Object.values(monthlyData)
    .sort((a, b) => a.name.localeCompare(b.name))
    .map(m => ({
      name: new Date(m.name + "-01").toLocaleString('default', { month: 'short' }),
      Score: parseFloat((m.total_score / m.count).toFixed(2))
    }));

  const summary = data.summary || {};
  const scores = data.kpi_scores || {};
  const breakdown = scores.details || [];

  const attendanceDays = summary.total_attendance_days || 0;
  const targetDays = data.period?.day_count || 10;
  const lateCount = summary.total_late_count || 0;
  const latePct = targetDays > 0 ? ((lateCount / targetDays) * 100).toFixed(1) : 0;
  const normalPct = targetDays > 0 ? (100 - latePct).toFixed(1) : 100;

  const getLateBadgeClass = (pct) => {
    if (pct >= 30) return "badge-danger";
    if (pct >= 15) return "badge-warning";
    return "badge-success";
  };

  const radarData = [
    { subject: 'DELIVERY', Skor: scores.delivery || 0, fullMark: 120 },
    { subject: 'ENGINEERING', Skor: scores.engineering || 0, fullMark: 120 },
    { subject: 'EFFORT', Skor: scores.effort || 0, fullMark: 120 },
    { subject: 'QUALITY', Skor: scores.quality || 0, fullMark: 120 }
  ];

  return (
    <div style={{ animation: "fadeIn 0.4s ease-out" }}>
      {renderHeader()}

      {/* Enhanced Stats Cards Grid */}
      <div className="stats-grid-premium">
        <div className="stat-card-premium animate-slide-up" style={{ animationDelay: "0.1s" }}>
          <div className="stat-icon-premium" style={{ 
            background: "linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)", 
            color: "#15803d" 
          }}>
            <Award size={24} />
          </div>
          <div className="stat-info">
            <h4>{scores.overall || 0}</h4>
            <p>Weighted score</p>
          </div>
        </div>

        <div className="stat-card-premium animate-slide-up" style={{ animationDelay: "0.2s" }}>
          <div className="stat-icon-premium">
            <CheckSquare size={24} />
          </div>
          <div className="stat-info">
            <h4>{summary.total_story_points || 0} SP</h4>
            <p>Jira Completed</p>
          </div>
        </div>

        <div className="stat-card-premium animate-slide-up" style={{ animationDelay: "0.3s" }}>
          <div className="stat-icon-premium" style={{ 
            background: "linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)", 
            color: "#0369a1" 
          }}>
            <GitMerge size={24} />
          </div>
          <div className="stat-info">
            <h4>{summary.total_mrs_merged || 0} MR</h4>
            <p>GitLab Merged</p>
          </div>
        </div>

        <div className="stat-card-premium animate-slide-up" style={{ animationDelay: "0.4s" }}>
          <div className="stat-icon-premium" style={{ 
            background: "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)", 
            color: "#166534" 
          }}>
            <UserCheck size={24} />
          </div>
          <div className="stat-info">
            <h4>{attendanceDays}/{targetDays} <span style={{ fontSize: "14px", fontWeight: 500 }}>Hari</span></h4>
            <p>Kehadiran</p>
          </div>
        </div>

        <div className="stat-card-premium animate-slide-up" style={{ animationDelay: "0.5s" }}>
          <div className="stat-icon-premium" style={{ 
            background: latePct >= 30 
              ? "linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)" 
              : latePct >= 15 
              ? "linear-gradient(135deg, #fef9c3 0%, #fef08a 100%)" 
              : "linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)", 
            color: latePct >= 30 ? "#b91c1c" : latePct >= 15 ? "#a16207" : "#15803d" 
          }}>
            <Clock size={24} />
          </div>
          <div className="stat-info">
            <h4 style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {latePct}%
              <span className={`badge-premium ${getLateBadgeClass(latePct)}`} style={{ fontSize: "10px" }}>
                {latePct >= 30 ? "CRITICAL" : latePct >= 15 ? "WARNING" : "GOOD"}
              </span>
            </h4>
            <p>Late Rate</p>
          </div>
        </div>
      </div>

      {/* Enhanced Attendance Progress Section */}
      <div className="card-premium" style={{ marginBottom: "24px" }}>
        <h3 style={{ 
          marginBottom: "20px", 
          fontSize: "18px", 
          fontWeight: "700", 
          color: "var(--color-primary)",
          display: "flex",
          alignItems: "center",
          gap: "10px"
        }}>
          <Calendar size={20} style={{ color: "var(--color-secondary)" }} />
          Rasio Kehadiran Tahunan
        </h3>
        <div style={{ marginBottom: "16px" }}>
          <div style={{ 
            display: "flex", 
            justifyContent: "space-between", 
            marginBottom: "12px" 
          }}>
            <div style={{ 
              padding: "8px 16px", 
              background: "var(--color-success-light)", 
              color: "#15803d", 
              borderRadius: "var(--radius-full)", 
              fontSize: "13px", 
              fontWeight: "700",
              display: "flex",
              alignItems: "center",
              gap: "6px"
            }}>
              <UserCheck size={14} />
              On-Time: {normalPct}%
            </div>
            <div style={{ 
              padding: "8px 16px", 
              background: latePct >= 30 
                ? "var(--color-danger-light)" 
                : "var(--color-warning-light)", 
              color: latePct >= 30 ? "#b91c1c" : "#a16207", 
              borderRadius: "var(--radius-full)", 
              fontSize: "13px", 
              fontWeight: "700",
              display: "flex",
              alignItems: "center",
              gap: "6px"
            }}>
              <Clock size={14} />
              Telat: {latePct}%
            </div>
          </div>
          <div className="progress-premium">
            <div className="progress-fill-premium normal" style={{ 
              width: `${normalPct}%`,
              background: "linear-gradient(90deg, #22c55e 0%, #16a34a 100%)"
            }}></div>
            <div className="progress-fill-premium late" style={{ 
              width: `${latePct}%`,
              background: latePct >= 30 
                ? "linear-gradient(90deg, #ef4444 0%, #dc2626 100%)" 
                : "linear-gradient(90deg, #ef4444 0%, #f59e0b 100%)"
            }}></div>
          </div>
        </div>
      </div>

      {/* Enhanced Charts Section */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "24px", marginBottom: "24px" }}>
        <div className="chart-container-premium animate-slide-up" style={{ animationDelay: "0.6s" }}>
          <h3 style={{ marginBottom: "20px" }}>
            <TrendingUp size={20} style={{ color: "var(--color-secondary)" }} />
            Tren Performa KPI (All Sprints)
          </h3>
          <div style={{ width: "100%", height: "300px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={12} tickLine={false} />
                <YAxis domain={[0, 120]} stroke="var(--color-text-muted)" fontSize={12} tickLine={false} />
                <Tooltip 
                  contentStyle={{ 
                    borderRadius: "12px", 
                    border: "1px solid #e2e8f0", 
                    boxShadow: "var(--shadow-lg)",
                    padding: "12px 16px"
                  }} 
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="Score"
                  stroke="var(--color-primary)"
                  strokeWidth={3}
                  activeDot={{ r: 8, fill: "var(--color-primary)", stroke: "white", strokeWidth: 2 }}
                  dot={{ r: 5, fill: "white", stroke: "var(--color-secondary)", strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="chart-container-premium animate-slide-up" style={{ animationDelay: "0.7s" }}>
          <h3 style={{ marginBottom: "20px" }}>
            <Award size={20} style={{ color: "var(--color-secondary)" }} />
            Proporsi Skor Matriks
          </h3>
          <div style={{ width: "100%", height: "300px", display: "flex", justifyContent: "center" }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid stroke="#e2e8f0" />
                <PolarAngleAxis dataKey="subject" fontSize={11} tick={{ fill: "var(--color-text-muted)" }} />
                <PolarRadiusAxis angle={30} domain={[0, 120]} tick={{ fill: "var(--color-text-light)", fontSize: 10 }} />
                <Radar
                  name="Skor Indikator"
                  dataKey="Skor"
                  stroke="var(--color-secondary)"
                  fill="var(--color-secondary)"
                  fillOpacity={0.3}
                  dot={{ fill: "var(--color-primary)", r: 4 }}
                />
                <Tooltip 
                  contentStyle={{ 
                    borderRadius: "12px", 
                    border: "1px solid #e2e8f0", 
                    boxShadow: "var(--shadow-lg)",
                    padding: "12px 16px"
                  }} 
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Enhanced Detailed Breakdown Card */}
      <div className="card-premium animate-slide-up" style={{ animationDelay: "0.8s" }}>
        <h3 style={{ 
          marginBottom: "24px", 
          fontSize: "18px", 
          fontWeight: "700", 
          color: "var(--color-primary)",
          display: "flex",
          alignItems: "center",
          gap: "10px"
        }}>
          <CheckSquare size={20} style={{ color: "var(--color-secondary)" }} />
          Rincian Capaian & Rumus Matriks
        </h3>
        <div className="data-table-container">
          <div className="table-container">
            <table className="table-premium">
              <thead>
                <tr>
                  <th>Indikator</th>
                  <th>Rumus Formula</th>
                  <th>Variabel / Input Raw</th>
                  <th>Nilai Raw</th>
                  <th>Skor Capped</th>
                  <th>Bobot</th>
                  <th>Skor Akhir (Weighted)</th>
                </tr>
              </thead>
              <tbody>
                {breakdown.map((item, idx) => (
                  <React.Fragment key={idx}>
                    <tr>
                      <td style={{ fontWeight: 700, color: "var(--color-primary)", fontSize: "13px" }}>
                        {item.metric_key.toUpperCase()}
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", color: "var(--color-secondary)", fontSize: "12px" }}>
                        {item.formula}
                      </td>
                      <td>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                          {item.variables && typeof item.variables === 'object' && Object.entries(item.variables).map(([k, v]) => (
                            <span key={k} className="badge-premium badge-primary">
                              {k}: {typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(2)) : v}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td style={{ fontWeight: 600, fontSize: "14px" }}>
                        {item.actual_value}
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        <span className={`badge-premium ${item.calculated_score >= 100 ? "badge-success" : "badge-primary"}`}>
                          {item.calculated_score}
                        </span>
                      </td>
                      <td style={{ fontSize: "14px", color: "var(--color-text-muted)" }}>
                        {(item.weight * 100).toFixed(0)}%
                      </td>
                      <td style={{ fontWeight: 800, color: "var(--color-primary)", fontSize: "16px" }}>
                        {item.weighted_score}
                      </td>
                    </tr>
                    {item.metric_key === "feature_complexity" && (
                      <tr>
                        <td colSpan="7" style={{ padding: "16px 24px 24px", background: "var(--color-bg-light)" }}>
                          <button
                            className="btn btn-outline"
                            onClick={() => setIsTasksOpen(!isTasksOpen)}
                            style={{ fontSize: "13px", padding: "8px 16px", borderRadius: "var(--radius-md)" }}
                          >
                            {isTasksOpen ? (
                              <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                <CheckSquare size={14} /> Sembunyikan Rincian Task
                              </span>
                            ) : (
                              <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                <Award size={14} /> Tampilkan Rincian Task JIRA ({data.completed_tasks?.length || 0})
                              </span>
                            )}
                          </button>
                          {isTasksOpen && data.completed_tasks && (
                            <div style={{ 
                              marginTop: "16px", 
                              border: "1px solid #e2e8f0", 
                              borderRadius: "var(--radius-lg)", 
                              overflow: "hidden", 
                              background: "white",
                              boxShadow: "var(--shadow-sm)"
                            }}>
                              <div style={{ 
                                padding: "16px 20px", 
                                borderBottom: "1px solid #e2e8f0", 
                                background: "linear-gradient(180deg, #fafbfc 0%, #f8fafc 100%)" 
                              }}>
                                <h4 style={{ 
                                  margin: 0, 
                                  fontSize: "14px", 
                                  fontWeight: "700", 
                                  color: "var(--color-primary)",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "8px"
                                }}>
                                  <GitMerge size={16} style={{ color: "var(--color-secondary)" }} />
                                  Breakdown Task & Bobot Multi-Factor (Tahun {selectedYear})
                                </h4>
                              </div>
                              <div style={{ maxHeight: "300px", overflowY: "auto", position: "relative" }}>
                                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}>
                                  <thead style={{ position: "sticky", top: 0, zIndex: 1 }}>
                                    <tr style={{ 
                                      background: "linear-gradient(180deg, #fafbfc 0%, #f8fafc 100%)", 
                                      color: "var(--color-text-muted)", 
                                      fontWeight: "700",
                                      borderBottom: "2px solid #e2e8f0"
                                    }}>
                                      <th style={{ padding: "12px 16px", width: "90px" }}>Key</th>
                                      <th style={{ padding: "12px 16px" }}>Summary & Deskripsi</th>
                                      <th style={{ padding: "12px 16px", width: "100px" }}>Tanggal</th>
                                      <th style={{ padding: "12px 16px", width: "100px" }}>Status</th>
                                      <th style={{ padding: "12px 16px", width: "30px" }}>C</th>
                                      <th style={{ padding: "12px 16px", width: "30px" }}>I</th>
                                      <th style={{ padding: "12px 16px", width: "30px" }}>S</th>
                                      <th style={{ padding: "12px 16px", width: "30px" }}>R</th>
                                      <th style={{ padding: "12px 16px", width: "30px" }}>O</th>
                                      <th style={{ padding: "12px 16px", width: "45px" }}>Total</th>
                                      <th style={{ padding: "12px 16px", textAlign: "right", width: "70px" }}>KPI Pts</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {data.completed_tasks.length === 0 ? (
                                      <tr>
                                        <td colSpan="11" style={{ padding: "20px", textAlign: "center", color: "var(--color-text-muted)" }}>
                                          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "12px" }}>
                                            <Award size={32} style={{ color: "var(--color-text-light)" }} />
                                            <span>Tidak ada task yang diselesaikan.</span>
                                          </div>
                                        </td>
                                      </tr>
                                    ) : (
                                      data.completed_tasks.map((task, tidx) => (
                                        <tr key={tidx} style={{ 
                                          borderBottom: "1px solid #f1f5f9", 
                                          background: tidx % 2 === 0 ? "white" : "var(--color-bg-light)",
                                          transition: "background var(--transition-fast)"
                                        }}>
                                          <td style={{ padding: "12px 16px", fontWeight: "600", color: "var(--color-primary)" }}>{task.key}</td>
                                          <td style={{ padding: "12px 16px", color: "var(--color-text-dark)" }}>
                                            <div style={{ fontWeight: "600", color: "var(--color-text-primary)" }}>{task.summary}</div>
                                            {task.description && (
                                              <div style={{ 
                                                fontSize: "11px", 
                                                color: "var(--color-text-muted)", 
                                                marginTop: "4px", 
                                                maxWidth: "450px", 
                                                overflow: "hidden", 
                                                textOverflow: "ellipsis", 
                                                whiteSpace: "nowrap" 
                                              }} title={task.description}>
                                                {task.description}
                                              </div>
                                            )}
                                          </td>
                                          <td style={{ padding: "12px 16px", color: "var(--color-text-muted)", whiteSpace: "nowrap", fontSize: "12px" }}>
                                            {task.resolved_date || "—"}
                                          </td>
                                          <td style={{ padding: "12px 16px" }}>
                                            <span className="badge-premium badge-success" style={{ fontSize: "10px" }}>
                                              {task.status}
                                            </span>
                                          </td>
                                          <td style={{ padding: "12px 16px", textAlign: "center", fontWeight: "600" }}>{task.complexity}</td>
                                          <td style={{ padding: "12px 16px", textAlign: "center", fontWeight: "600" }}>{task.impact}</td>
                                          <td style={{ padding: "12px 16px", textAlign: "center", fontWeight: "600" }}>{task.scope}</td>
                                          <td style={{ padding: "12px 16px", textAlign: "center", fontWeight: "600" }}>{task.risk}</td>
                                          <td style={{ padding: "12px 16px", textAlign: "center", fontWeight: "600" }}>{task.ownership}</td>
                                          <td style={{ padding: "12px 16px", textAlign: "center", fontWeight: "700" }}>
                                            {task.complexity + task.impact + task.scope + task.risk + task.ownership}
                                          </td>
                                          <td style={{ padding: "12px 16px", fontWeight: "700", color: "var(--color-primary)", textAlign: "right" }}>{task.points.toFixed(1)}</td>
                                        </tr>
                                      ))
                                    )}
                                  </tbody>
                                </table>
                              </div>
                              <div style={{ 
                                padding: "16px 20px", 
                                borderTop: "1px solid #e2e8f0", 
                                background: "linear-gradient(180deg, #fafbfc 0%, #f8fafc 100%)", 
                                fontSize: "11px", 
                                color: "var(--color-text-muted)", 
                                display: "flex", 
                                gap: "16px", 
                                flexWrap: "wrap", 
                                lineHeight: "1.6",
                                fontWeight: "500"
                              }}>
                                <span style={{ 
                                  fontWeight: "700", 
                                  color: "var(--color-primary)",
                                  padding: "4px 12px",
                                  background: "var(--color-tint-light)",
                                  borderRadius: "var(--radius-full)"
                                }}>Legenda Dimensi Multi-Factor:</span>
                                <span><strong>C (Complexity)</strong>: Kerumitan Teknis (0-5)</span>
                                <span><strong>I (Impact)</strong>: Dampak Bisnis (0-5)</span>
                                <span><strong>S (Scope)</strong>: Cakupan Sistem (0-5)</span>
                                <span><strong>R (Risk)</strong>: Risiko Rilis (0-3)</span>
                                <span><strong>O (Ownership)</strong>: Tingkat Kepemilikan (0-2)</span>
                                <span><strong>Total</strong>: Skor Kumulatif (0-20)</span>
                                <span><strong>KPI Pts</strong>: Poin KPI Terpetakan (1-25)</span>
                              </div>
                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}