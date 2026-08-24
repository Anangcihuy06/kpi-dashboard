import React, { useState, useEffect } from "react";
import { Settings, Play, CheckCircle, RefreshCw, AlertCircle, Plus, Trash2, Globe, Server, Shield, UserCog, User, Building2, Layers, ShieldAlert, Lock, Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";

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
  const [showGuide, setShowGuide] = useState(false);

  const [saveLoading, setSaveLoading] = useState(false);
  const [calcLoading, setCalcLoading] = useState(false);
  const [calcProgress, setCalcProgress] = useState(0);
  const [syncDataLoading, setSyncDataLoading] = useState(false);
  const [testLoading, setTestLoading] = useState(false);
  const [integLoading, setIntegLoading] = useState(false);
  const [showAIPrompt, setShowAIPrompt] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [indicatorDescription, setIndicatorDescription] = useState("");

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
    const permissionLevel = getUserPermissionLevel();
    if (permissionLevel === "EMPLOYEE") {
      toast.error("Hanya manager dan admin yang dapat menambahkan indikator KPI.", {
        description: "Hubungi manager Anda untuk perubahan indikator."
      });
      return;
    }
    setShowAIPrompt(true);
  };

  const handleAIGenerate = async () => {
    if (!indicatorDescription.trim()) {
      toast.error("Mohon isi deskripsi indikator");
      return;
    }

    setAiLoading(true);
    const controller = new AbortController();
    const abortTimer = setTimeout(() => controller.abort(), 120000);
    try {
      const request = {
        user_id: currentUser.id || "unknown",
        user_name: currentUser.fullName || currentUser.name || "Unknown User",
        user_role: getUserPermissionLevel(),
        has_subordinates: currentUser.hasSubordinates || false,
        division_id: currentUser.division_id,
        division_name: divisions.find(d => d.id === currentUser.division_id)?.name || "Unknown",
        division_code: divisions.find(d => d.id === currentUser.division_id)?.code || "UNKNOWN",
        group_id: selectedGroupId,
        group_name: currentUser.group_name || null,
        creation_scope: selectedGroupId ? "group" : "division",
        indicator_description: indicatorDescription
      };

      const response = await fetch(import.meta.env.VITE_API_URL + "/api/v1/ai/generate-formula", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: controller.signal
      });

      const data = await response.json();

      if (data.status === "success" && data.formula) {
        const newMetric = {
          metric_key: data.variables?.metric_key || "kpi_" + Date.now(),
          weight: 0.10,
          calc_type: "FORMULA",
          formula_expression: data.formula,
          variables: data.variables || {},
          cap_score: data.cap_score || 100
        };

        setMetrics([...metrics, newMetric]);
        setShowAIPrompt(false);
        setIndicatorDescription("");
        toast.success("Indikator berhasil dibuat dengan AI!");
      } else {
        throw new Error(data.error || "Gagal generate formula");
      }
    } catch (error) {
      toast.error(error.name === "AbortError" ? "Request timeout, coba lagi." : (error.message || "Terjadi kesalahan saat generate formula"));
    } finally {
      clearTimeout(abortTimer);
      setAiLoading(false);
    }
  };

  const removeMetricRow = (idx) => {
    setMetrics(metrics.filter((_, i) => i !== idx));
  };

  // Helper functions for role checking
  const getUserPermissionLevel = () => {
    if (currentUser.roles?.includes("ROLE_ADMIN")) return "ADMIN";
    if (currentUser.roles?.includes("MANAGER") || currentUser.roles?.includes("SUPERVISOR") || currentUser.hasSubordinates) return "MANAGER";
    return "EMPLOYEE";
  };

  const canCreateIndicators = () => {
    return getUserPermissionLevel() !== "EMPLOYEE";
  };

  const getPermissionMessage = () => {
    const permissionLevel = getUserPermissionLevel();
    if (permissionLevel === "EMPLOYEE") {
      return {
        icon: <ShieldAlert size={24} />,
        title: "Permission Required",
        message: "Hanya manager dan admin yang dapat menambahkan indikator KPI.",
        submessage: "Hubungi manager Anda untuk perubahan indikator."
      };
    }
    return null;
  };

  const handleSaveRules = async () => {
    setSaveLoading(true);
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
      toast.success(`Aturan berhasil diperbarui ke Versi ${data.version}!`);
      fetchRulesForDivision(selectedDivisionId, selectedGroupId);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaveLoading(false);
    }
  };

  const handleSaveIntegrations = async (e) => {
    e.preventDefault();
    setIntegLoading(true);
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
      toast.success(data.message);
      fetchIntegrations();
    } catch (err) {
      toast.error(err.message);
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

  const pollJobUntilDone = (jobId, onDone, timeoutMs = 60 * 60 * 1000, onProgress = null) => {
    const startedAt = Date.now();
    const poll = setInterval(async () => {
      try {
        const statusRes = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/jobs/${jobId}`);
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          if (onProgress && statusData.progress != null) onProgress(statusData.progress);
          if (statusData.status === "COMPLETED" || statusData.status === "FAILED") {
            clearInterval(poll);
            onDone(statusData);
            return;
          }
        }
        if (Date.now() - startedAt > timeoutMs) {
          clearInterval(poll);
          onDone({ status: "TIMEOUT", error_message: "Waktu habis menunggu job. Cek ulang nanti atau jalankan ulang." });
        }
      } catch (e) {
        console.error("Error polling job status:", e);
      }
    }, 10000);
  };

  const handleSyncData = async () => {
    setSyncDataLoading(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/sync/data?supervisor_id=${currentUser.id || ""}`, {
        method: "POST"
      });
      if (!response.ok) throw new Error("Gagal menjalankan sync data");
      const data = await response.json();

      if (data.job_id) {
        toast.info("Sync data dari Jira/GitLab berjalan di background...");
        pollJobUntilDone(data.job_id, async (statusData) => {
          setSyncDataLoading(false);
          if (statusData.status === "COMPLETED") {
            toast.success("Sync data selesai! Jira & GitLab berhasil diperbarui.");
          } else {
            toast.error("Sync data gagal: " + (statusData.error_message || "Unknown error"));
          }
        });
      } else {
        toast.success("Sync data selesai!");
        setSyncDataLoading(false);
      }
    } catch (err) {
      toast.error(err.message);
      setSyncDataLoading(false);
    }
  };

  const handleCalcKPI = async () => {
    if (metrics.length === 0) {
      toast.warning("Matriks KPI belum dikonfigurasi. Silakan tambahkan indikator terlebih dahulu agar kalkulasi dapat berjalan.", { autoClose: 5000 });
      return;
    }
    
    setCalcLoading(true);
    setCalcProgress(0);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/kpi/calculate/${selectedYear}?force=true&supervisor_id=${currentUser.id || ""}`, {
        method: "POST"
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        toast.error(errData.detail || "Gagal menjalankan kalkulasi");
        setCalcLoading(false);
        setCalcProgress(0);
        return;
      }
      const data = await response.json();

      const checkEmptyData = async () => {
        try {
          const checkRes = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/kpi/yearly-performance?user_id=${currentUser.id}&year=${selectedYear}`);
          const checkData = await checkRes.json();
          if (checkData.status === "success" && (!checkData.data || (checkData.data.summary?.total_activities === 0 && checkData.data.summary?.total_issues_completed === 0))) {
             toast.warning(`Kalkulasi selesai, tetapi data untuk tahun ${selectedYear} masih kosong. Silakan jalankan 'Sync Data' terlebih dahulu.`, { autoClose: 6000 });
          } else {
             toast.success(`Kalkulasi KPI selesai untuk tahun ${selectedYear}.`);
          }
        } catch(e) {
          toast.success(`Kalkulasi KPI selesai untuk tahun ${selectedYear}.`);
        }
      };

      if (data.job_id) {
        toast.info("Menghitung KPI dari data lokal...");
        pollJobUntilDone(data.job_id, async (statusData) => {
          setCalcLoading(false);
          setCalcProgress(100);
          if (statusData.status === "COMPLETED") {
            await checkEmptyData();
          } else {
            toast.error("Kalkulasi KPI gagal: " + (statusData.error_message || "Unknown error"));
          }
        }, 60 * 60 * 1000, setCalcProgress);
      } else {
        await checkEmptyData();
        setCalcLoading(false);
        setCalcProgress(100);
      }
    } catch (err) {
      toast.error(err.message);
      setCalcLoading(false);
      setCalcProgress(0);
    }
  };

   return (
    <div className="dashboard-premium-bold">
      <div className="header-ui">
        <div>
          <span className="hero-eyebrow">Administration & Configuration</span>
          <h2>Matriks Configurator & Rule Builder</h2>
          <p style={{ color: "var(--color-text-muted)", fontSize: "14px", margin: 0 }}>
            Tentukan konfigurasi matriks KPI divisi, rumusan formula dinamis, dan koneksi server integrasi.
          </p>
        </div>
      </div>

      {/* Bold Sub Tabs Toggle */}
      <div className="glass-card-bold" style={{ padding: "0", marginBottom: "28px", overflow: "hidden" }}>
        <div style={{ display: "flex", gap: "0", borderBottom: "1px solid rgba(102, 122, 209, 0.2)", padding: "0 24px" }}>
          <button
            onClick={() => setActiveSubTab("rules")}
            style={{ 
              background: activeSubTab === "rules" ? "linear-gradient(135deg, #121854, #4059c6)" : "transparent",
              color: activeSubTab === "rules" ? "#ffffff" : "#64748b",
              borderRadius: "0",
              padding: "12px 24px",
              fontSize: "14px",
              fontWeight: 700,
              boxShadow: "none",
              border: "none",
              cursor: "pointer",
              transition: "all 0.3s ease",
              position: "relative"
            }}
          >
            <Settings size={14} style={{ display: "inline", marginRight: "8px", verticalAlign: "middle" }} />
            KPI Matrix Rules
            {activeSubTab === "rules" && <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "3px", background: "linear-gradient(90deg, #4059c6, #667ad1)" }} />}
          </button>
          <button
            onClick={() => setActiveSubTab("integrations")}
            style={{ 
              background: activeSubTab === "integrations" ? "linear-gradient(135deg, #121854, #4059c6)" : "transparent",
              color: activeSubTab === "integrations" ? "#ffffff" : "#64748b",
              borderRadius: "0",
              padding: "12px 24px",
              fontSize: "14px",
              fontWeight: 700,
              boxShadow: "none",
              border: "none",
              cursor: "pointer",
              transition: "all 0.3s ease",
              position: "relative"
            }}
          >
            <Globe size={14} style={{ display: "inline", marginRight: "8px", verticalAlign: "middle" }} />
            Jira & GitLab Integrations
            {activeSubTab === "integrations" && <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: "3px", background: "linear-gradient(90deg, #4059c6, #667ad1)" }} />}
          </button>
        </div>
      </div>

      {activeSubTab === "rules" ? (
        <>
          {/* Calculate scores trigger */}
          <div className="card" style={{ background: "linear-gradient(90deg, var(--color-tint) 0%, rgba(255,255,255,1) 100%)", borderColor: "var(--color-accent)" }}>
            <h3 style={{ marginBottom: "8px" }}>Sync Data & Hitung KPI</h3>
            <p style={{ fontSize: "13px", color: "var(--color-text-muted)", marginBottom: "20px" }}>
              <strong>Sync Data</strong> menarik data terbaru dari Jira/GitLab ke database lokal. <strong>Hitung KPI</strong> menghitung KPI karyawan menggunakan data yang sudah ada di database lokal.
            </p>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "16px" }}>
              <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
                <button
                  className="btn-primary"
                  onClick={handleSyncData}
                  disabled={syncDataLoading}
                  style={{ width: "auto", padding: "0 24px", height: "44px", display: "flex", alignItems: "center", gap: "8px" }}
                >
                  {syncDataLoading ? <RefreshCw className="animate-spin" size={16} /> : <Globe size={16} />}
                  {syncDataLoading ? "Sync Data Berjalan..." : "Sync Data"}
                </button>
                <button
                  className="btn-primary"
                  onClick={handleCalcKPI}
                  disabled={calcLoading}
                  style={{ width: "auto", padding: "0 24px", height: "44px", display: "flex", alignItems: "center", gap: "8px" }}
                >
                  {calcLoading ? <RefreshCw className="animate-spin" size={16} /> : <Play size={16} />}
                  {calcLoading ? "Menghitung KPI..." : "Hitung KPI"}
                </button>
              </div>
              
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
            </div>
            {calcLoading && (
              <div style={{ marginTop: "10px", width: "100%", maxWidth: "380px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                  <span className="status-pill syncing"><RefreshCw size={11} className="animate-spin" /> Sedang Menghitung</span>
                  <span className="table-meta num">{calcProgress}%</span>
                </div>
                <div style={{
                  height: "8px", background: "#e2e8f0", borderRadius: "4px", overflow: "hidden"
                }}>
                  <div style={{
                    height: "100%", width: `${Math.max(calcProgress, 2)}%`,
                    background: "var(--color-primary)", borderRadius: "4px",
                    transition: "width 0.8s ease-in-out"
                  }} />
                </div>
                <div className="table-meta" style={{ marginTop: "6px" }}>
                  Kalkulasi hanya memproses tanggal yang belum terhitung, lalu memperbarui agregat tahunan.
                </div>
              </div>
            )}
          </div>

          <div className="configurator-grid">

            {/* Main Formula Rules Configurator */}
            <div className="card">
              <div style={{ marginBottom: "24px", paddingBottom: "20px", borderBottom: "1px solid #e2e8f0" }}>
                <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "flex-start", gap: "16px" }}>
                  <div style={{ flex: "1 1 300px" }}>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center", marginBottom: "12px" }}>
                      <div style={{ 
                        padding: "4px 12px", 
                        background: "rgba(37, 99, 235, 0.1)", 
                        color: "var(--color-primary)", 
                        borderRadius: "20px", 
                        fontSize: "11px", 
                        fontWeight: 600,
                        letterSpacing: "0.5px",
                        textTransform: "uppercase",
                        border: "1px solid rgba(37, 99, 235, 0.2)"
                      }}>
                        {currentUser.group_name || "Tidak ada Group"}
                      </div>
                      <div style={{ 
                        padding: "4px 12px", 
                        background: "#f1f5f9", 
                        color: "#64748b", 
                        borderRadius: "20px", 
                        fontSize: "11px", 
                        fontWeight: 600,
                        letterSpacing: "0.5px",
                        textTransform: "uppercase",
                        border: "1px solid #e2e8f0"
                      }}>
                        {divisions.find(d => d.id === selectedDivisionId)?.name || "Default Divisi"}
                      </div>
                    </div>
                    
                    <textarea
                      value={name}
                      onChange={(e) => {
                        setName(e.target.value);
                        e.target.style.height = 'auto';
                        e.target.style.height = e.target.scrollHeight + 'px';
                      }}
                      rows={1}
                      style={{
                        width: "100%",
                        fontSize: "22px",
                        fontWeight: 700,
                        color: "#0f172a",
                        border: "1px solid transparent",
                        background: "transparent",
                        padding: "4px 8px",
                        marginLeft: "-8px",
                        borderRadius: "6px",
                        transition: "all 0.2s",
                        outline: "none",
                        resize: "none",
                        overflow: "hidden",
                        lineHeight: "1.4"
                      }}
                      onFocus={(e) => { e.target.style.border = "1px solid #cbd5e1"; e.target.style.background = "#fff"; }}
                      onBlur={(e) => { e.target.style.border = "1px solid transparent"; e.target.style.background = "transparent"; }}
                      placeholder="Masukkan Nama Matriks KPI..."
                    />
                    <div style={{ fontSize: "13px", color: "#64748b", marginTop: "4px", paddingLeft: "2px" }}>
                      Atur indikator, formula, dan bobot KPI untuk karyawan di grup ini.
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                    <button className="btn-outline" onClick={() => setShowGuide(true)} style={{ padding: "8px 16px", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px", borderRadius: "8px", borderColor: "#cbd5e1", color: "#475569", background: "#fff", boxShadow: "0 1px 2px rgba(0,0,0,0.05)" }}>
                      <AlertCircle size={16} /> Panduan Formula
                    </button>
                    {canCreateIndicators() ? (
                      <button className="btn-primary" onClick={addMetricRow} style={{ padding: "8px 16px", fontSize: "13px", display: "flex", alignItems: "center", gap: "8px", borderRadius: "8px", boxShadow: "0 1px 3px rgba(37,99,235,0.2)" }}>
                        <Sparkles size={16} /> Tambah dengan AI
                      </button>
                    ) : (
                      <div className="permission-message" style={{ 
                        padding: "8px 12px", 
                        fontSize: "12px", 
                        display: "flex", 
                        alignItems: "center", 
                        gap: "8px", 
                        borderRadius: "8px", 
                        background: "#fef3c7", 
                        color: "#92400e",
                        border: "1px solid #fcd34d"
                      }}>
                        {getPermissionMessage()?.icon}
                        <div>
                          <div style={{ fontWeight: 600 }}>{getPermissionMessage()?.title}</div>
                          <div style={{ fontSize: "11px" }}>{getPermissionMessage()?.message}</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="table-container">
                <table className="custom-table" style={{ fontSize: "12px" }}>
                  <thead>
                    <tr>
                      <th>Key Indikator</th>
                      <th data-align="right" style={{ width: "80px" }}>Bobot</th>
                      <th>Formula Ekspresi</th>
                      <th data-align="right" style={{ width: "80px" }}>Cap</th>
                      <th>Variables (JSON)</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.length === 0 ? (
                      <tr>
                        <td colSpan="6" style={{ textAlign: "center", padding: "40px 20px", background: "#f8fafc" }}>
                          <div style={{ color: "var(--color-text-muted)", marginBottom: "12px" }}>
                            <AlertCircle size={32} style={{ margin: "0 auto", color: "#94a3b8" }} />
                          </div>
                          <h4 style={{ margin: "0 0 8px 0", color: "var(--color-primary)" }}>Belum Ada Configure Matrix</h4>
                          <p style={{ margin: 0, fontSize: "14px", color: "var(--color-text-muted)" }}>
                            Silakan tambahkan indikator baru atau buat otomatis dengan AI.
                          </p>
                        </td>
                      </tr>
                    ) : (
                      metrics.map((metric, idx) => (
                        <tr key={idx}>
                        <td>
                          <input
                            type="text"
                            className="table-input"
                            value={metric.metric_key}
                            onChange={(e) => handleMetricChange(idx, "metric_key", e.target.value)}
                          />
                        </td>
                        <td data-align="right">
                          <input
                            type="number"
                            step="0.05"
                            min="0"
                            max="1"
                            className="table-input num"
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
                        <td data-align="right">
                          <input
                            type="number"
                            className="table-input num"
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
                    )))}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: "24px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
              <span className="table-meta" style={{ fontSize: "12px" }}>
                Total bobot:{" "}
                <strong className={`num ${Math.abs((metrics.reduce((s, m) => s + (parseFloat(m.weight) || 0), 0)) - 1) <= 0.01 ? "text-success" : "text-danger"}`}>
                  {(metrics.reduce((s, m) => s + (parseFloat(m.weight) || 0), 0) * 100).toFixed(0)}%
                </strong>{" "}
                (harus 100%)
              </span>
              <button
                className="btn-primary"
                onClick={handleSaveRules}
                disabled={saveLoading}
                style={{ width: "auto", padding: "0 24px" }}
              >
                {saveLoading && <RefreshCw className="animate-spin" size={16} />}
                Simpan & Terapkan Perubahan (Buat Versi Baru)
              </button>
            </div>
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
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                    <h4 style={{ fontSize: "14px", margin: 0 }}>Hasil Evaluasi</h4>
                    <span className={`status-pill ${testResult.success ? "live" : "stale"}`}>
                      {testResult.success ? "Formula Valid" : "Gagal Parsing"}
                    </span>
                  </div>
                  {testResult.success ? (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#15803d", fontWeight: 700, fontSize: "18px" }}>
                      <CheckCircle size={20} />
                      <span className="num">Output: {testResult.value}</span>
                    </div>
                  ) : (
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "8px", color: "#b91c1c", fontSize: "13px" }}>
                      <AlertCircle size={18} style={{ flexShrink: 0, marginTop: "2px" }} />
                      <div>
                        <span style={{ fontWeight: 700 }}>Detail Kesalahan:</span>
                        <p style={{ fontFamily: "var(--font-mono)", marginTop: "4px", marginBottom: 0 }}>{testResult.error}</p>
                      </div>
                    </div>
                  )}
                  <p className="table-meta" style={{ marginTop: 10, marginBottom: 0 }}>
                    Nilai dihitung menggunakan evaluator AST aman — tidak menggunakan eval().
                  </p>
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
              <p style={{ fontSize: "11px", color: "var(--color-text-muted)", marginTop: "8px" }}>
                * Token disimpan dalam database dalam keadaan terenkripsi (AES). Token yang ada tidak akan pernah ditampilkan ulang.
              </p>
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
      
      {/* Panduan Formula Modal */}
      {showGuide && (
        <div className="modal-backdrop-ui" onClick={() => setShowGuide(false)}>
          <div className="modal-ui" onClick={(e) => e.stopPropagation()}>
            <div className="modal-ui-header">
              <h3 style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <AlertCircle size={20} style={{ color: "var(--color-secondary)" }} /> Panduan Penulisan Formula
              </h3>
              <button className="modal-ui-close" onClick={() => setShowGuide(false)} aria-label="Tutup panduan">&times;</button>
            </div>
            <div className="modal-ui-body" style={{ fontSize: "14px", color: "#334155", lineHeight: "1.6" }}>
              <p style={{ marginBottom: "16px" }}>Bapak/Ibu dapat menulis formula penilaian menggunakan ekspresi matematika standar. Sistem akan mengevaluasi formula tersebut berdasarkan data historis/otomatis yang ditarik dari Jira, GitLab, dan HRIS.</p>
              
              <h4 style={{ color: "var(--color-primary)", marginBottom: "8px", fontSize: "15px" }}>Pengaturan Indikator (Bobot & Cap)</h4>
              <ul style={{ marginBottom: "20px", paddingLeft: "20px", listStyleType: "disc" }}>
                <li><strong>Bobot (Weight):</strong> Formatnya adalah <strong>Desimal (0.1 sampai 1.0)</strong>. Contoh: Untuk bobot 90%, tulis <code>0.9</code>. Untuk 10%, tulis <code>0.1</code>. Pastikan total keseluruhan bobot dari semua indikator bernilai <code>1.0</code>.</li>
                <li><strong>Cap Score (Batas Maksimal):</strong> Adalah nilai maksimal yang bisa didapatkan dari indikator ini sebelum dikalikan bobot. Jika diisi <code>100</code>, maka meskipun hasil perhitungan formula mencapai 120, nilai akhir indikator tersebut akan dibatasi (di-cap) hanya sampai 100 saja.</li>
              </ul>

              <h4 style={{ color: "var(--color-primary)", marginBottom: "8px", fontSize: "15px" }}>Variabel yang Tersedia</h4>
              <ul style={{ marginBottom: "20px", paddingLeft: "20px", listStyleType: "disc" }}>
                <li><code>attendance_days</code>: Total hari kehadiran karyawan.</li>
                <li><code>target_days</code>: Total target hari kerja dalam periode tersebut (misal: 261).</li>
                <li><code>late_percentage</code>: Persentase keterlambatan karyawan.</li>
                <li><code>complexity_sp</code>: Total poin kompleksitas (kalkulasi dari CIRSO).</li>
                <li><code>target_complexity_pts</code>: Target poin kompleksitas (didefinisikan di kolom Variables JSON).</li>
                <li><code>gitlab_commits</code>: Total jumlah commit di GitLab.</li>
                <li><code>gitlab_mr</code>: Total jumlah Merge Request di GitLab.</li>
                <li><code>jira_sp</code> / <code>raw_jira_sp</code>: Total Story Points dari tiket Jira.</li>
                <li><code>jira_issues_completed</code>: Total tiket Jira yang diselesaikan.</li>
                <li><i>Setiap *Key* yang Bapak/Ibu masukkan ke dalam kolom <b>Variables (JSON)</b> juga otomatis menjadi variabel yang bisa digunakan di formula.</i></li>
              </ul>

              <h4 style={{ color: "var(--color-primary)", marginBottom: "8px", fontSize: "15px" }}>Fungsi Matematika yang Didukung</h4>
              <ul style={{ marginBottom: "20px", paddingLeft: "20px", listStyleType: "disc" }}>
                <li><code>min(a, b)</code>: Mengambil nilai terkecil. Sering digunakan untuk membatasi skor maksimal (Cap).</li>
                <li><code>max(a, b)</code>: Mengambil nilai terbesar. Sering digunakan agar skor tidak minus.</li>
                <li><code>round(a, digit)</code>: Membulatkan angka (contoh: <code>round(skor, 2)</code>).</li>
                <li>Operator dasar: <code>+</code>, <code>-</code>, <code>*</code>, <code>/</code></li>
              </ul>

              <h4 style={{ color: "var(--color-primary)", marginBottom: "8px", fontSize: "15px" }}>Contoh Formula</h4>
              <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0", marginBottom: "16px" }}>
                <strong>Persentase Biasa:</strong><br/>
                <code>(attendance_days / target_days) * 100</code>
              </div>
              <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0", marginBottom: "16px" }}>
                <strong>Dibatasi Maksimal 100 (Capped):</strong><br/>
                <code>min((complexity_sp / target_complexity_pts) * 100, 100)</code>
              </div>
              <div style={{ background: "#f8fafc", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <strong>Dengan Pengurangan (Penalti):</strong><br/>
                <code>max((attendance_days / target_days) * 100 - (late_percentage * 0.5), 0)</code>
              </div>
            </div>
            <div className="modal-ui-footer">
              <button onClick={() => setShowGuide(false)} className="btn-primary" style={{ padding: "8px 24px", fontSize: "14px" }}>Tutup</button>
            </div>
          </div>
        </div>
      )}

      {showAIPrompt && (
        <div className="modal-backdrop-ui">
          <div className="modal-ui" style={{ maxWidth: "520px" }}>
            <div className="modal-ui-header">
              <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                <Sparkles size={20} style={{ color: "var(--color-secondary)" }} /> Buat Indikator dengan AI
              </h3>
              <button
                className="modal-ui-close"
                onClick={() => {
                  setShowAIPrompt(false);
                  setIndicatorDescription("");
                }}
                aria-label="Tutup"
              >&times;</button>
            </div>

            <div className="modal-ui-body">
              <div style={{ marginBottom: "16px" }}>
                <label style={{
                  display: "block",
                  fontSize: "14px",
                  fontWeight: 600,
                  color: "#374151",
                  marginBottom: "8px"
                }}>
                  Deskripsi Indikator KPI
                </label>
                <textarea
                  value={indicatorDescription}
                  onChange={(e) => setIndicatorDescription(e.target.value)}
                  placeholder="Contoh: Indikator kehadiran dengan target 22 hari kerja per bulan, penalti 0.5 poin untuk keterlambatan di atas 15 menit"
                  rows={4}
                  style={{
                    width: "100%",
                    padding: "12px",
                    border: "1px solid #d1d5db",
                    borderRadius: "8px",
                    fontSize: "14px",
                    fontFamily: "inherit",
                    resize: "vertical",
                    boxSizing: "border-box"
                  }}
                />
              </div>

            <div style={{
              background: "#fef3c7",
              padding: "12px",
              borderRadius: "8px",
              marginBottom: "16px",
              fontSize: "12px",
              color: "#92400e"
            }}>
              <strong>💡 Tips:</strong> Jelaskan secara detail tentang:
              <ul style={{ margin: "8px 0 0 20px", padding: 0 }}>
                <li>Target yang ingin dicapai</li>
                <li>Metric apa yang diukur</li>
                <li>Aturan penalti/pengurangan</li>
              </ul>
            </div>

            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
              <button
                onClick={() => {
                  setShowAIPrompt(false);
                  setIndicatorDescription("");
                }}
                style={{
                  padding: "10px 20px",
                  border: "1px solid #d1d5db",
                  background: "white",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: 600,
                  color: "#374151"
                }}
              >
                Batal
              </button>
              <button
                onClick={handleAIGenerate}
                disabled={aiLoading}
                style={{
                  padding: "10px 20px",
                  background: aiLoading ? "#9ca3af" : "#2563eb",
                  color: "white",
                  border: "none",
                  borderRadius: "8px",
                  cursor: aiLoading ? "not-allowed" : "pointer",
                  fontSize: "14px",
                  fontWeight: 600,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px"
                }}
              >
                {aiLoading ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Sedang Generate...
                  </>
                ) : (
                  <>
                    <Sparkles size={16} />
                    Generate Formula
                  </>
                )}
              </button>
            </div>
          </div>
          </div>
        </div>
      )}

    </div>
  );
}
