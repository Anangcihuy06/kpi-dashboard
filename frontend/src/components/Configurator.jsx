import React, { useState, useEffect } from "react";
import { Settings, Play, CheckCircle, RefreshCw, AlertCircle, Plus, Trash2, Globe, Server } from "lucide-react";

export default function Configurator() {
  const [activeSubTab, setActiveSubTab] = useState("rules"); // "rules" or "integrations"

  // Matrix Rules states
  const [ruleId, setRuleId] = useState("");
  const [name, setName] = useState("");
  const [metrics, setMetrics] = useState([]);
  const [sprints, setSprints] = useState([]);
  const [divisions, setDivisions] = useState([]);
  const [selectedDivisionId, setSelectedDivisionId] = useState("");
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  
  const [currentUser, setCurrentUser] = useState({});

  // Integration Settings states
  const [jiraUrl, setJiraUrl] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraToken, setJiraToken] = useState("");
  const [jiraBoardId, setJiraBoardId] = useState("");
  const [jiraSpField, setJiraSpField] = useState("customfield_10016");
  const [gitlabUrl, setGitlabUrl] = useState("https://gitlab.com");
  const [gitlabToken, setGitlabToken] = useState("");

  // Live Tester states
  const [testFormula, setTestFormula] = useState("min((complexity_sp / target_complexity_pts) * 100, 100)");
  const [testContextJson, setTestContextJson] = useState('{\n  "complexity_sp": 150,\n  "target_complexity_pts": 300,\n  "attendance_days": 240,\n  "target_days": 261,\n  "late_percentage": 5\n}');
  const [testResult, setTestResult] = useState(null);

  const [saveLoading, setSaveLoading] = useState(false);
  const [calcLoading, setCalcLoading] = useState(false);
  const [testLoading, setTestLoading] = useState(false);
  const [integLoading, setIntegLoading] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
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
    if (selectedDivisionId) {
      fetchRulesForDivision(selectedDivisionId, selectedGroupId);
    }
  }, [selectedDivisionId, selectedGroupId]);

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
      // Fetch current division info first
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
        
        if (selectedDiv.code === "IT" && data.metrics && (!data.metrics.some(m => m.metric_key === "feature_complexity"))) {
            // Auto-upgrade to Pure Complexity config for IT division
            setName("IT Developer KPI Matrix (Pure Complexity)");
            setMetrics([
              { metric_key: "feature_complexity", category: "ENGINEERING", weight: 0.90, calc_type: "FORMULA", formula_expression: "min((complexity_sp / target_complexity_pts) * 100, 100)", variables: { target_complexity_pts: 300, max_c: 5, max_i: 5, max_s: 5, max_r: 3, max_o: 2 }, cap_score: 100.0 },
              { metric_key: "attendance", category: "DISCIPLINE", weight: 0.10, calc_type: "FORMULA", formula_expression: "max((attendance_days / target_days) * 100 - (late_percentage * 0.5), 0)", variables: { target_days: 261, late_percentage: 5 }, cap_score: 100.0 }
            ]);
        } else {
            setName(data.name);
            setMetrics(data.metrics);
        }
      } else {
        if (selectedDiv.code === "IT") {
            setName("IT Developer KPI Matrix (Pure Complexity)");
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
    <div>
      <div className="header-ui">
        <div>
          <h2>Matriks Configurator & Rule Builder</h2>
          <p style={{ color: "var(--color-text-muted)", fontSize: "14px" }}>
            Tentukan konfigurasi matriks KPI divisi, rumusan formula dinamis, dan koneksi server integrasi.
          </p>
        </div>
      </div>

      {message && (
        <div
          className="card"
          style={{
            borderColor: message.type === "success" ? "#bbf7d0" : "#fecaca",
            backgroundColor: message.type === "success" ? "#f0fdf4" : "#fef2f2",
            color: message.type === "success" ? "#15803d" : "#b91c1c",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "16px 24px",
            marginBottom: "24px"
          }}
        >
          {message.type === "success" ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Sub Tabs Toggle */}
      <div style={{ display: "flex", gap: "12px", borderBottom: "1px solid #cbd5e1", marginBottom: "28px", paddingBottom: "2px" }}>
        <button
          className={`switcher-btn ${activeSubTab === "rules" ? "active" : ""}`}
          onClick={() => { setActiveSubTab("rules"); setMessage(null); }}
          style={{ backgroundColor: activeSubTab === "rules" ? "var(--color-secondary)" : "transparent", color: activeSubTab === "rules" ? "#fff" : "var(--color-primary)", padding: "8px 24px", borderRadius: "16px 16px 0 0", fontSize: "14px" }}
        >
          <Settings size={14} style={{ display: "inline", marginRight: "6px" }} />
          KPI Matrix Rules
        </button>
        <button
          className={`switcher-btn ${activeSubTab === "integrations" ? "active" : ""}`}
          onClick={() => { setActiveSubTab("integrations"); setMessage(null); }}
          style={{ backgroundColor: activeSubTab === "integrations" ? "var(--color-secondary)" : "transparent", color: activeSubTab === "integrations" ? "#fff" : "var(--color-primary)", padding: "8px 24px", borderRadius: "16px 16px 0 0", fontSize: "14px" }}
        >
          <Globe size={14} style={{ display: "inline", marginRight: "6px" }} />
          Jira & GitLab Integrations
        </button>
      </div>

      {activeSubTab === "rules" ? (
        <>
          {/* Calculate scores trigger */}
          <div className="card" style={{ background: "linear-gradient(90deg, var(--color-tint) 0%, rgba(255,255,255,1) 100%)", borderColor: "var(--color-accent)" }}>
            <h3 style={{ marginBottom: "8px" }}>Trigger Sync & Kalkulasi Tahunan (Data dari Database Lokal)</h3>
            <p style={{ fontSize: "13px", color: "var(--color-text-muted)", marginBottom: "20px" }}>
              Jalankan sinkronisasi langsung untuk menarik data dari Jira/GitLab kantor, memproses formula, dan meng-update dashboard untuk satu tahun penuh.
            </p>
            <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <label className="form-label" style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Pilih Tahun</label>
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
              <button
                className="btn-primary"
                onClick={handleCalculateYear}
                disabled={calcLoading}
                style={{ width: "auto", padding: "0 24px", height: "44px", marginTop: "16px" }}
              >
                {calcLoading ? <RefreshCw className="animate-spin" size={16} /> : <Play size={16} />}
                Sync & Hitung KPI Karyawan
              </button>
            </div>
          </div>

          <div className="configurator-grid">

            {/* Main Formula Rules Configurator */}
            <div className="card">
              <div className="flex-between" style={{ marginBottom: "16px" }}>
                <div>
                  <h3 style={{ marginBottom: "4px" }}>Aturan Indikator Divisi / Group</h3>
                  <div style={{ display: "flex", gap: "8px", alignItems: "center", marginTop: "8px" }}>
                    <div style={{ 
                      padding: "4px 12px", 
                      background: "rgba(37, 99, 235, 0.1)", 
                      color: "var(--color-primary)", 
                      borderRadius: "16px", 
                      fontSize: "12px", 
                      fontWeight: 600,
                      border: "1px solid rgba(37, 99, 235, 0.2)"
                    }}>
                      {currentUser.group_name || "Tidak ada Group"}
                    </div>
                    <div style={{ 
                      padding: "4px 12px", 
                      background: "#f1f5f9", 
                      color: "#475569", 
                      borderRadius: "16px", 
                      fontSize: "12px", 
                      fontWeight: 500,
                      border: "1px solid #e2e8f0"
                    }}>
                      {divisions.find(d => d.id === selectedDivisionId)?.name || "Default Divisi"}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "12px" }}>
                  <button className="btn-outline" onClick={addMetricRow} style={{ padding: "6px 16px", fontSize: "12px", display: "flex", alignItems: "center", gap: "6px", height: "32px" }}>
                    <Plus size={14} /> Tambah Indikator
                  </button>
                </div>
              </div>

              <div style={{ marginBottom: "20px" }}>
                <label className="form-label">Nama Matriks</label>
                <input
                  type="text"
                  className="form-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div className="table-container">
                <table className="custom-table" style={{ fontSize: "12px" }}>
                  <thead>
                    <tr>
                      <th>Key Indikator</th>
                      <th style={{ width: "80px" }}>Bobot</th>
                      <th>Formula Ekspresi</th>
                      <th style={{ width: "80px" }}>Cap</th>
                      <th>Variables (JSON)</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.map((metric, idx) => (
                      <tr key={idx}>
                        <td>
                          <input
                            type="text"
                            className="table-input"
                            value={metric.metric_key}
                            onChange={(e) => handleMetricChange(idx, "metric_key", e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            step="0.05"
                            min="0"
                            max="1"
                            className="table-input"
                            value={metric.weight}
                            onChange={(e) => handleMetricChange(idx, "weight", e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="text"
                            className="table-input table-input-formula"
                            value={metric.formula_expression}
                            onChange={(e) => handleMetricChange(idx, "formula_expression", e.target.value)}
                          />
                        </td>
                        <td>
                          <input
                            type="number"
                            className="table-input"
                            value={metric.cap_score}
                            onChange={(e) => handleMetricChange(idx, "cap_score", e.target.value)}
                          />
                        </td>
                        <td>
                          {metric.metric_key === "feature_complexity" ? (
                            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", minWidth: "350px", background: "#f8fafc", padding: "8px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
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
                                  <div key={f.key} style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                                    <label style={{ fontSize: "10px", fontWeight: "600", width: "90px", color: "#475569" }}>{f.label}:</label>
                                    <input
                                      type="number"
                                      style={{ width: "60px", fontSize: "11px", padding: "4px", border: "1px solid #cbd5e1", borderRadius: "4px" }}
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
                              className="table-input table-input-formula"
                              value={typeof metric.variables === 'object' ? JSON.stringify(metric.variables) : metric.variables}
                              onChange={(e) => handleMetricChange(idx, "variables", e.target.value)}
                              style={{ fontFamily: "monospace", fontSize: "11px" }}
                            />
                          )}
                        </td>
                        <td>
                          <button
                            onClick={() => removeMetricRow(idx)}
                            style={{ background: "none", border: "none", cursor: "pointer", color: "#ef4444", padding: "6px" }}
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
                className="btn-primary"
                onClick={handleSaveRules}
                disabled={saveLoading}
                style={{ marginTop: "24px" }}
              >
                {saveLoading && <RefreshCw className="animate-spin" size={16} />}
                Simpan & Terapkan Perubahan (Buat Versi Baru)
              </button>
            </div>

            {/* Live Formula Tester Side Panel */}
            <div className="card">
              <h3 style={{ marginBottom: "8px" }}>Live Formula Tester</h3>
              <p style={{ fontSize: "12px", color: "var(--color-text-muted)", marginBottom: "20px" }}>
                Uji rumus formula matematika Anda dengan input variabel dummy langsung sebelum disimpan.
              </p>

              <div className="form-group">
                <label className="form-label">Formula Uji</label>
                <input
                  type="text"
                  className="form-input"
                  value={testFormula}
                  onChange={(e) => setTestFormula(e.target.value)}
                  style={{ fontFamily: "monospace" }}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Input Context (JSON)</label>
                <textarea
                  className="form-input"
                  value={testContextJson}
                  onChange={(e) => setTestContextJson(e.target.value)}
                  style={{ height: "140px", fontFamily: "monospace", padding: "12px", borderRadius: "16px", resize: "none" }}
                />
              </div>

              <button
                className="btn-primary"
                onClick={handleTestFormula}
                disabled={testLoading}
                style={{ marginBottom: "20px" }}
              >
                {testLoading && <RefreshCw className="animate-spin" size={16} />}
                <Play size={14} /> Jalankan Simulasi Uji
              </button>

              {testResult && (
                <div className="tester-box">
                  <h4 style={{ fontSize: "14px", marginBottom: "8px" }}>Hasil Evaluasi:</h4>
                  {testResult.success ? (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#15803d", fontWeight: 700, fontSize: "18px" }}>
                      <CheckCircle size={20} />
                      <span>Output: {testResult.value}</span>
                    </div>
                  ) : (
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "8px", color: "#b91c1c", fontSize: "13px" }}>
                      <AlertCircle size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
                      <div>
                        <span style={{ fontWeight: 700 }}>Syntax Error / Parsing Gagal:</span>
                        <p style={{ fontFamily: "monospace", marginTop: "4px" }}>{testResult.error}</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Guide Card for Target Pts */}
            <div className="card" style={{ marginTop: "24px", background: "#f0f9ff", border: "1px solid #bae6fd" }}>
              <h3 style={{ marginBottom: "12px", color: "#0369a1", fontSize: "14px", display: "flex", alignItems: "center", gap: "8px" }}>
                💡 Panduan Menentukan Target Pts
              </h3>
              <div style={{ fontSize: "12px", color: "#334155", lineHeight: "1.6" }}>
                <p style={{ marginBottom: "8px" }}>
                  <strong>Target Pts</strong> adalah benchmark ekspektasi poin kumulatif (C+I+R+S+O) yang harus dicapai karyawan dalam 1 tahun.
                </p>
                <p style={{ marginBottom: "8px", fontWeight: "bold" }}>Contoh Pendekatan "Kapasitas Sprint" / Common Issue:</p>
                <ul style={{ paddingLeft: "16px", margin: "0 0 8px 0" }}>
                  <li><strong>Bug Fix (Kecil)</strong>: C(1)+I(1)+S(1)+R(1)+O(1) = <strong>5 pts</strong></li>
                  <li><strong>New Feature (Menengah)</strong>: C(3)+I(3)+S(2)+R(2)+O(1) = <strong>11 pts</strong></li>
                </ul>
                <p style={{ marginBottom: "8px" }}>
                  Jika ekspektasi standar 1 developer IT adalah mengerjakan <strong>1 Feature + 2 Bug Fix</strong> per minggu (total 21 pts/minggu), 
                  maka target tahunan (52 minggu) adalah sekitar <strong>± 1.000 pts</strong>.
                </p>
                <p style={{ fontStyle: "italic", color: "#64748b", margin: 0 }}>
                  *Sesuaikan angka Target Pts pada form di atas dengan beban kerja atau data riil rata-rata dari Top Performer Anda tahun lalu.
                </p>
              </div>
            </div>

          </div>
        </>
      ) : (
        /* Jira & GitLab Integration Forms */
        <form onSubmit={handleSaveIntegrations} className="configurator-grid">
          {/* Jira Configuration */}
          <div className="card">
            <h3 style={{ marginBottom: "20px", display: "flex", alignItems: "center", gap: "10px" }}>
              <Server size={20} style={{ color: "var(--color-secondary)" }} />
              Jira Server Credentials
            </h3>

            <div className="form-group">
              <label className="form-label">Jira Host URL</label>
              <input
                type="url"
                className="form-input"
                value={jiraUrl}
                onChange={(e) => setJiraUrl(e.target.value)}
                placeholder="https://atibusinessgroup.atlassian.net"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Jira Admin Email</label>
              <input
                type="email"
                className="form-input"
                value={jiraEmail}
                onChange={(e) => setJiraEmail(e.target.value)}
                placeholder="email@atibusinessgroup.com"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Jira API Token (Enkripsi AES)</label>
              <input
                type="password"
                className="form-input"
                value={jiraToken}
                onChange={(e) => setJiraToken(e.target.value)}
                placeholder={jiraToken ? "••••••••••••••••" : "Masukkan API Token Jira Baru"}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Jira Board ID</label>
              <input
                type="text"
                className="form-input"
                value={jiraBoardId}
                onChange={(e) => setJiraBoardId(e.target.value)}
                placeholder="Misal: 12"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Custom Field Story Points</label>
              <input
                type="text"
                className="form-input"
                value={jiraSpField}
                onChange={(e) => setJiraSpField(e.target.value)}
                placeholder="customfield_10016"
                required
              />
            </div>
          </div>

          {/* GitLab Configuration */}
          <div className="card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <h3 style={{ marginBottom: "20px", display: "flex", alignItems: "center", gap: "10px" }}>
                <Globe size={20} style={{ color: "var(--color-secondary)" }} />
                GitLab Server Credentials
              </h3>

              <div className="form-group">
                <label className="form-label">GitLab Host URL</label>
                <input
                  type="url"
                  className="form-input"
                  value={gitlabUrl}
                  onChange={(e) => setGitlabUrl(e.target.value)}
                  placeholder="https://gitlab.com atau domain gitlab kantor"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Personal Access Token (Enkripsi AES)</label>
                <input
                  type="password"
                  className="form-input"
                  value={gitlabToken}
                  onChange={(e) => setGitlabToken(e.target.value)}
                  placeholder={gitlabToken ? "••••••••••••••••" : "Masukkan Personal Access Token Baru"}
                />
                <p style={{ fontSize: "11px", color: "var(--color-text-muted)", marginTop: "8px" }}>
                  * PAT disarankan menggunakan scope <strong>read_api</strong> dan <strong>read_repository</strong>.
                </p>
              </div>
            </div>

            <button
              type="submit"
              className="btn-primary"
              disabled={integLoading}
              style={{ marginTop: "40px" }}
            >
              {integLoading && <RefreshCw className="animate-spin" size={16} />}
              Simpan Konfigurasi Integrasi
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
