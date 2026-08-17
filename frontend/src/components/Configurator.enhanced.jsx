import React, { useState, useEffect } from "react";
import { 
  Settings, Play, CheckCircle, RefreshCw, AlertCircle, Plus, Trash2, 
  Globe, Server, Info, Code, Database, Zap, Shield 
} from "lucide-react";

export default function Configurator() {
  const [activeSubTab, setActiveSubTab] = useState("rules");

  const [ruleId, setRuleId] = useState("");
  const [name, setName] = useState("");
  const [metrics, setMetrics] = useState([]);
  const [sprints, setSprints] = useState([]);
  const [divisions, setDivisions] = useState([]);
  const [selectedDivisionId, setSelectedDivisionId] = useState("");
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [currentUser, setCurrentUser] = useState({});

  const [jiraUrl, setJiraUrl] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraToken, setJiraToken] = useState("");
  const [jiraBoardId, setJiraBoardId] = useState("");
  const [jiraSpField, setJiraSpField] = useState("customfield_10016");
  const [gitlabUrl, setGitlabUrl] = useState("https://gitlab.com");
  const [gitlabToken, setGitlabToken] = useState("");

  const [testFormula, setTestFormula] = useState("min((complexity_sp / target_complexity_pts) * 100, 100)");
  const [testContextJson, setTestContextJson] = useState('{\n  "complexity_sp": 150,\n  "target_complexity_pts": 300,\n  "attendance_days": 240,\n  "target_days": 261,\n  "late_percentage": 5\n}');
  const [testResult, setTestResult] = useState(null);
  const [showGuide, setShowGuide] = useState(false);

  const [saveLoading, setSaveLoading] = useState(false);
  const [calcLoading, setCalcLoading] = useState(false);
  const [testLoading, setTestLoading] = useState(false);
  const [integLoading, setIntegLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetchSprints();
    const storedUser = JSON.parse(localStorage.getItem("kpi_user") || "{}");
    setCurrentUser(storedUser);
    if (storedUser.division_id) {
      setSelectedDivisionId(storedUser.division_id);
    }
    if (storedUser.group_id) {
      setSelectedGroupId(storedUser.group_id);
    }
    fetchDivisions(storedUser.division_id);
    fetchIntegrations();
  }, []);

  useEffect(() => {
    if (selectedDivisionId && mounted) {
      fetchRulesForDivision(selectedDivisionId, selectedGroupId);
    }
  }, [selectedDivisionId, selectedGroupId, mounted]);

  const fetchSprints = async () => {
    try {
      const response = await fetch(import.meta.env.VITE_API_URL + "/api/v1/sprints");
      const list = await response.json();
      setSprints(list);
    } catch (err) {
      console.error("Gagal mengambil data sprint:", err);
    }
  };

  const fetchDivisions = async (userDivId) => {
    try {
      const divRes = await fetch(import.meta.env.VITE_API_URL + "/api/v1/divisions");
      const list = await divRes.json();
      setDivisions(list);
      if (list.length > 0 && !userDivId) {
        const initialDiv = list.find(d => d.code === "IT")?.id || list[0].id;
        setSelectedDivisionId(initialDiv);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchRulesForDivision = async (divId, groupId) => {
    try {
      const divRes = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/divisions`);
      const divList = await divRes.json();
      const selectedDiv = divList.find(d => d.id === divId) || { name: "New Division", code: "" };

      let url = `${import.meta.env.VITE_API_URL}/api/v1/kpi-rules?division_id=${divId}`;
      if (groupId) {
        url += `&group_id=${groupId}`;
      }
      
      const ruleRes = await fetch(url);
      const data = await ruleRes.json();
      
      if (data && data.rule_id) {
        setRuleId(data.rule_id);
        const isDigitalSolutionGroup = currentUser && currentUser.group_name === "Digital Solution Development";
        
        if (isDigitalSolutionGroup && data.metrics && (!data.metrics.some(m => m.metric_key === "feature_complexity"))) {
          setName("Digital Solution Developer KPI Matrix");
          setMetrics([
            { metric_key: "feature_complexity", category: "ENGINEERING", weight: 0.90, calc_type: "FORMULA", formula_expression: "min((complexity_sp / target_complexity_pts) * 100, 100)", variables: { target_complexity_pts: 300, max_c: 5, max_i: 5, max_s: 5, max_r: 3, max_o: 2 }, cap_score: 100.0 },
            { metric_key: "attendance", category: "DISCIPLINE", weight: 0.10, calc_type: "FORMULA", formula_expression: "max((attendance_days / target_days) * 100 - (late_percentage * 0.5), 0)", variables: { target_days: 261, late_percentage: 5 }, cap_score: 100.0 }
          ]);
        } else {
          setName(data.name);
          setMetrics(data.metrics);
        }
      } else {
        const isDigitalSolutionGroup = currentUser && currentUser.group_name === "Digital Solution Development";
        if (isDigitalSolutionGroup) {
          setName("Digital Solution Developer KPI Matrix");
          setMetrics([
            { metric_key: "feature_complexity", category: "ENGINEERING", weight: 0.90, calc_type: "FORMULA", formula_expression: "min((complexity_sp / target_complexity_pts) * 100, 100)", variables: { target_complexity_pts: 300, max_c: 5, max_i: 5, max_s: 5, max_r: 3, max_o: 2 }, cap_score: 100.0 },
            { metric_key: "attendance", category: "DISCIPLINE", weight: 0.10, calc_type: "FORMULA", formula_expression: "max((attendance_days / target_days) * 100 - (late_percentage * 0.5), 0)", variables: { target_days: 261, late_percentage: 5 }, cap_score: 100.0 }
          ]);
        } else {
          setName(`${selectedDiv.name} KPI Matrix`);
          setMetrics([
            { metric_key: "attendance", category: "EFFORT", weight: 1.00, calc_type: "FORMULA", formula_expression: "max((attendance_days / target_days) * 100 - (late_percentage * 0.5), 0)", variables: { target_days: 261, late_percentage: 5 }, cap_score: 100.0 }
          ]);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchIntegrations = async () => {
    try {
      const response = await fetch(import.meta.env.VITE_API_URL + "/api/v1/integrations");
      if (response.ok) {
        const data = await response.json();
        setJiraUrl(data.jira_url || "");
        setJiraEmail(data.jira_email || "");
        setJiraToken(data.jira_token || "");
        setJiraBoardId(data.jira_board_id || "");
        setJiraSpField(data.jira_sp_field || "customfield_10016");
        setGitlabUrl(data.gitlab_url || "https://gitlab.com");
        setGitlabToken(data.gitlab_token || "");
      }
    } catch (err) {
      console.error("Gagal memuat kredensial integrasi:", err);
    }
  };

  const handleMetricChange = (idx, field, value) => {
    const updated = [...metrics];
    if (field === "variables") {
      try {
        updated[idx][field] = JSON.parse(value);
      } catch (e) {
        updated[idx][field + "_raw"] = value;
        return;
      }
    } else {
      updated[idx][field] = value;
    }
    setMetrics(updated);
  };

  const addMetricRow = () => {
    setMetrics([
      ...metrics,
      { metric_key: "new_metric", category: "ENGINEERING", weight: 0.10, calc_type: "FORMULA", formula_expression: "input * 10", variables: {}, cap_score: 100.0 }
    ]);
  };

  const removeMetricRow = (idx) => {
    setMetrics(metrics.filter((_, i) => i !== idx));
  };

  const handleSaveRules = async () => {
    setSaveLoading(true);
    setMessage(null);
    try {
      const totalWeight = metrics.reduce((acc, curr) => acc + parseFloat(curr.weight), 0);
      if (totalWeight < 0.99 || totalWeight > 1.01) {
        throw new Error(`Total bobot harus bernilai 100% (1.0). Saat ini: ${(totalWeight * 100).toFixed(0)}%`);
      }
      
      const response = await fetch(import.meta.env.VITE_API_URL + "/api/v1/kpi-rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          division_id: selectedDivisionId,
          group_id: selectedGroupId || null,
          group_name: currentUser.group_name || null,
          name: name,
          metrics: metrics
        })
      });

      if (!response.ok) throw new Error("Gagal menyimpan aturan");
      const data = await response.json();
      setMessage({ type: "success", text: `Aturan berhasil diperbarui ke Versi ${data.version}!` });
      fetchRulesForDivision(selectedDivisionId);
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setSaveLoading(false);
    }
  };

  const handleSaveIntegrations = async (e) => {
    e.preventDefault();
    setIntegLoading(true);
    setMessage(null);
    try {
      const response = await fetch(import.meta.env.VITE_API_URL + "/api/v1/integrations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jira_url: jiraUrl,
          jira_email: jiraEmail,
          jira_token: jiraToken,
          jira_board_id: jiraBoardId,
          jira_sp_field: jiraSpField,
          gitlab_url: gitlabUrl,
          gitlab_token: gitlabToken
        })
      });

      if (!response.ok) throw new Error("Gagal menyimpan integrasi");
      const data = await response.json();
      setMessage({ type: "success", text: data.message });
      fetchIntegrations();
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setIntegLoading(false);
    }
  };

  const handleTestFormula = async () => {
    setTestLoading(true);
    setTestResult(null);
    try {
      let parsedContext = {};
      try {
        parsedContext = JSON.parse(testContextJson);
      } catch (e) {
        throw new Error("Format JSON Test Input tidak valid.");
      }

      const response = await fetch(import.meta.env.VITE_API_URL + "/api/v1/kpi/evaluate-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          formula: testFormula,
          context: parsedContext
        })
      });
      const data = await response.json();
      if (data.status === "success") {
        setTestResult({ success: true, value: data.result });
      } else {
        setTestResult({ success: false, error: data.message });
      }
    } catch (err) {
      setTestResult({ success: false, error: err.message });
    } finally {
      setTestLoading(false);
    }
  };

  const handleCalculateYear = async () => {
    setCalcLoading(true);
    setMessage(null);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/sync/year/${selectedYear}`, {
        method: "POST"
      });
      if (!response.ok) throw new Error("Gagal menjalankan kalkulasi");
      const data = await response.json();
      setMessage({
        type: "success",
        text: `Kalkulasi & Sinkronisasi selesai! Berhasil memperbarui data dari Jira/GitLab untuk tahun ${selectedYear}.`
      });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setCalcLoading(false);
    }
  };

  return (
    <div style={{ animation: "fadeIn 0.4s ease-out" }}>
      {/* Enhanced Header */}
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ 
          fontSize: "32px", 
          marginBottom: "8px", 
          background: "var(--gradient-primary)", 
          WebkitBackgroundClip: "text", 
          WebkitTextFillColor: "transparent", 
          backgroundClip: "text",
          display: "flex",
          alignItems: "center",
          gap: "12px"
        }}>
          <Settings size={32} style={{ 
            color: "var(--color-secondary)",
            WebkitTextFillColor: "var(--color-secondary)"
          }} />
          Matriks Configurator & Rule Builder
        </h1>
        <p style={{ color: "var(--color-text-muted)", fontSize: "14px", fontWeight: "500" }}>
          Tentukan konfigurasi matriks KPI divisi, rumusan formula dinamis, dan koneksi server integrasi.
        </p>
      </div>

      {/* Enhanced Alert Messages */}
      {message && (
        <div className={`alert-premium alert-${message.type}`} style={{ marginBottom: "24px" }}>
          {message.type === "success" ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
          <span style={{ fontWeight: "600" }}>{message.text}</span>
        </div>
      )}

      {/* Enhanced Tab Navigation */}
      <div className="tab-container-premium">
        <button
          className={`tab-premium ${activeSubTab === "rules" ? "active" : ""}`}
          onClick={() => { setActiveSubTab("rules"); setMessage(null); }}
        >
          <Settings size={16} style={{ display: "inline", marginRight: "8px" }} />
          KPI Matrix Rules
        </button>
        <button
          className={`tab-premium ${activeSubTab === "integrations" ? "active" : ""}`}
          onClick={() => { setActiveSubTab("integrations"); setMessage(null); }}
        >
          <Globe size={16} style={{ display: "inline", marginRight: "8px" }} />
          Jira & GitLab Integrations
        </button>
      </div>

      {activeSubTab === "rules" ? (
        <>
          {/* Enhanced Sync Trigger Card */}
          <div className="card-premium" style={{ 
            background: "linear-gradient(135deg, var(--color-tint-light) 0%, rgba(255,255,255,1) 100%)", 
            borderColor: "var(--color-accent)",
            marginBottom: "24px"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <h3 style={{ 
                  marginBottom: "8px", 
                  fontSize: "18px", 
                  fontWeight: "700", 
                  color: "var(--color-primary)",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px"
                }}>
                  <Zap size={20} style={{ color: "var(--color-secondary)" }} />
                  Trigger Sync & Kalkulasi Tahunan
                </h3>
                <p style={{ fontSize: "13px", color: "var(--color-text-muted)", marginBottom: "20px", lineHeight: "1.6" }}>
                  Jalankan sinkronisasi langsung untuk menarik data dari Jira/GitLab kantor, memproses formula, dan meng-update dashboard untuk satu tahun penuh.
                </p>
                <div style={{ display: "flex", gap: "16px", alignItems: "center", flexWrap: "wrap" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <label style={{ fontSize: "11px", fontWeight: "700", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>Pilih Tahun</label>
                    <select
                      style={{
                        padding: "10px 16px",
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
                  <button
                    className="btn btn-primary"
                    onClick={handleCalculateYear}
                    disabled={calcLoading}
                    style={{ marginTop: "18px", padding: "10px 24px", borderRadius: "var(--radius-md)" }}
                  >
                    {calcLoading ? (
                      <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span className="spinner-premium"></span> Memproses...
                      </span>
                    ) : (
                      <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <Play size={16} /> Sync & Hitung KPI Karyawan
                      </span>
                    )}
                  </button>
                </div>
              </div>
              <div style={{ 
                padding: "16px", 
                background: "rgba(64, 89, 198, 0.1)", 
                borderRadius: "var(--radius-lg)",
                border: "1px solid rgba(64, 89, 198, 0.2)",
                display: "flex",
                alignItems: "center",
                gap: "12px"
              }}>
                <Database size={32} style={{ color: "var(--color-secondary)" }} />
                <div>
                  <div style={{ fontSize: "11px", fontWeight: "700", color: "var(--color-text-muted)", textTransform: "uppercase" }}>Data Source</div>
                  <div style={{ fontSize: "14px", fontWeight: "600", color: "var(--color-primary)" }}>Database Lokal</div>
                </div>
              </div>
            </div>
          </div>

          <div className="configurator-grid-premium">

            {/* Enhanced Main Formula Rules Configurator */}
            <div className="configurator-card-premium animate-slide-up" style={{ animationDelay: "0.1s" }}>
              <div style={{ marginBottom: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
                  <div>
                    <h3 style={{ 
                      marginBottom: "8px", 
                      fontSize: "18px", 
                      fontWeight: "700", 
                      color: "var(--color-primary)",
                      display: "flex",
                      alignItems: "center",
                      gap: "10px"
                    }}>
                      <Code size={20} style={{ color: "var(--color-secondary)" }} />
                      Aturan Indikator Divisi / Group
                    </h3>
                    <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
                      <div style={{ 
                        padding: "6px 14px", 
                        background: "rgba(64, 89, 198, 0.1)", 
                        color: "var(--color-primary)", 
                        borderRadius: "var(--radius-full)", 
                        fontSize: "12px", 
                        fontWeight: 700,
                        border: "1px solid rgba(64, 89, 198, 0.2)"
                      }}>
                        {currentUser.group_name || "Tidak ada Group"}
                      </div>
                      <div style={{ 
                        padding: "6px 14px", 
                        background: "#f1f5f9", 
                        color: "var(--color-text-muted)", 
                        borderRadius: "var(--radius-full)", 
                        fontSize: "12px", 
                        fontWeight: 600,
                        border: "1px solid #e2e8f0"
                      }}>
                        {divisions.find(d => d.id === selectedDivisionId)?.name || "Default Divisi"}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button 
                      className="btn btn-glass" 
                      onClick={() => setShowGuide(true)} 
                      style={{ padding: "8px 16px", fontSize: "12px", borderRadius: "var(--radius-md)" }}
                    >
                      <AlertCircle size={14} /> Panduan Formula
                    </button>
                    <button 
                      className="btn btn-outline" 
                      onClick={addMetricRow} 
                      style={{ padding: "8px 16px", fontSize: "12px", borderRadius: "var(--radius-md)" }}
                    >
                      <Plus size={14} /> Tambah Indikator
                    </button>
                  </div>
                </div>

                <div className="form-group-premium">
                  <label className="form-label-premium">Nama Matriks</label>
                  <input
                    type="text"
                    className="form-input-premium"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Contoh: Digital Solution Developer KPI Matrix"
                    style={{ height: "48px" }}
                  />
                </div>
              </div>

              <div className="data-table-container" style={{ marginBottom: "20px" }}>
                <table className="table-premium" style={{ fontSize: "12px" }}>
                  <thead>
                    <tr>
                      <th style={{ width: "140px" }}>Key Indikator</th>
                      <th style={{ width: "90px" }}>Bobot</th>
                      <th>Formula Ekspresi</th>
                      <th style={{ width: "80px" }}>Cap</th>
                      <th>Variables (JSON)</th>
                      <th style={{ width: "60px" }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.map((metric, idx) => (
                      <tr key={idx}>
                        <td>
                          <input
                            type="text"
                            className="form-input-premium"
                            value={metric.metric_key}
                            onChange={(e) => handleMetricChange(idx, "metric_key", e.target.value)}
                            style={{ height: "40px", fontSize: "12px" }}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            step="0.05"
                            min="0"
                            max="1"
                            className="form-input-premium"
                            value={metric.weight}
                            onChange={(e) => handleMetricChange(idx, "weight", e.target.value)}
                            style={{ height: "40px", fontSize: "12px" }}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            className="form-input-premium"
                            value={metric.formula_expression}
                            onChange={(e) => handleMetricChange(idx, "formula_expression", e.target.value)}
                            style={{ 
                              height: "40px", 
                              fontSize: "11px",
                              fontFamily: "var(--font-mono)",
                              minWidth: "280px"
                            }}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            className="form-input-premium"
                            value={metric.cap_score}
                            onChange={(e) => handleMetricChange(idx, "cap_score", e.target.value)}
                            style={{ height: "40px", fontSize: "12px" }}
                          />
                        </td>
                        <td>
                          {metric.metric_key === "feature_complexity" ? (
                            <div style={{ 
                              display: "flex", 
                              flexWrap: "wrap", 
                              gap: "10px", 
                              minWidth: "400px", 
                              background: "var(--color-bg-light)", 
                              padding: "12px", 
                              borderRadius: "var(--radius-md)", 
                              border: "1px solid #e2e8f0" 
                            }}>
                              {[
                                { key: 'max_c', label: 'C (Complexity)' },
                                { key: 'max_i', label: 'I (Impact)' },
                                { key: 'max_s', label: 'S (Scope)' },
                                { key: 'max_r', label: 'R (Risk)' },
                                { key: 'max_o', label: 'O (Ownership)' },
                                { key: 'target_complexity_pts', label: 'Target Pts' }
                              ].map(f => {
                                let varsObj = {};
                                try {
                                  varsObj = typeof metric.variables === 'string' ? JSON.parse(metric.variables) : metric.variables;
                                } catch(e) {}
                                return (
                                  <div key={f.key} style={{ display: "flex", alignItems: "center", gap: "8px", minWidth: "140px" }}>
                                    <label style={{ 
                                      fontSize: "10px", 
                                      fontWeight: "700", 
                                      minWidth: "90px", 
                                      color: "var(--color-text-muted)",
                                      textTransform: "uppercase"
                                    }}>{f.label}:</label>
                                    <input
                                      type="number"
                                      style={{ 
                                        width: "50px", 
                                        fontSize: "11px", 
                                        padding: "6px 8px", 
                                        border: "1px solid #e2e8f0", 
                                        borderRadius: "var(--radius-sm)",
                                        fontWeight: "600"
                                      }}
                                      value={varsObj[f.key] !== undefined ? varsObj[f.key] : ""}
                                      onChange={(e) => {
                                        const newVars = { ...varsObj, [f.key]: parseFloat(e.target.value) || 0 };
                                        handleMetricChange(idx, "variables", JSON.stringify(newVars));
                                      }}
                                    />
                                  </div>
                                );
                              })}
                            </div>
                          ) : (
                            <input
                              type="text"
                              className="form-input-premium"
                              value={typeof metric.variables === 'object' ? JSON.stringify(metric.variables) : metric.variables}
                              onChange={(e) => handleMetricChange(idx, "variables", e.target.value)}
                              style={{ 
                                fontFamily: "var(--font-mono)", 
                                fontSize: "10px",
                                height: "40px",
                                minWidth: "200px"
                              }}
                            />
                          )}
                        </td>
                        <td>
                          <button
                            onClick={() => removeMetricRow(idx)}
                            style={{ 
                              background: "rgba(239, 68, 68, 0.1)", 
                              border: "1px solid rgba(239, 68, 68, 0.2)", 
                              cursor: "pointer", 
                              color: "#ef4444", 
                              padding: "8px",
                              borderRadius: "var(--radius-sm)",
                              transition: "var(--transition-base)",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center"
                            }}
                            onMouseEnter={(e) => {
                              e.target.style.background = "#ef4444";
                              e.target.style.color = "white";
                            }}
                            onMouseLeave={(e) => {
                              e.target.style.background = "rgba(239, 68, 68, 0.1)";
                              e.target.style.color = "#ef4444";
                            }}
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <button
                className="btn btn-primary"
                onClick={handleSaveRules}
                disabled={saveLoading}
                style={{ width: "100%", padding: "14px 24px", borderRadius: "var(--radius-md)" }}
              >
                {saveLoading ? (
                  <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className="spinner-premium"></span> Menyimpan...
                  </span>
                ) : (
                  <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Shield size={16} /> Simpan & Terapkan Perubahan (Buat Versi Baru)
                  </span>
                )}
              </button>
            </div>

            {/* Enhanced Live Formula Tester Side Panel */}
            <div className="configurator-card-premium animate-slide-up" style={{ animationDelay: "0.2s" }}>
              <h3 style={{ 
                marginBottom: "12px", 
                fontSize: "18px", 
                fontWeight: "700", 
                color: "var(--color-primary)",
                display: "flex",
                alignItems: "center",
                gap: "10px"
              }}>
                <Zap size={20} style={{ color: "var(--color-secondary)" }} />
                Live Formula Tester
              </h3>
              <p style={{ fontSize: "13px", color: "var(--color-text-muted)", marginBottom: "20px", lineHeight: "1.6" }}>
                Uji rumus formula matematika Anda dengan input variabel dummy langsung sebelum disimpan.
              </p>

              <div className="form-group-premium">
                <label className="form-label-premium">Formula Uji</label>
                <input
                  type="text"
                  className="form-input-premium"
                  value={testFormula}
                  onChange={(e) => setTestFormula(e.target.value)}
                  style={{ fontFamily: "var(--font-mono)", fontSize: "13px", height: "48px" }}
                  placeholder="min((complexity_sp / target_complexity_pts) * 100, 100)"
                />
              </div>

              <div className="form-group-premium">
                <label className="form-label-premium">Input Context (JSON)</label>
                <textarea
                  className="form-input-premium"
                  value={testContextJson}
                  onChange={(e) => setTestContextJson(e.target.value)}
                  style={{ 
                    height: "160px", 
                    fontFamily: "var(--font-mono)", 
                    padding: "16px", 
                    borderRadius: "var(--radius-lg)", 
                    resize: "none",
                    fontSize: "12px"
                  }}
                />
              </div>

              <button
                className="btn btn-primary"
                onClick={handleTestFormula}
                disabled={testLoading}
                style={{ width: "100%", marginBottom: "20px", padding: "14px 24px", borderRadius: "var(--radius-md)" }}
              >
                {testLoading ? (
                  <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span className="spinner-premium"></span> Menguji...
                  </span>
                ) : (
                  <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <Play size={16} /> Jalankan Simulasi Uji
                  </span>
                )}
              </button>

              {testResult && (
                <div className={`alert-premium ${testResult.success ? "alert-success" : "alert-danger"}`}>
                  {testResult.success ? (
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <CheckCircle size={24} />
                      <div>
                        <div style={{ fontWeight: "700", fontSize: "14px", marginBottom: "4px" }}>Hasil Evaluasi Berhasil</div>
                        <div style={{ fontSize: "20px", fontWeight: "800" }}>Output: {testResult.value}</div>
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                      <AlertCircle size={20} style={{ flexShrink: 0, marginTop: "2px" }} />
                      <div>
                        <div style={{ fontWeight: "700", fontSize: "14px", marginBottom: "6px" }}>Syntax Error / Parsing Gagal</div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "12px", background: "rgba(239, 68, 68, 0.1)", padding: "10px 12px", borderRadius: "var(--radius-sm)" }}>
                          {testResult.error}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Enhanced Guide Card */}
            <div className="configurator-card-premium animate-slide-up" style={{ 
              marginTop: "24px", 
              background: "linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)", 
              border: "1px solid #bae6fd",
              animationDelay: "0.3s"
            }}>
              <h3 style={{ 
                marginBottom: "16px", 
                color: "#0369a1", 
                fontSize: "16px", 
                fontWeight: "700", 
                display: "flex", 
                alignItems: "center", 
                gap: "10px" 
              }}>
                <Info size={20} /> Panduan Menentukan Target Pts
              </h3>
              <div style={{ fontSize: "13px", color: "#334155", lineHeight: "1.7" }}>
                <p style={{ marginBottom: "12px", fontWeight: "600" }}>
                  <strong>Target Pts</strong> adalah benchmark ekspektasi poin kumulatif (C+I+R+S+O) yang harus dicapai karyawan dalam 1 tahun.
                </p>
                <div style={{ 
                  padding: "16px", 
                  background: "rgba(255,255,255,0.7)", 
                  borderRadius: "var(--radius-md)", 
                  marginBottom: "12px",
                  border: "1px solid rgba(59, 130, 246, 0.2)"
                }}>
                  <div style={{ fontWeight: "700", marginBottom: "10px", color: "#0369a1" }}>Contoh Pendekatan "Kapasitas Sprint" / Common Issue:</div>
                  <ul style={{ paddingLeft: "20px", margin: 0, listStyleType: "disc" }}>
                    <li style={{ marginBottom: "6px" }}><strong>Bug Fix (Kecil)</strong>: C(1)+I(1)+S(1)+R(1)+O(1) = <strong>5 pts</strong></li>
                    <li><strong>New Feature (Menengah)</strong>: C(3)+I(3)+S(2)+R(2)+O(1) = <strong>11 pts</strong></li>
                  </ul>
                </div>
                <p style={{ marginBottom: "8px" }}>
                  Jika ekspektasi standar 1 developer IT adalah mengerjakan <strong>1 Feature + 2 Bug Fix</strong> per minggu (total 21 pts/minggu), 
                  maka target tahunan (52 minggu) adalah sekitar <strong>± 1.000 pts</strong>.
                </p>
                <p style={{ 
                  fontStyle: "italic", 
                  color: "#64748b", 
                  margin: 0,
                  padding: "12px",
                  background: "rgba(255,255,255,0.5)",
                  borderRadius: "var(--radius-sm)",
                  borderLeft: "3px solid #0369a1"
                }}>
                  *Sesuaikan angka Target Pts pada form di atas dengan beban kerja atau data riil rata-rata dari Top Performer Anda tahun lalu.
                </p>
              </div>
            </div>

          </div>
        </>
      ) : (
        /* Enhanced Jira & GitLab Integration Forms */
        <form onSubmit={handleSaveIntegrations} className="configurator-grid-premium">
          {/* Enhanced Jira Configuration */}
          <div className="configurator-card-premium animate-slide-up" style={{ animationDelay: "0.1s" }}>
            <h3 style={{ 
              marginBottom: "24px", 
              fontSize: "18px", 
              fontWeight: "700", 
              color: "var(--color-primary)",
              display: "flex",
              alignItems: "center",
              gap: "10px"
            }}>
              <Server size={24} style={{ color: "var(--color-secondary)" }} />
              Jira Server Credentials
            </h3>

            <div className="form-group-premium">
              <label className="form-label-premium">Jira Host URL</label>
              <input
                type="url"
                className="form-input-premium"
                value={jiraUrl}
                onChange={(e) => setJiraUrl(e.target.value)}
                placeholder="https://atibusinessgroup.atlassian.net"
                required
                style={{ height: "48px" }}
              />
            </div>

            <div className="form-group-premium">
              <label className="form-label-premium">Jira Admin Email</label>
              <input
                type="email"
                className="form-input-premium"
                value={jiraEmail}
                onChange={(e) => setJiraEmail(e.target.value)}
                placeholder="email@atibusinessgroup.com"
                required
                style={{ height: "48px" }}
              />
            </div>

            <div className="form-group-premium">
              <label className="form-label-premium">Jira API Token (Enkripsi AES)</label>
              <input
                type="password"
                className="form-input-premium"
                value={jiraToken}
                onChange={(e) => setJiraToken(e.target.value)}
                placeholder={jiraToken ? "••••••••••••••••" : "Masukkan API Token Jira Baru"}
                style={{ height: "48px" }}
              />
            </div>

            <div className="form-group-premium">
              <label className="form-label-premium">Jira Board ID</label>
              <input
                type="text"
                className="form-input-premium"
                value={jiraBoardId}
                onChange={(e) => setJiraBoardId(e.target.value)}
                placeholder="Misal: 12"
                required
                style={{ height: "48px" }}
              />
            </div>

            <div className="form-group-premium">
              <label className="form-label-premium">Custom Field Story Points</label>
              <input
                type="text"
                className="form-input-premium"
                value={jiraSpField}
                onChange={(e) => setJiraSpField(e.target.value)}
                placeholder="customfield_10016"
                required
                style={{ height: "48px" }}
              />
            </div>
          </div>

          {/* Enhanced GitLab Configuration */}
          <div className="configurator-card-premium animate-slide-up" style={{ 
            display: "flex", 
            flexDirection: "column", 
            justifyContent: "space-between",
            animationDelay: "0.2s"
          }}>
            <div>
              <h3 style={{ 
                marginBottom: "24px", 
                fontSize: "18px", 
                fontWeight: "700", 
                color: "var(--color-primary)",
                display: "flex",
                alignItems: "center",
                gap: "10px"
              }}>
                <Globe size={24} style={{ color: "var(--color-secondary)" }} />
                GitLab Server Credentials
              </h3>

              <div className="form-group-premium">
                <label className="form-label-premium">GitLab Host URL</label>
                <input
                  type="url"
                  className="form-input-premium"
                  value={gitlabUrl}
                  onChange={(e) => setGitlabUrl(e.target.value)}
                  placeholder="https://gitlab.com atau domain gitlab kantor"
                  required
                  style={{ height: "48px" }}
                />
              </div>

              <div className="form-group-premium">
                <label className="form-label-premium">Personal Access Token (Enkripsi AES)</label>
                <input
                  type="password"
                  className="form-input-premium"
                  value={gitlabToken}
                  onChange={(e) => setGitlabToken(e.target.value)}
                  placeholder={gitlabToken ? "••••••••••••••••" : "Masukkan Personal Access Token Baru"}
                  style={{ height: "48px" }}
                />
                <div style={{ 
                  fontSize: "11px", 
                  color: "var(--color-text-muted)", 
                  marginTop: "8px",
                  padding: "10px 12px",
                  background: "var(--color-bg-light)",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid #e2e8f0"
                }}>
                  <strong>Info:</strong> PAT disarankan menggunakan scope <code style={{ 
                    background: "rgba(64, 89, 198, 0.1)", 
                    color: "var(--color-primary)", 
                    padding: "2px 6px", 
                    borderRadius: "4px", 
                    fontFamily: "var(--font-mono)" 
                  }}>read_api</code> dan <code style={{ 
                    background: "rgba(64, 89, 198, 0.1)", 
                    color: "var(--color-primary)", 
                    padding: "2px 6px", 
                    borderRadius: "4px", 
                    fontFamily: "var(--font-mono)" 
                  }}>read_repository</code>.
                </div>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={integLoading}
              style={{ width: "100%", marginTop: "32px", padding: "14px 24px", borderRadius: "var(--radius-md)" }}
            >
              {integLoading ? (
                <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span className="spinner-premium"></span> Menyimpan...
                </span>
              ) : (
                <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Shield size={16} /> Simpan Konfigurasi Integrasi
                </span>
              )}
            </button>
          </div>
        </form>
      )}
      
      {/* Enhanced Formula Guide Modal */}
      {showGuide && (
        <div className="modal-backdrop" onClick={(e) => {
          if (e.target === e.currentTarget) setShowGuide(false);
        }}>
          <div className="modal-content" style={{ maxWidth: "650px" }}>
            <div className="modal-header">
              <h3 style={{ 
                margin: 0, 
                fontSize: "18px", 
                color: "var(--color-primary)", 
                display: "flex", 
                alignItems: "center", 
                gap: "10px" 
              }}>
                <AlertCircle size={20} /> Panduan Penulisan Formula
              </h3>
              <button 
                onClick={() => setShowGuide(false)} 
                style={{ 
                  background: "transparent", 
                  border: "none", 
                  fontSize: "24px", 
                  cursor: "pointer", 
                  color: "var(--color-text-muted)",
                  padding: "4px",
                  borderRadius: "var(--radius-sm)",
                  transition: "var(--transition-fast)"
                }}
                onMouseEnter={(e) => e.target.style.background = "var(--color-bg-light)"}
                onMouseLeave={(e) => e.target.style.background = "transparent"}
              >×</button>
            </div>
            <div className="modal-body">
              <p style={{ marginBottom: "16px", lineHeight: "1.7" }}>
                Bapak/Ibu dapat menulis formula penilaian menggunakan ekspresi matematika standar. Sistem akan mengevaluasi formula tersebut berdasarkan data historis/otomatis yang ditarik dari Jira, GitLab, dan HRIS.
              </p>
              
              <div style={{ 
                padding: "16px", 
                background: "var(--color-bg-light)", 
                borderRadius: "var(--radius-lg)", 
                marginBottom: "16px",
                border: "1px solid #e2e8f0"
              }}>
                <h4 style={{ 
                  color: "var(--color-primary)", 
                  marginBottom: "12px", 
                  fontSize: "15px", 
                  fontWeight: "700",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px"
                }}>
                  <Settings size={16} style={{ color: "var(--color-secondary)" }} />
                  Pengaturan Indikator (Bobot & Cap)
                </h4>
                <ul style={{ marginBottom: 0, paddingLeft: "20px", listStyleType: "disc", lineHeight: "1.8" }}>
                  <li><strong>Bobot (Weight):</strong> Formatnya adalah <strong>Desimal (0.1 sampai 1.0)</strong>. Contoh: Untuk bobot 90%, tulis <code style={{ 
                    background: "rgba(64, 89, 198, 0.1)", 
                    color: "var(--color-primary)", 
                    padding: "2px 6px", 
                    borderRadius: "4px", 
                    fontFamily: "var(--font-mono)" 
                  }}>0.9</code>. Untuk 10%, tulis <code style={{ 
                    background: "rgba(64, 89, 198, 0.1)", 
                    color: "var(--color-primary)", 
                    padding: "2px 6px", 
                    borderRadius: "4px", 
                    fontFamily: "var(--font-mono)" 
                  }}>0.1</code>. Pastikan total keseluruhan bobot dari semua indikator bernilai <code style={{ 
                    background: "rgba(64, 89, 198, 0.1)", 
                    color: "var(--color-primary)", 
                    padding: "2px 6px", 
                    borderRadius: "4px", 
                    fontFamily: "var(--font-mono)" 
                  }}>1.0</code>.</li>
                  <li><strong>Cap Score (Batas Maksimal):</strong> Adalah nilai maksimal yang bisa didapatkan dari indikator ini sebelum dikalikan bobot. Jika diisi <code style={{ 
                    background: "rgba(64, 89, 198, 0.1)", 
                    color: "var(--color-primary)", 
                    padding: "2px 6px", 
                    borderRadius: "4px", 
                    fontFamily: "var(--font-mono)" 
                  }}>100</code>, maka meskipun hasil perhitungan formula mencapai 120, nilai akhir indikator tersebut akan dibatasi (di-cap) hanya sampai 100 saja.</li>
                </ul>
              </div>

              <div style={{ 
                padding: "16px", 
                background: "var(--color-bg-light)", 
                borderRadius: "var(--radius-lg)", 
                marginBottom: "16px",
                border: "1px solid #e2e8f0"
              }}>
                <h4 style={{ 
                  color: "var(--color-primary)", 
                  marginBottom: "12px", 
                  fontSize: "15px", 
                  fontWeight: "700",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px"
                }}>
                  <Database size={16} style={{ color: "var(--color-secondary)" }} />
                  Variabel yang Tersedia
                </h4>
                <ul style={{ marginBottom: 0, paddingLeft: "20px", listStyleType: "disc", lineHeight: "1.8" }}>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>attendance_days</code>: Total hari kehadiran karyawan.</li>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>target_days</code>: Total target hari kerja dalam periode tersebut (misal: 261).</li>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>late_percentage</code>: Persentase keterlambatan karyawan.</li>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>complexity_sp</code>: Total poin kompleksitas (kalkulasi dari CIRSO).</li>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>target_complexity_pts</code>: Target poin kompleksitas (didefinisikan di kolom Variables JSON).</li>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>gitlab_commits</code>: Total jumlah commit di GitLab.</li>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>gitlab_mr</code>: Total jumlah Merge Request di GitLab.</li>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>jira_sp</code> / <code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>raw_jira_sp</code>: Total Story Points dari tiket Jira.</li>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>jira_issues_completed</code>: Total tiket Jira yang diselesaikan.</li>
                  <li><em>Setiap *Key* yang Bapak/Ibu masukkan ke dalam kolom <b>Variables (JSON)</b> juga otomatis menjadi variabel yang bisa digunakan di formula.</em></li>
                </ul>
              </div>

              <div style={{ 
                padding: "16px", 
                background: "var(--color-bg-light)", 
                borderRadius: "var(--radius-lg)", 
                marginBottom: "16px",
                border: "1px solid #e2e8f0"
              }}>
                <h4 style={{ 
                  color: "var(--color-primary)", 
                  marginBottom: "12px", 
                  fontSize: "15px", 
                  fontWeight: "700",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px"
                }}>
                  <Zap size={16} style={{ color: "var(--color-secondary)" }} />
                  Fungsi Matematika yang Didukung
                </h4>
                <ul style={{ marginBottom: 0, paddingLeft: "20px", listStyleType: "disc", lineHeight: "1.8" }}>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>min(a, b)</code>: Mengambil nilai terkecil. Sering digunakan untuk membatasi skor maksimal (Cap).</li>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>max(a, b)</code>: Mengambil nilai terbesar. Sering digunakan agar skor tidak minus.</li>
                  <li><code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>round(a, digit)</code>: Membulatkan angka (contoh: <code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>round(skor, 2)</code>).</li>
                  <li>Operator dasar: <code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>+</code>, <code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>-</code>, <code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>*</code>, <code style={{ background: "rgba(64, 89, 198, 0.1)", color: "var(--color-primary)", padding: "2px 6px", borderRadius: "4px", fontFamily: "var(--font-mono)" }}>/</code></li>
                </ul>
              </div>

              <h4 style={{ 
                color: "var(--color-primary)", 
                marginBottom: "12px", 
                fontSize: "15px", 
                fontWeight: "700",
                display: "flex",
                alignItems: "center",
                gap: "8px"
              }}>
                <Code size={16} style={{ color: "var(--color-secondary)" }} />
                Contoh Formula
              </h4>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <div style={{ 
                  background: "var(--color-bg-light)", 
                  padding: "14px 18px", 
                  borderRadius: "var(--radius-md)", 
                  border: "1px solid #e2e8f0" 
                }}>
                  <div style={{ fontWeight: "700", marginBottom: "8px", color: "var(--color-primary)" }}>Persentase Biasa:</div>
                  <code style={{ 
                    background: "white", 
                    padding: "8px 12px", 
                    borderRadius: "var(--radius-sm)", 
                    display: "block", 
                    fontFamily: "var(--font-mono)",
                    fontSize: "13px",
                    border: "1px solid #e2e8f0"
                  }}>(attendance_days / target_days) * 100</code>
                </div>
                <div style={{ 
                  background: "var(--color-bg-light)", 
                  padding: "14px 18px", 
                  borderRadius: "var(--radius-md)", 
                  border: "1px solid #e2e8f0" 
                }}>
                  <div style={{ fontWeight: "700", marginBottom: "8px", color: "var(--color-primary)" }}>Dibatasi Maksimal 100 (Capped):</div>
                  <code style={{ 
                    background: "white", 
                    padding: "8px 12px", 
                    borderRadius: "var(--radius-sm)", 
                    display: "block", 
                    fontFamily: "var(--font-mono)",
                    fontSize: "13px",
                    border: "1px solid #e2e8f0"
                  }}>min((complexity_sp / target_complexity_pts) * 100, 100)</code>
                </div>
                <div style={{ 
                  background: "var(--color-bg-light)", 
                  padding: "14px 18px", 
                  borderRadius: "var(--radius-md)", 
                  border: "1px solid #e2e8f0" 
                }}>
                  <div style={{ fontWeight: "700", marginBottom: "8px", color: "var(--color-primary)" }}>Dengan Pengurangan (Penalti):</div>
                  <code style={{ 
                    background: "white", 
                    padding: "8px 12px", 
                    borderRadius: "var(--radius-sm)", 
                    display: "block", 
                    fontFamily: "var(--font-mono)",
                    fontSize: "13px",
                    border: "1px solid #e2e8f0"
                  }}>max((attendance_days / target_days) * 100 - (late_percentage * 0.5), 0)</code>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button 
                onClick={() => setShowGuide(false)} 
                className="btn btn-primary" 
                style={{ padding: "10px 24px", borderRadius: "var(--radius-md)" }}
              >
                Tutup
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}