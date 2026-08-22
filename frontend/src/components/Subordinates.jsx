import React, { useState, useEffect } from "react";
import { Users, Search, ArrowLeft, ChevronDown, ChevronUp, BarChart2, Award, Info, Clock, UserCheck, AlertTriangle, RefreshCw, Mail, Download, Crown, TrendingUp } from "lucide-react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, BarChart, Bar, Cell } from "recharts";
import { exportToCSV } from "../utils/export";
import { toast } from "sonner";
import Dashboard from "./Dashboard";


const SCORE_GRADIENT = ["#12ccab", "#4f8cff", "#8b5cf6", "#f59e0b", "#ef4444"];

export default function Subordinates({ supervisorId, initialMemberId, onResetTarget }) {
  const [subordinates, setSubordinates] = useState([]);
  const [selectedSubId, setSelectedSubId] = useState(null);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [syncStatus, setSyncStatus] = useState({ last_sync_time: null, is_syncing: false });

  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedRows, setExpandedRows] = useState({});
  const [selectedSubName, setSelectedSubName] = useState("");
  const [editingEmails, setEditingEmails] = useState({});
  const [emailSaving, setEmailSaving] = useState({});
  const [attendanceSyncing, setAttendanceSyncing] = useState(false);
  const [calcProgress, setCalcProgress] = useState({ progress: 0, total: 0 });

  // Drill-in target passthrough from the org Dashboard (hierarchy tree).
  useEffect(() => {
    if (initialMemberId) {
      setSelectedSubId(initialMemberId);
    }
  }, [initialMemberId]);

  useEffect(() => {
    fetchSyncStatus();

    // Auto-refresh sync status every 30 seconds
    const syncInterval = setInterval(() => {
      fetchSyncStatus();
    }, 30000);

    return () => clearInterval(syncInterval);
  }, []);

  useEffect(() => {
    if (supervisorId) {
      setLoading(true);
      fetchTeamScores();
    }
  }, [supervisorId, selectedYear]);

  const fetchSyncStatus = async () => {
    try {
      const response = await fetch(import.meta.env.VITE_API_URL + "/api/v1/sync/status");
      const status = await response.json();
      setSyncStatus(status);
    } catch (err) {
      console.error("Gagal mengambil status sync:", err);
    }
  };

  const syncAttendanceForYear = async (year) => {
    if (!supervisorId || attendanceSyncing) return;
    setAttendanceSyncing(true);
    try {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL}/api/v1/attendance/sync-year?supervisor_id=${supervisorId}&year=${year}`,
        { method: "POST" }
      );
      const data = await res.json();
      if (!res.ok) {
        toast.error(data.detail || "Gagal sinkronisasi KPI & Attendance");
        setAttendanceSyncing(false);
        return;
      }
      toast.info("[Attendance Sync] Memulai sinkronisasi KPI & Attendance...");
      
      if (data.job_id) {
        // Poll job status every 3s
        const poll = setInterval(async () => {
          try {
            const statusRes = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/jobs/${data.job_id}`);
            if (statusRes.ok) {
              const statusData = await statusRes.json();
              if (statusData.status === "COMPLETED" || statusData.status === "FAILED") {
                clearInterval(poll);
                await fetchTeamScores(true); // Refresh after completion (force recalc)
                setAttendanceSyncing(false);
                if (statusData.status === "COMPLETED") {
                  toast.success("Sinkronisasi KPI & Attendance berhasil! Skor KPI diperbarui.");
                } else {
                  toast.error("Sinkronisasi KPI & Attendance gagal.");
                }
              }
            }
          } catch (e) {
            console.error("Error polling job status:", e);
          }
        }, 10000);
      } else {
        // Fallback
        setTimeout(async () => {
          await fetchTeamScores(true);
          setAttendanceSyncing(false);
          toast.success("Sinkronisasi KPI & Attendance selesai! Skor KPI diperbarui.");
        }, 10000);
      }
    } catch (err) {
      toast.error("Gagal sinkronisasi KPI & Attendance: " + err.message);
      setAttendanceSyncing(false);
    }
  };

  const fetchTeamScores = async (force = false) => {
    try {
      const url = `${import.meta.env.VITE_API_URL}/api/v1/kpi/team-yearly?user_id=${supervisorId}&year=${selectedYear}&direct_only=true${force ? '&force_refresh=true' : ''}`;
      const response = await fetch(url, {
        cache: 'no-store'
      });
      
      if (response.status === 202) {
        // Background calculation in progress
        const data = await response.json();
        const partial = data.partial_data || [];
        if (partial.length > 0) {
          setSubordinates(partial);
          setLoading(false); // We have partial data, stop showing skeleton
        }
        const progress = data.progress || 0;
        const total = data.total || 0;
        setCalcProgress({ progress, total });
        
        // Poll again without blocking the UI
        setTimeout(async () => {
          await fetchTeamScores(false);
        }, 10000);
        return; 
      }
      
      if (!response.ok) throw new Error("Gagal mengambil report tim");
      const data = await response.json();
      
      if (data.status === "success") {
        setSubordinates(data.data || []);
        setCalcProgress({ progress: data.data?.length || 0, total: data.data?.length || 0 });
      } else {
        setSubordinates([]);
      }
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
    return Promise.resolve();
  };

  const toggleRow = (userId) => {
    setExpandedRows(prev => ({
      ...prev,
      [userId]: !prev[userId]
    }));
  };

  const handleExportCSV = () => {
    const exportData = subordinates.map(sub => ({
      NIK: sub.nik || "-",
      Nama: sub.full_name,
      Divisi: sub.division || "-",
      "Overall KPI": sub.kpi_scores?.overall || 0,
      "Kehadiran (%)": sub.attendance?.normal_percentage || 0,
      "Terlambat (%)": sub.attendance?.late_percentage || 0,
      "C": sub.pillars?.C?.score || 0,
      "I": sub.pillars?.I?.score || 0,
      "S": sub.pillars?.S?.score || 0,
      "R": sub.pillars?.R?.score || 0,
      "O": sub.pillars?.O?.score || 0,
    }));
    exportToCSV(`Kinerja_Tim_${selectedYear}.csv`, exportData);
  };

  const getLeaderboard = () => {
    return [...subordinates]
      .filter(s => s.kpi_scores && s.kpi_scores.overall > 0)
      .sort((a, b) => b.kpi_scores.overall - a.kpi_scores.overall)
      .slice(0, 3)
      .map(s => ({ name: s.full_name.split(' ')[0], Score: parseFloat(s.kpi_scores.overall.toFixed(1)) }));
  };
  const leaderboard = getLeaderboard();

  // Filter subordinates by search query
  const sortedSubordinates = [...subordinates].sort((a, b) => (b.kpi_scores?.overall || 0) - (a.kpi_scores?.overall || 0));

  const filteredSubs = sortedSubordinates.filter(sub =>
    sub.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (sub.nik && sub.nik.includes(searchQuery))
  );

  // Calculate team summary stats
  const averageTeamScore = subordinates.length > 0
    ? (subordinates.reduce((acc, curr) => acc + (curr.kpi_scores?.overall || 0), 0) / subordinates.length).toFixed(2)
    : "0.00";

  const topPerformer = subordinates.length > 0
    ? [...subordinates].sort((a, b) => (b.kpi_scores?.overall || 0) - (a.kpi_scores?.overall || 0))[0]
    : null;

  // Attendance team averages
  const avgAttendancePct = subordinates.length > 0
    ? (subordinates.reduce((acc, a) => {
      const targetDays = a.period?.day_count || 260;
      const presentDays = a.summary?.total_attendance_days || 0;
      return acc + ((presentDays / targetDays) * 100);
    }, 0) / subordinates.length).toFixed(1)
    : "0.0";

  const avgLatePct = subordinates.length > 0
    ? (subordinates.reduce((acc, a) => {
      const targetDays = a.period?.day_count || 260;
      const lateCount = a.summary?.total_late_count || 0;
      return acc + ((lateCount / targetDays) * 100);
    }, 0) / subordinates.length).toFixed(1)
    : "0.0";

  // Get attendance for a specific user
  const getAttendanceForUser = (userId) => {
    const sub = subordinates.find(a => a.user_id === userId);
    if (!sub) return null;
    const targetDays = sub.period?.day_count || 260;
    const presentDays = sub.summary?.total_attendance_days || 0;
    const lateCount = sub.summary?.total_late_count || 0;
    return {
      attendance_days: presentDays,
      target_days: targetDays,
      late_count: lateCount,
      late_percentage: (lateCount / targetDays) * 100
    };
  };

  // Late badge class
  const getLateBadgeClass = (pct) => {
    if (pct >= 30) return "badge-danger";
    if (pct >= 15) return "badge-warning";
    return "badge-success";
  };

  const handleEmailChange = (userId, value) => {
    setEditingEmails(prev => ({
      ...prev,
      [userId]: value
    }));
  };

  const handleSaveEmail = async (userId) => {
    const emailVal = editingEmails[userId] !== undefined ? editingEmails[userId] : "";
    setEmailSaving(prev => ({ ...prev, [userId]: true }));
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/users/${userId}/email`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ email: emailVal })
      });
      if (!response.ok) throw new Error("Gagal mengupdate email");
      
      // Update local subordinates list
      setSubordinates(prev => prev.map(s => s.user_id === userId ? { ...s, email: emailVal } : s));
      toast.success("Email berhasil disimpan!");
    } catch (err) {
      toast.error("Gagal menyimpan email: " + err.message);
    } finally {
      setEmailSaving(prev => ({ ...prev, [userId]: false }));
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

  // Precise, locale-aware number formatting (id-ID)
  const fmt = (n, digits = 0) =>
    Number(n || 0).toLocaleString("id-ID", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });

  if (selectedSubId) {
    return (
      <div>
        <button
          className="btn-outline"
          onClick={() => { setSelectedSubId(null); if (onResetTarget) onResetTarget(); }}
          style={{ marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}
        >
          <ArrowLeft size={16} /> Kembali ke Daftar Tim
        </button>
        <Dashboard userId={selectedSubId} isSelf={false} />
      </div>
    );
  }

  return (
    <div>
      <div className="header-ui">
        <div>
          <span className="hero-eyebrow">Team Oversight</span>
          <h2>Hierarki Tim & Subordinat</h2>
          <p style={{ color: "var(--color-text-muted)", fontSize: "14px", margin: 0 }}>
            Kelola dan evaluasi KPI dari seluruh anggota tim di bawah kendali Anda.
          </p>
          <div className="status-strip">
            <span className={`status-pill ${syncStatus.is_syncing ? "syncing" : "live"}`}>
              <RefreshCw size={11} className={syncStatus.is_syncing ? "animate-spin" : ""} />
              {syncStatus.is_syncing ? "Sinkronisasi berjalan" : "Data terbaru"}
            </span>
            {calcProgress.total > 0 && calcProgress.progress < calcProgress.total && (
              <span className="status-pill syncing">
                <RefreshCw size={11} className="animate-spin" />
                Menghitung KPI {calcProgress.progress}/{calcProgress.total}
              </span>
            )}
            <span>Terakhir diperbarui: <strong>{formatLastSyncTime()}</strong></span>
            <span className="table-meta">· otomatis setiap {syncStatus.sync_interval_minutes} menit</span>
          </div>
        </div>

        <div className="filter-group" style={{ display: "flex", gap: "10px", alignItems: "flex-end", justifyContent: "flex-end" }}>
          <button
            className="btn-outline"
            onClick={handleExportCSV}
            title="Download Laporan CSV"
            style={{ display: "flex", alignItems: "center", gap: "6px", padding: "0 16px", height: "48px", fontSize: "12px", fontWeight: 600 }}
          >
            <Download size={13} />
            Export CSV
          </button>
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
          <button
            className="btn-outline"
            onClick={handleExportCSV}
            title="Download Laporan CSV"
            style={{ display: "flex", alignItems: "center", gap: "6px", padding: "0 16px", height: "48px", fontSize: "12px", fontWeight: 600 }}
          >
            <Download size={13} />
            Export CSV
          </button>
          <button
            className={attendanceSyncing ? "btn-outline" : "btn-primary"}
            onClick={() => syncAttendanceForYear(selectedYear)}
            disabled={attendanceSyncing}
            title="Sinkronisasi data kehadiran dari HRIS untuk seluruh anggota tim"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "0 16px",
              height: "48px",
              fontSize: "12px",
              fontWeight: 600,
              whiteSpace: "nowrap",
              width: "auto"
            }}
          >
            <RefreshCw size={13} className={attendanceSyncing ? "animate-spin" : ""} />
            {attendanceSyncing ? "Menyinkronkan..." : "Sync Attendance"}
          </button>
        </div>
      </div>

      {/* Leaderboard Section */}
      {leaderboard.length > 0 && (
        <div className="card" style={{ marginBottom: "var(--space-6)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
            <Crown size={18} style={{ color: "#8b5cf6" }} />
            <h3 style={{ margin: 0, fontSize: "var(--text-lg)", fontWeight: 700 }}>Top Performers Tim</h3>
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
      )}

      {/* Team Aggregated Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card ui-tooltip" data-metric-desc="Rata-rata weighted score seluruh anggota tim aktif untuk tahun terpilih.">
          <div className="stat-icon" style={{ background: "linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)", color: "#15803d" }}>
            <BarChart2 size={24} />
          </div>
          <div className="stat-info">
            <h4 className="num">{fmt(averageTeamScore, 2)}</h4>
            <p>Average Team Score</p>
          </div>
        </div>

        <div className="stat-card ui-tooltip" data-metric-desc="Jumlah anggota tim aktif yang tercatat di bawah kendali Anda.">
          <div className="stat-icon" style={{ background: "linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)", color: "#0369a1" }}>
            <Users size={24} />
          </div>
          <div className="stat-info">
            <h4 className="num">{fmt(subordinates.length)} <span style={{ fontSize: "14px", fontWeight: 500 }}>Orang</span></h4>
            <p>Total Anggota Tim</p>
          </div>
        </div>

        {/* Attendance Team Stat */}
        <div className="stat-card ui-tooltip" data-metric-desc="Rata-rata rasio kehadiran (hari hadir / target hari kerja) seluruh anggota tim.">
          <div className="stat-icon" style={{ background: "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)", color: "#166534" }}>
            <UserCheck size={24} />
          </div>
          <div className="stat-info">
            <h4 className="num">{fmt(avgAttendancePct, 1)}%</h4>
            <p>Avg Kehadiran Tim</p>
          </div>
        </div>

        {/* Late Percentage Team Stat */}
        <div className="stat-card ui-tooltip" data-metric-desc="Rata-rata persentase keterlambatan untuk periode terpilih (GOOD &lt;15%).">
          <div className="stat-icon" style={{ background: parseFloat(avgLatePct) >= 20 ? "linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)" : "linear-gradient(135deg, #fef9c3 0%, #fef08a 100%)", color: parseFloat(avgLatePct) >= 20 ? "#b91c1c" : "#a16207" }}>
            <Clock size={24} />
          </div>
          <div className="stat-info">
            <h4 style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span className="num">{fmt(avgLatePct, 1)}%</span>
              <span className={`badge ${getLateBadgeClass(parseFloat(avgLatePct))}`} style={{ fontSize: "9px" }}>
                {parseFloat(avgLatePct) >= 30 ? "CRITICAL" : parseFloat(avgLatePct) >= 15 ? "WARNING" : "GOOD"}
              </span>
            </h4>
            <p>Avg Keterlambatan Tim</p>
          </div>
        </div>

        <div className="stat-card ui-tooltip" data-metric-desc="Anggota dengan weighted score tertinggi pada periode terpilih." style={{ gridColumn: "span 2" }}>
          <div className="stat-icon" style={{ background: "linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)", color: "#b91c1c" }}>
            <Award size={24} />
          </div>
          <div className="stat-info">
            <h4 style={{ fontSize: "20px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {topPerformer ? topPerformer.full_name : "N/A"}
            </h4>
            <p>Top Performer ({fmt(topPerformer?.final_score || 0, 2)} poin)</p>
          </div>
        </div>
      </div>

      {/* Search and Table Container */}
      <div className="card" style={{ padding: "30px 0" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 30px 24px", borderBottom: "1px solid #f1f5f9" }}>
          <div style={{ position: "relative", width: "100%", maxWidth: "340px" }}>
            <Search size={18} style={{ position: "absolute", left: "16px", top: "14px", color: "var(--color-text-muted)" }} />
            <input
              type="text"
              placeholder="Cari nama atau NIK karyawan..."
              className="form-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Cari anggota tim"
              style={{ paddingLeft: "48px" }}
            />
          </div>
          <span className="text-sm text-muted" style={{ fontWeight: 600 }}>
            Menampilkan {filteredSubs.length} dari {subordinates.length} Karyawan
          </span>
        </div>

        <div className="table-container">
          <table className="custom-table">
            <thead>
              <tr>
                <th style={{ width: "40px" }}></th>
                <th>Nama Karyawan</th>
                <th>NIK</th>
                <th>Role</th>
                <th data-align="right">Hadir</th>
                <th data-align="right">Telat</th>
                <th data-align="right">Late %</th>
                <th data-align="right">KPI Score</th>
                <th>Tindakan</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="9" style={{ padding: 0 }}>
                    <div style={{ padding: "32px", display: "flex", alignItems: "center", justifyContent: "center", gap: "16px" }}>
                      <RefreshCw className="animate-spin" size={20} style={{ color: "var(--color-secondary)" }} />
                      <span className="text-sm text-muted">Memuat daftar anggota tim...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredSubs.length === 0 && !loading ? (
                <tr>
                  <td colSpan="9">
                    <div className="empty-state">
                      <div className="empty-icon"><Search size={24} /></div>
                      <h4>{subordinates.length === 0 ? "Belum Ada Anggota Tim" : "Tidak Ada Hasil Pencarian"}</h4>
                      <p>
                        {subordinates.length === 0
                          ? "Anggota tim akan muncul otomatis setelah data diperbarui dari HRIS."
                          : `Tidak ada anggota tim yang cocok dengan kata kunci "${searchQuery}".`}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredSubs.map(sub => {
                  const attInfo = getAttendanceForUser(sub.user_id);
                  const isExpanded = !!expandedRows[sub.user_id];
                  const scoreInfo = sub.kpi_scores || {};

                  return (
                    <React.Fragment key={sub.user_id}>
                      <tr>
                        <td>
                          <button
                            onClick={() => toggleRow(sub.user_id)}
                            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-primary)" }}
                          >
                            {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                          </button>
                        </td>
                        <td style={{ fontWeight: 700, color: "var(--color-primary)" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            {sub.full_name}
                            {!sub.email && (
                              <span className="badge" style={{ background: "#fef08a", color: "#a16207", display: "flex", alignItems: "center", gap: "4px", fontSize: "10px", padding: "2px 6px" }}>
                                <AlertTriangle size={10} /> Email Required
                              </span>
                            )}
                          </div>
                        </td>
                        <td>{sub.nik}</td>
                        <td>
                          <span className="badge badge-primary">
                            Bawahan
                          </span>
                        </td>
                        <td data-align="right" className="num">
                          {attInfo ? (
                            <span style={{ fontWeight: 700, color: "#15803d" }}>
                              {fmt(attInfo.attendance_days)}/{fmt(attInfo.target_days)}
                            </span>
                          ) : (
                            <span style={{ color: "var(--color-text-muted)" }}>—</span>
                          )}
                        </td>
                        <td data-align="right" className="num">
                          {attInfo ? (
                            <span style={{ fontWeight: 700, color: attInfo.late_count > 0 ? "#b91c1c" : "#15803d" }}>
                              {fmt(attInfo.late_count)}x
                            </span>
                          ) : (
                            <span style={{ color: "var(--color-text-muted)" }}>—</span>
                          )}
                        </td>
                        <td data-align="right" className="num">
                          {attInfo ? (
                            <span className={`badge ${getLateBadgeClass(attInfo.late_percentage)}`}>
                              {fmt(attInfo.late_percentage, 1)}%
                            </span>
                          ) : (
                            <span style={{ color: "var(--color-text-muted)" }}>—</span>
                          )}
                        </td>
                        <td data-align="right" className="num" style={{ fontWeight: 800, fontSize: "16px", color: "var(--color-primary)" }}>
                          {scoreInfo.overall !== undefined ? fmt(scoreInfo.overall, 2) : "N/A"}
                        </td>
                        <td>
                          {!sub.email ? (
                            <button
                              className="btn-primary"
                              onClick={() => {
                                setExpandedRows(prev => ({ ...prev, [sub.user_id]: true }));
                              }}
                              style={{ padding: "6px 16px", fontSize: "12px", background: "#f59e0b", borderColor: "#f59e0b", color: "#fff", display: "flex", alignItems: "center", gap: "4px" }}
                            >
                              <AlertTriangle size={14} />
                              Lengkapi Email
                            </button>
                          ) : (
                            <button
                              className="btn-outline"
                              onClick={() => {
                                setSelectedSubId(sub.user_id);
                                setSelectedSubName(sub.full_name);
                              }}
                              style={{ padding: "6px 16px", fontSize: "12px" }}
                            >
                              Lihat Dashboard Detail
                            </button>
                          )}
                        </td>
                      </tr>

                      {/* Expanded row */}
                      {isExpanded && (
                        <tr className="expandable-row">
                          <td colSpan="9" style={{ padding: 0 }}>
                            {/* Summary Detail */}
                            <div style={{ padding: "20px 24px", display: "flex", gap: "24px", borderBottom: "1px solid #f1f5f9", alignItems: "stretch", flexWrap: "wrap" }}>
                              <div className="stat-card" style={{ flex: "1 1 220px", minHeight: "90px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
                                <span className="metric-label" style={{ marginBottom: 8 }}>Jira Completed</span>
                                <div style={{ display: "flex", alignItems: "baseline", gap: 8, margin: 0 }}>
                                  <span className="metric-value">{fmt(sub.summary?.total_issues_completed || 0)}</span>
                                  <span className="table-meta">tiket · {fmt(sub.summary?.total_story_points || 0)} pts</span>
                                </div>
                              </div>
                              <div className="stat-card" style={{ flex: "3 1 450px", minHeight: "90px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
                                <h4 style={{ fontSize: "12px", fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "8px" }}>Email Kantor (untuk Sinkronisasi Git/Jira)</h4>
                                <div style={{ display: "flex", gap: "10px", alignItems: "center", width: "100%" }}>
                                  <div style={{ position: "relative", flex: 1, minWidth: "220px" }}>
                                    <Mail size={16} style={{ position: "absolute", left: "12px", top: "11px", color: "#94a3b8" }} />
                                    <input
                                      type="email"
                                      placeholder="nama.karyawan@atibusinessgroup.com"
                                      className="form-input"
                                      required
                                      value={editingEmails[sub.user_id] !== undefined ? editingEmails[sub.user_id] : (sub.email || "")}
                                      onChange={(e) => handleEmailChange(sub.user_id, e.target.value)}
                                      style={{ 
                                        fontSize: "14px", 
                                        height: "38px", 
                                        width: "100%",
                                        paddingLeft: "36px", 
                                        borderRadius: "6px", 
                                        border: !sub.email ? "2px solid #f59e0b" : "1px solid #cbd5e1",
                                        backgroundColor: !sub.email ? "#fefce8" : "#f8fafc",
                                        transition: "all 0.2s"
                                      }}
                                    />
                                  </div>
                                  <button
                                    className="btn-primary"
                                    onClick={() => handleSaveEmail(sub.user_id)}
                                    disabled={emailSaving[sub.user_id]}
                                    style={{ 
                                      width: "auto", 
                                      padding: "0 18px", 
                                      height: "38px", 
                                      fontSize: "12px", 
                                      fontWeight: 600,
                                      borderRadius: "6px",
                                      display: "flex", 
                                      alignItems: "center", 
                                      justifyContent: "center",
                                      whiteSpace: "nowrap"
                                    }}
                                  >
                                    {emailSaving[sub.user_id] ? "Menyimpan..." : "Simpan Email"}
                                  </button>
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
