import React, { useState, useEffect } from "react";
import { 
  Users, Search, ArrowLeft, ChevronDown, ChevronUp, BarChart2, Award, Info, 
  Clock, UserCheck, AlertTriangle, RefreshCw, Mail, Filter, Calendar 
} from "lucide-react";
import Dashboard from "./Dashboard.enhanced";

export default function Subordinates({ supervisorId }) {
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
    if (supervisorId && mounted) {
      fetchTeamScores();
    }
  }, [supervisorId, selectedYear, mounted]);

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
      console.log("[Attendance Sync]", data.message);
      
      if (data.job_id) {
        const poll = setInterval(async () => {
          try {
            const statusRes = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/jobs/${data.job_id}`);
            if (statusRes.ok) {
              const statusData = await statusRes.json();
              if (statusData.status === "COMPLETED" || statusData.status === "FAILED") {
                clearInterval(poll);
                await fetchTeamScores();
                setAttendanceSyncing(false);
              }
            }
          } catch (e) {
            console.error("Error polling job status:", e);
          }
        }, 3000);
      } else {
        setTimeout(async () => {
          await fetchTeamScores();
          setAttendanceSyncing(false);
        }, 3000);
      }
    } catch (err) {
      console.error("[Attendance Sync] Gagal:", err);
      setAttendanceSyncing(false);
    }
  };

  const fetchTeamScores = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/kpi/team-yearly?user_id=${supervisorId}&year=${selectedYear}`, {
        cache: 'no-store'
      });
      if (!response.ok) throw new Error("Gagal mengambil report tim");
      const data = await response.json();
      if (data.status === "success") {
        setSubordinates(data.data || []);
      } else {
        setSubordinates([]);
      }
    } catch (err) {
      console.error(err);
      setSubordinates([]);
    } finally {
      setLoading(false);
    }
  };

  const toggleRow = (userId) => {
    setExpandedRows(prev => ({
      ...prev,
      [userId]: !prev[userId]
    }));
  };

  const filteredSubs = subordinates.filter(sub =>
    sub.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (sub.nik && sub.nik.includes(searchQuery))
  );

  const averageTeamScore = subordinates.length > 0
    ? (subordinates.reduce((acc, curr) => acc + (curr.kpi_scores?.overall || 0), 0) / subordinates.length).toFixed(2)
    : "0.00";

  const topPerformer = subordinates.length > 0
    ? [...subordinates].sort((a, b) => (b.kpi_scores?.overall || 0) - (a.kpi_scores?.overall || 0))[0]
    : null;

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
      
      setSubordinates(prev => prev.map(s => s.user_id === userId ? { ...s, email: emailVal } : s));
    } catch (err) {
      alert("Gagal menyimpan email: " + err.message);
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

  if (selectedSubId) {
    return (
      <div style={{ animation: "fadeIn 0.3s ease-out" }}>
        <button
          className="btn btn-outline"
          onClick={() => setSelectedSubId(null)}
          style={{ marginBottom: "24px", borderRadius: "var(--radius-md)" }}
        >
          <ArrowLeft size={16} /> Kembali ke Daftar Tim
        </button>
        <Dashboard userId={selectedSubId} isSelf={false} />
      </div>
    );
  }

  return (
    <div style={{ animation: "fadeIn 0.4s ease-out" }}>
      {/* Enhanced Header */}
      <div style={{ marginBottom: "32px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
          <div>
            <h1 style={{ 
              fontSize: "32px", 
              marginBottom: "8px", 
              background: "var(--gradient-primary)", 
              WebkitBackgroundClip: "text", 
              WebkitTextFillColor: "transparent", 
              backgroundClip: "text" 
            }}>
              Hierarki Tim & Subordinat
            </h1>
            <p style={{ color: "var(--color-text-muted)", fontSize: "14px", fontWeight: "500" }}>
              Kelola dan evaluasi KPI dari seluruh anggota tim di bawah kendali Anda.
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
                Data tim disinkronisasi: <strong style={{ color: "var(--color-primary)" }}>{formatLastSyncTime()}</strong>
              </span>
              <span style={{ color: "var(--color-text-light)", fontSize: "11px" }}>(otomatis setiap {syncStatus.sync_interval_minutes} menit)</span>
            </div>
          </div>

          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
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
            <button
              className={`btn ${attendanceSyncing ? "btn-outline" : "btn-primary"}`}
              onClick={() => syncAttendanceForYear(selectedYear)}
              disabled={attendanceSyncing}
              title="Sinkronisasi data kehadiran dari HRIS untuk seluruh anggota tim"
              style={{ 
                minWidth: "160px",
                borderRadius: "var(--radius-md)" 
              }}
            >
              <RefreshCw size={14} className={attendanceSyncing ? "animate-spin" : ""} />
              {attendanceSyncing ? "Menyinkronkan..." : "Sync Attendance"}
            </button>
          </div>
        </div>
      </div>

      {/* Enhanced Team Stats Cards */}
      <div className="stats-grid-premium">
        <div className="stat-card-premium animate-slide-up" style={{ animationDelay: "0.1s" }}>
          <div className="stat-icon-premium" style={{ 
            background: "linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)", 
            color: "#15803d" 
          }}>
            <BarChart2 size={24} />
          </div>
          <div className="stat-info">
            <h4>{averageTeamScore}</h4>
            <p>Average Team Score</p>
          </div>
        </div>

        <div className="stat-card-premium animate-slide-up" style={{ animationDelay: "0.2s" }}>
          <div className="stat-icon-premium" style={{ 
            background: "linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)", 
            color: "#0369a1" 
          }}>
            <Users size={24} />
          </div>
          <div className="stat-info">
            <h4>{subordinates.length} Orang</h4>
            <p>Total Anggota Tim</p>
          </div>
        </div>

        <div className="stat-card-premium animate-slide-up" style={{ animationDelay: "0.3s" }}>
          <div className="stat-icon-premium" style={{ 
            background: "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)", 
            color: "#166534" 
          }}>
            <UserCheck size={24} />
          </div>
          <div className="stat-info">
            <h4>{avgAttendancePct}%</h4>
            <p>Avg Kehadiran Tim</p>
          </div>
        </div>

        <div className="stat-card-premium animate-slide-up" style={{ animationDelay: "0.4s" }}>
          <div className="stat-icon-premium" style={{ 
            background: parseFloat(avgLatePct) >= 20 
              ? "linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)" 
              : "linear-gradient(135deg, #fef9c3 0%, #fef08a 100%)", 
            color: parseFloat(avgLatePct) >= 20 ? "#b91c1c" : "#a16207" 
          }}>
            <Clock size={24} />
          </div>
          <div className="stat-info">
            <h4 style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {avgLatePct}%
              <span className={`badge-premium ${getLateBadgeClass(parseFloat(avgLatePct))}`} style={{ fontSize: "9px" }}>
                {parseFloat(avgLatePct) >= 30 ? "CRITICAL" : parseFloat(avgLatePct) >= 15 ? "WARNING" : "GOOD"}
              </span>
            </h4>
            <p>Avg Keterlambatan Tim</p>
          </div>
        </div>

        <div className="stat-card-premium animate-slide-up" style={{ 
          gridColumn: "span 2", 
          animationDelay: "0.5s" 
        }}>
          <div className="stat-icon-premium" style={{ 
            background: "linear-gradient(135deg, #fef9c3 0%, #fde047 100%)", 
            color: "#a16207" 
          }}>
            <Award size={24} />
          </div>
          <div className="stat-info">
            <h4>{topPerformer ? topPerformer.full_name : "N/A"}</h4>
            <p>Top Performer {topPerformer ? `(${topPerformer.final_score})` : ""}</p>
          </div>
        </div>
      </div>

      {/* Enhanced Team Table */}
      <div className="card-premium animate-slide-up" style={{ animationDelay: "0.6s", padding: 0 }}>
        {/* Enhanced Search and Filters */}
        <div className="data-table-header">
          <div style={{ display: "flex", gap: "16px", alignItems: "center", flex: 1 }}>
            <div className="search-container-premium" style={{ maxWidth: "360px" }}>
              <Search size={18} className="search-icon-premium" />
              <input
                type="text"
                placeholder="Cari nama atau NIK karyawan..."
                className="search-input-premium"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="badge-premium badge-info" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <Filter size={14} />
              <span>Menampilkan {filteredSubs.length} dari {subordinates.length} Karyawan</span>
            </div>
          </div>
          <div className="data-table-actions">
            <button className="btn btn-glass" style={{ fontSize: "13px", padding: "10px 16px" }}>
              <Calendar size={14} /> Export Report
            </button>
          </div>
        </div>

        {/* Enhanced Table */}
        <div className="table-container" style={{ borderRadius: 0 }}>
          <table className="table-premium">
            <thead>
              <tr>
                <th style={{ width: "50px" }}></th>
                <th>Nama Karyawan</th>
                <th>NIK</th>
                <th>Role</th>
                <th>Hadir</th>
                <th>Telat</th>
                <th>Late %</th>
                <th>KPI Score</th>
                <th className="action-cell">Tindakan</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: "center", padding: "60px 40px" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
                      <RefreshCw className="animate-spin" size={40} style={{ color: "var(--color-secondary)" }} />
                      <p style={{ fontSize: "16px", fontWeight: "600", color: "var(--color-text-muted)" }}>
                        Memuat daftar anggota tim...
                      </p>
                    </div>
                  </td>
                </tr>
              ) : filteredSubs.length === 0 ? (
                <tr>
                  <td colSpan="9" style={{ textAlign: "center", padding: "60px 40px" }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
                      <Search size={48} style={{ color: "var(--color-text-light)" }} />
                      <p style={{ fontSize: "16px", fontWeight: "600", color: "var(--color-text-muted)" }}>
                        Tidak ada anggota tim yang cocok dengan pencarian.
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
                      <tr style={{ transition: "background var(--transition-fast)" }}>
                        <td style={{ textAlign: "center" }}>
                          <button
                            onClick={() => toggleRow(sub.user_id)}
                            style={{ 
                              background: "var(--color-tint-light)", 
                              border: "1px solid var(--color-accent)", 
                              cursor: "pointer", 
                              color: "var(--color-primary)",
                              borderRadius: "var(--radius-sm)",
                              padding: "6px",
                              transition: "var(--transition-base)",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center"
                            }}
                            onMouseEnter={(e) => e.target.style.background = "var(--color-accent)"}
                            onMouseLeave={(e) => e.target.style.background = "var(--color-tint-light)"}
                          >
                            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                          </button>
                        </td>
                        <td style={{ fontWeight: 700, color: "var(--color-primary)", fontSize: "14px" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                            <span>{sub.full_name}</span>
                            {!sub.email && (
                              <span className="badge-premium" style={{ 
                                background: "var(--color-warning-light)", 
                                color: "#a16207", 
                                fontSize: "10px",
                                padding: "4px 8px",
                                gap: "4px" 
                              }}>
                                <AlertTriangle size={10} /> Email Required
                              </span>
                            )}
                          </div>
                        </td>
                        <td style={{ fontFamily: "var(--font-mono)", fontSize: "13px", color: "var(--color-text-muted)" }}>
                          {sub.nik}
                        </td>
                        <td>
                          <span className="badge-premium badge-primary" style={{ fontSize: "11px" }}>
                            Bawahan
                          </span>
                        </td>
                        <td>
                          {attInfo ? (
                            <div style={{ 
                              padding: "6px 12px", 
                              background: "var(--color-success-light)", 
                              color: "#15803d", 
                              borderRadius: "var(--radius-full)", 
                              fontWeight: 700,
                              fontSize: "13px",
                              display: "inline-block"
                            }}>
                              {attInfo.attendance_days}/{attInfo.target_days}
                            </div>
                          ) : (
                            <span style={{ color: "var(--color-text-light)" }}>—</span>
                          )}
                        </td>
                        <td>
                          {attInfo ? (
                            <div style={{ 
                              padding: "6px 12px", 
                              background: attInfo.late_count > 0 
                                ? "var(--color-danger-light)" 
                                : "var(--color-success-light)", 
                              color: attInfo.late_count > 0 ? "#b91c1c" : "#15803d", 
                              borderRadius: "var(--radius-full)", 
                              fontWeight: 700,
                              fontSize: "13px",
                              display: "inline-block"
                            }}>
                              {attInfo.late_count}x
                            </div>
                          ) : (
                            <span style={{ color: "var(--color-text-light)" }}>—</span>
                          )}
                        </td>
                        <td>
                          {attInfo ? (
                            <span className={`badge-premium ${getLateBadgeClass(attInfo.late_percentage)}`} style={{ fontSize: "11px" }}>
                              {attInfo.late_percentage.toFixed(1)}%
                            </span>
                          ) : (
                            <span style={{ color: "var(--color-text-light)" }}>—</span>
                          )}
                        </td>
                        <td style={{ fontWeight: 800, fontSize: "18px", color: "var(--color-primary)" }}>
                          {scoreInfo.overall !== undefined ? scoreInfo.overall : "N/A"}
                        </td>
                        <td className="action-cell">
                          {!sub.email ? (
                            <button
                              className="btn btn-primary"
                              onClick={() => {
                                setExpandedRows(prev => ({ ...prev, [sub.user_id]: true }));
                              }}
                              style={{ 
                                padding: "8px 16px", 
                                fontSize: "12px", 
                                background: "linear-gradient(135deg, #f59e0b 0%, #d97706 100%)",
                                borderRadius: "var(--radius-sm)" 
                              }}
                            >
                              <AlertTriangle size={14} /> Lengkapi Email
                            </button>
                          ) : (
                            <button
                              className="btn btn-outline"
                              onClick={() => {
                                setSelectedSubId(sub.user_id);
                                setSelectedSubName(sub.full_name);
                              }}
                              style={{ 
                                padding: "8px 16px", 
                                fontSize: "12px",
                                borderRadius: "var(--radius-sm)" 
                              }}
                            >
                              Lihat Dashboard Detail
                            </button>
                          )}
                        </td>
                      </tr>

                      {/* Enhanced Expanded Row */}
                      {isExpanded && (
                        <tr>
                          <td colSpan="9" style={{ padding: 0, background: "var(--color-bg-light)" }}>
                            <div style={{ 
                              padding: "24px", 
                              display: "flex", 
                              gap: "24px", 
                              borderBottom: "1px solid #e2e8f0", 
                              alignItems: "stretch", 
                              flexWrap: "wrap" 
                            }}>
                              <div className="stat-card-premium" style={{ 
                                flex: "1 1 240px", 
                                minHeight: "100px", 
                                display: "flex", 
                                flexDirection: "column", 
                                justifyContent: "center",
                                boxShadow: "none",
                                border: "1px solid #e2e8f0"
                              }}>
                                <div style={{ 
                                  fontSize: "11px", 
                                  fontWeight: 700, 
                                  color: "var(--color-text-muted)", 
                                  textTransform: "uppercase", 
                                  letterSpacing: "0.05em", 
                                  marginBottom: "8px",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "6px"
                                }}>
                                  <CheckSquare size={12} />
                                  Jira Completed
                                </div>
                                <p style={{ 
                                  fontSize: "24px", 
                                  fontWeight: 800, 
                                  color: "var(--color-primary)", 
                                  margin: 0,
                                  background: "var(--gradient-primary)",
                                  WebkitBackgroundClip: "text",
                                  WebkitTextFillColor: "transparent",
                                  backgroundClip: "text"
                                }}>
                                  {sub.summary?.total_issues_completed || 0} <span style={{ 
                                    fontSize: "14px", 
                                    fontWeight: 500, 
                                    color: "var(--color-text-muted)",
                                    WebkitTextFillColor: "var(--color-text-muted)"
                                  }}> Tiket</span>
                                  <span style={{ 
                                    fontSize: "13px", 
                                    fontWeight: 500, 
                                    color: "var(--color-text-light)",
                                    WebkitTextFillColor: "var(--color-text-light)",
                                    marginLeft: "8px" 
                                  }}>({sub.summary?.total_story_points || 0} Pts)</span>
                                </p>
                              </div>
                              <div className="stat-card-premium" style={{ 
                                flex: "3 1 480px", 
                                minHeight: "100px", 
                                display: "flex", 
                                flexDirection: "column", 
                                justifyContent: "center",
                                boxShadow: "none",
                                border: "1px solid #e2e8f0"
                              }}>
                                <div style={{ 
                                  fontSize: "11px", 
                                  fontWeight: 700, 
                                  color: "var(--color-text-muted)", 
                                  textTransform: "uppercase", 
                                  letterSpacing: "0.05em", 
                                  marginBottom: "8px",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "6px"
                                }}>
                                  <Mail size={12} />
                                  Email Kantor (untuk Sinkronisasi Git/Jira)
                                </div>
                                <div style={{ display: "flex", gap: "12px", alignItems: "center", width: "100%" }}>
                                  <div style={{ position: "relative", flex: 1, minWidth: "240px" }}>
                                    <Mail size={16} style={{ 
                                      position: "absolute", 
                                      left: "14px", 
                                      top: "50%", 
                                      transform: "translateY(-50%)", 
                                      color: "var(--color-text-light)" 
                                    }} />
                                    <input
                                      type="email"
                                      placeholder="nama.karyawan@atibusinessgroup.com"
                                      className="form-input-premium"
                                      required
                                      value={editingEmails[sub.user_id] !== undefined ? editingEmails[sub.user_id] : (sub.email || "")}
                                      onChange={(e) => handleEmailChange(sub.user_id, e.target.value)}
                                      style={{ 
                                        paddingLeft: "42px", 
                                        height: "44px",
                                        borderRadius: "var(--radius-md)",
                                        border: !sub.email ? "2px solid #f59e0b" : "2px solid #e2e8f0",
                                        backgroundColor: !sub.email ? "#fefce8" : "var(--color-card-bg)",
                                        transition: "var(--transition-base)",
                                        fontSize: "14px"
                                      }}
                                      onFocus={(e) => e.target.style.borderColor = "var(--color-secondary)"}
                                      onBlur={(e) => e.target.style.borderColor = !sub.email ? "#f59e0b" : "#e2e8f0"}
                                    />
                                  </div>
                                  <button
                                    className="btn btn-primary"
                                    onClick={() => handleSaveEmail(sub.user_id)}
                                    disabled={emailSaving[sub.user_id]}
                                    style={{ 
                                      padding: "0 20px", 
                                      height: "44px", 
                                      fontSize: "13px", 
                                      fontWeight: 600,
                                      borderRadius: "var(--radius-md)",
                                      minWidth: "140px"
                                    }}
                                  >
                                    {emailSaving[sub.user_id] ? (
                                      <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                        <span className="spinner-premium"></span> Menyimpan...
                                      </span>
                                    ) : "Simpan Email"}
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