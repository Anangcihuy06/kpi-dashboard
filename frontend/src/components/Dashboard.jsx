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

  useEffect(() => {
    fetchSyncStatus();

    // Auto-refresh sync status every 30 seconds
    const syncInterval = setInterval(() => {
      fetchSyncStatus();
    }, 30000);

    return () => clearInterval(syncInterval);
  }, []);

  useEffect(() => {
    if (userId) {
      fetchPerformance();
    }
  }, [userId, selectedYear]);

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

  // Render header logic to be reusable in error/loading states
  const renderHeader = () => (
    <div className="header-ui">
      <div>
        <h2>{isSelf ? "My Performance Dashboard" : `Dashboard: ${data?.full_name || "Anggota Tim"}`}</h2>
        <p style={{ color: "var(--color-text-muted)", fontSize: "14px" }}>
          Divisi IT & Engineering | NIK: {userId === "482" ? "01.05.13.500" : "Bawahan"}
        </p>
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          marginTop: "8px",
          fontSize: "12px",
          color: "var(--color-text-muted)"
        }}>
          <RefreshCw size={12} className={syncStatus.is_syncing ? "animate-spin" : ""} />
          <span>Data disinkronisasi: <strong>{formatLastSyncTime()}</strong></span>
        </div>
      </div>
      <div className="filter-group">
        <select
          className="select-control"
          value={selectedYear}
          onChange={(e) => setSelectedYear(Number(e.target.value))}
        >
          {[2025, 2026, 2027].map(y => (
            <option key={y} value={y}>Tahun {y}</option>
          ))}
        </select>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div>
        {renderHeader()}
        <div style={{ textAlign: "center", padding: "40px" }}>
          <RefreshCw className="animate-spin" size={32} style={{ color: "#121854", margin: "0 auto 16px" }} />
          <p>Memuat data performa tahunan...</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div>
        {renderHeader()}
        <div className="card" style={{ borderColor: "#fee2e2", backgroundColor: "#fef2f2", color: "#b91c1c", marginTop: "20px" }}>
          <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Info size={18} /> Error Memuat Data</h4>
          <p>{error || "Data performa tahunan belum tersedia."}</p>
        </div>
      </div>
    );
  }

  // Monthly breakdown for trend chart
  const monthlyData = {};
  if (data.daily_breakdown) {
    data.daily_breakdown.forEach(day => {
      const month = day.date.substring(0, 7); // YYYY-MM
      if (!monthlyData[month]) {
        monthlyData[month] = { count: 0, total_score: 0, commits: 0, mrs: 0, sp: 0, name: month };
      }
      monthlyData[month].count += 1;
      monthlyData[month].total_score += day.overall_score;
      monthlyData[month].commits += day.commit_count;
      monthlyData[month].mrs += day.mr_merged;
      monthlyData[month].sp += day.issues_completed; // Approximation using issues
    });
  }

  const trendData = Object.values(monthlyData)
    .sort((a, b) => a.name.localeCompare(b.name))
    .map(m => ({
      name: new Date(m.name + "-01").toLocaleString('default', { month: 'short' }),
      Score: parseFloat((m.total_score / m.count).toFixed(2))
    }));

  // Stat calculations
  const summary = data.summary || {};
  const scores = data.kpi_scores || {};
  const breakdown = scores.details || [];

  // Attendance data
  const attendanceDays = summary.total_attendance_days || 0;
  const targetDays = data.period?.day_count || 10;
  const lateCount = summary.total_late_count || 0;
  const latePct = targetDays > 0 ? ((lateCount / targetDays) * 100).toFixed(1) : 0;
  const normalPct = targetDays > 0 ? (100 - latePct).toFixed(1) : 100;

  // Late badge color
  const getLateBadgeClass = (pct) => {
    if (pct >= 30) return "badge-danger";
    if (pct >= 15) return "badge-warning";
    return "badge-success";
  };

  // Data for radar chart
  const radarData = [
    { subject: 'DELIVERY', Skor: scores.delivery || 0, fullMark: 120 },
    { subject: 'ENGINEERING', Skor: scores.engineering || 0, fullMark: 120 },
    { subject: 'EFFORT', Skor: scores.effort || 0, fullMark: 120 },
    { subject: 'QUALITY', Skor: scores.quality || 0, fullMark: 120 }
  ];

  return (
    <div>
      {renderHeader()}

      {/* Stats Cards Grid */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)", color: "#15803d" }}>
            <Award size={24} />
          </div>
          <div className="stat-info">
            <h4>{scores.overall || 0}</h4>
            <p>Weighted score</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <CheckSquare size={24} />
          </div>
          <div className="stat-info">
            <h4>{summary.total_story_points || 0} SP</h4>
            <p>Jira Completed</p>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon" style={{ background: "linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)", color: "#0369a1" }}>
            <GitMerge size={24} />
          </div>
          <div className="stat-info">
            <h4>{summary.total_mrs_merged || 0} MR</h4>
            <p>GitLab Merged</p>
          </div>
        </div>



        {/* Attendance Card */}
        <div className="stat-card">
          <div className="stat-icon" style={{ background: "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)", color: "#166534" }}>
            <UserCheck size={24} />
          </div>
          <div className="stat-info">
            <h4>{attendanceDays}/{targetDays} <span style={{ fontSize: "14px", fontWeight: 500 }}>Hari</span></h4>
            <p>Kehadiran</p>
          </div>
        </div>

        {/* Late Rate Card */}
        <div className="stat-card">
          <div className="stat-icon" style={{ background: latePct >= 30 ? "linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)" : latePct >= 15 ? "linear-gradient(135deg, #fef9c3 0%, #fef08a 100%)" : "linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)", color: latePct >= 30 ? "#b91c1c" : latePct >= 15 ? "#a16207" : "#15803d" }}>
            <Clock size={24} />
          </div>
          <div className="stat-info">
            <h4 style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {latePct}%
              <span className={`badge ${getLateBadgeClass(latePct)}`} style={{ fontSize: "10px" }}>
                {latePct >= 30 ? "CRITICAL" : latePct >= 15 ? "WARNING" : "GOOD"}
              </span>
            </h4>
            <p>Late Rate</p>
          </div>
        </div>
      </div>
      {/* Attendance Progress Bar */}
      <div className="card" style={{ marginBottom: "24px" }}>
        <h3 style={{ marginBottom: "16px", fontSize: "16px" }}>Rasio Kehadiran Tahunan</h3>
        <div className="attendance-progress-container">
          <div className="attendance-progress-labels">
            <span style={{ color: "#15803d", fontWeight: 700, fontSize: "13px" }}>On-Time: {normalPct}%</span>
            <span style={{ color: "#b91c1c", fontWeight: 700, fontSize: "13px" }}>Telat: {latePct}%</span>
          </div>
          <div className="attendance-progress-bar">
            <div className="attendance-progress-fill normal" style={{ width: `${normalPct}%` }}></div>
            <div className="attendance-progress-fill late" style={{ width: `${latePct}%` }}></div>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "24px", marginBottom: "24px" }}>
        {/* Line Trend Chart */}
        <div className="card" style={{ height: "400px" }}>
          <h3 style={{ marginBottom: "20px" }}>Tren Performa KPI (All Sprints)</h3>
          <div style={{ width: "100%", height: "300px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={12} tickLine={false} />
                <YAxis domain={[0, 120]} stroke="var(--color-text-muted)" fontSize={12} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: "12px", border: "1px solid #cbd5e1" }} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="Score"
                  stroke="var(--color-primary)"
                  strokeWidth={3}
                  activeDot={{ r: 8 }}
                  dot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Radar Metrics Breakdown */}
        <div className="card" style={{ height: "400px" }}>
          <h3 style={{ marginBottom: "20px" }}>Proporsi Skor Matriks</h3>
          <div style={{ width: "100%", height: "300px", display: "flex", justifyContent: "center" }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" fontSize={11} />
                <PolarRadiusAxis angle={30} domain={[0, 120]} />
                <Radar
                  name="Skor Indikator"
                  dataKey="Skor"
                  stroke="var(--color-secondary)"
                  fill="var(--color-secondary)"
                  fillOpacity={0.3}
                />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Detailed Breakdown Card */}
      <div className="card">
        <h3 style={{ marginBottom: "20px" }}>Rincian Capaian & Rumus Matriks</h3>
        <div className="table-container">
          <table className="custom-table">
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
                    <td style={{ fontWeight: 700, color: "var(--color-primary)" }}>
                      {item.metric_key.toUpperCase()}
                    </td>
                    <td style={{ fontFamily: "monospace", color: "var(--color-secondary)", fontSize: "13px" }}>
                      {item.formula}
                    </td>
                    <td>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                        {item.variables && typeof item.variables === 'object' && Object.entries(item.variables).map(([k, v]) => (
                          <span key={k} className="badge badge-primary">
                            {k}: {typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(2)) : v}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td style={{ fontWeight: 600 }}>
                      {item.actual_value}
                    </td>
                    <td style={{ fontWeight: 600 }}>
                      <span className={`badge ${item.calculated_score >= 100 ? "badge-success" : "badge-primary"}`}>
                        {item.calculated_score}
                      </span>
                    </td>
                    <td>
                      {(item.weight * 100).toFixed(0)}%
                    </td>
                    <td style={{ fontWeight: 800, color: "var(--color-primary)" }}>
                      {item.weighted_score}
                    </td>
                  </tr>
                  {item.metric_key === "feature_complexity" && (
                    <tr>
                      <td colSpan="7" style={{ padding: "10px 24px 20px" }}>
                        <button
                          className="btn-outline"
                          onClick={() => setIsTasksOpen(!isTasksOpen)}
                          style={{ fontSize: "12px", padding: "6px 12px", cursor: "pointer" }}
                        >
                          {isTasksOpen ? "Sembunyikan Rincian Task" : `Tampilkan Rincian Task JIRA (${data.completed_tasks?.length || 0})`}
                        </button>
                        {isTasksOpen && data.completed_tasks && (
                          <div style={{ marginTop: "12px", border: "1px solid #e2e8f0", borderRadius: "8px", overflow: "hidden", backgroundColor: "#f8fafc" }}>
                            <div style={{ padding: "12px 16px", borderBottom: "1px solid #e2e8f0", backgroundColor: "#f1f5f9" }}>
                              <h4 style={{ margin: 0, fontSize: "13px", color: "var(--color-primary)" }}>Breakdown Task & Bobot Multi-Factor (Tahun {selectedYear})</h4>
                            </div>
                            <div style={{ maxHeight: "300px", overflowY: "auto", position: "relative" }}>
                              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}>
                                <thead>
                                  <tr style={{ backgroundColor: "#f1f5f9", color: "#475569", fontWeight: 700 }}>
                                    <th style={{ padding: "8px 12px", width: "90px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>Key</th>
                                    <th style={{ padding: "8px 12px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>Summary & Deskripsi</th>
                                    <th style={{ padding: "8px 12px", width: "100px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>Tanggal</th>
                                    <th style={{ padding: "8px 12px", width: "100px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>Status</th>
                                    <th style={{ padding: "8px 12px", width: "30px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>C</th>
                                    <th style={{ padding: "8px 12px", width: "30px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>I</th>
                                    <th style={{ padding: "8px 12px", width: "30px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>S</th>
                                    <th style={{ padding: "8px 12px", width: "30px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>R</th>
                                    <th style={{ padding: "8px 12px", width: "30px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>O</th>
                                    <th style={{ padding: "8px 12px", width: "45px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>Total</th>
                                    <th style={{ padding: "8px 12px", textAlign: "right", width: "70px", position: "sticky", top: 0, backgroundColor: "#f1f5f9", zIndex: 1, borderBottom: "1.5px solid #cbd5e1" }}>KPI Pts</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {data.completed_tasks.length === 0 ? (
                                    <tr>
                                      <td colSpan="11" style={{ padding: "16px", textAlign: "center", color: "#64748b" }}>Tidak ada task yang diselesaikan.</td>
                                    </tr>
                                  ) : (
                                    data.completed_tasks.map((task, tidx) => (
                                      <tr key={tidx} style={{ borderBottom: "1px solid #e2e8f0", backgroundColor: tidx % 2 === 0 ? "#ffffff" : "#f8fafc" }}>
                                        <td style={{ padding: "8px 12px", fontWeight: 600 }}>{task.key}</td>
                                        <td style={{ padding: "8px 12px", color: "#334155" }}>
                                          <div style={{ fontWeight: 600, color: "#1e293b" }}>{task.summary}</div>
                                          {task.description && (
                                            <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px", maxWidth: "450px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={task.description}>
                                              {task.description}
                                            </div>
                                          )}
                                        </td>
                                        <td style={{ padding: "8px 12px", color: "#475569", whiteSpace: "nowrap" }}>
                                          {task.resolved_date || "—"}
                                        </td>
                                        <td style={{ padding: "8px 12px" }}>
                                          <span className="badge badge-success" style={{ fontSize: "10px", padding: "3px 8px" }}>{task.status}</span>
                                        </td>
                                        <td style={{ padding: "8px 12px" }}>{task.complexity}</td>
                                        <td style={{ padding: "8px 12px" }}>{task.impact}</td>
                                        <td style={{ padding: "8px 12px" }}>{task.scope}</td>
                                        <td style={{ padding: "8px 12px" }}>{task.risk}</td>
                                        <td style={{ padding: "8px 12px" }}>{task.ownership}</td>
                                        <td style={{ padding: "8px 12px", fontWeight: 600 }}>
                                          {task.complexity + task.impact + task.scope + task.risk + task.ownership}
                                        </td>
                                        <td style={{ padding: "8px 12px", fontWeight: 700, color: "var(--color-primary)", textAlign: "right" }}>{task.points.toFixed(1)}</td>
                                      </tr>
                                    ))
                                  )}
                                </tbody>
                              </table>
                            </div>
                            <div style={{ padding: "12px 16px", borderTop: "1px solid #e2e8f0", backgroundColor: "#f1f5f9", fontSize: "11px", color: "#475569", display: "flex", gap: "16px", flexWrap: "wrap", lineHeight: "1.5" }}>
                              <span style={{ fontWeight: 700, color: "var(--color-primary)" }}>Legenda Dimensi Multi-Factor:</span>
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
  );
}
