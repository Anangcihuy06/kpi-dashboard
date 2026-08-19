import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { 
  // AI & Formula Icons
  Wand2, Sparkles, FunctionSquare, 
  // Context & Division Icons
  Building2, Layers, Users,
  // User & Role Icons
  Shield, UserCog, User, Crown,
  // Actions
  X, RefreshCw, Copy, CheckCircle, AlertCircle,
  // Testing & Validation
  Beaker,
  // Examples & Help
  Lightbulb, HelpCircle, Info, MessageSquare,
  // Navigation
  ChevronRight, ArrowRight,
  // Variables & Data
  Database, Hash, Braces, Settings,
  // Status & Feedback
  ShieldAlert, ShieldCheck,
  // Permissions
  Lock, LockOpen,
  // Configuration
  Sliders,
  // Additional UI
  Plus, Search, Filter, Eye, EyeOff, ChevronDown, ChevronUp,
  // Performance & Metrics
  TrendingUp, BarChart3,
  // Time & Dates
  Clock,
  // Communication
  Bell,
  // Files
  FileCode,
  // Operations
  Edit2, Trash2, Save
} from 'lucide-react';

const AIIndicatorCreator = ({ 
  currentUser, 
  selectedDivisionId, 
  selectedGroupId,
  divisions,
  onFormulaGenerated,
  onCancel 
}) => {
  const [indicatorDescription, setIndicatorDescription] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [aiResponse, setAiResponse] = useState(null);
  const [testData, setTestData] = useState({});
  const [testResult, setTestResult] = useState(null);
  const [showVariableHelper, setShowVariableHelper] = useState(false);
  const [aiContext, setAiContext] = useState(null);
  const [selectedScope, setSelectedScope] = useState('personal');
  const [validationResult, setValidationResult] = useState(null);

  // Helper Functions
  const getUserRoleIcon = () => {
    if (currentUser.roles?.includes('ROLE_ADMIN')) {
      return <Crown size={16} className="icon-admin" />;
    } else if (currentUser.roles?.includes('MANAGER') || currentUser.hasSubordinates) {
      return <UserCog size={16} className="icon-manager" />;
    } else {
      return <User size={16} className="icon-employee" />;
    }
  };

  const getUserRoleLabel = () => {
    if (currentUser.roles?.includes('ROLE_ADMIN')) return 'ADMIN';
    if (currentUser.roles?.includes('MANAGER')) return 'MANAGER';
    if (currentUser.hasSubordinates) return 'SUPERVISOR';
    return 'EMPLOYEE';
  };

  const getDivisionName = (divisionId) => {
    const division = divisions.find(d => d.id === divisionId);
    return division ? division.name : 'Unknown Division';
  };

  const getDivisionCode = (divisionId) => {
    const division = divisions.find(d => d.id === divisionId);
    return division ? division.code : 'UNKNOWN';
  };

  const determineCreationScope = () => {
    if (currentUser.roles?.includes('ROLE_ADMIN')) {
      return 'division';
    } else if (currentUser.roles?.includes('MANAGER') || currentUser.hasSubordinates) {
      return selectedGroupId ? 'group' : 'personal';
    } else {
      return 'personal';
    }
  };

  const getPermissionLevel = () => {
    if (currentUser.roles?.includes('ROLE_ADMIN')) return 'Admin - Full Access';
    if (currentUser.roles?.includes('MANAGER') || currentUser.hasSubordinates) {
      return selectedGroupId ? `Manager - ${getGroupName(selectedGroupId)}` : 'Manager - No Group Selected';
    }
    return 'Employee - View Only';
  };

  const getGroupName = (groupId) => {
    // This would need to be fetched from user data or groups endpoint
    return currentUser.group_name || 'Unknown Group';
  };

  // Load AI context on mount
  useEffect(() => {
    loadAIContext();
  }, [selectedDivisionId, currentUser]);

  const loadAIContext = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/ai/division-context?division_id=${selectedDivisionId}&user_id=${currentUser.id}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setAiContext(data);
        
        // Set default scope based on permissions
        const defaultScope = determineCreationScope();
        setSelectedScope(defaultScope);
        
        // Set example description from context
        if (data.division_context?.example_prompts?.length > 0) {
          setIndicatorDescription(data.division_context.example_prompts[0]);
        }
      }
    } catch (error) {
      console.error('Failed to load AI context:', error);
      toast.error('Failed to load AI context');
    }
  };

  // Generate AI formula
  const handleGenerateFormula = async () => {
    if (!indicatorDescription.trim()) {
      toast.error('Please enter an indicator description');
      return;
    }

    setIsGenerating(true);
    setAiResponse(null);
    const controller = new AbortController();
    const abortTimer = setTimeout(() => controller.abort(), 120000);
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/ai/generate-formula`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: currentUser.id,
          user_name: currentUser.full_name,
          user_role: getUserRoleLabel(),
          has_subordinates: currentUser.hasSubordinates,
          division_id: selectedDivisionId,
          division_name: getDivisionName(selectedDivisionId),
          division_code: getDivisionCode(selectedDivisionId),
          group_id: selectedGroupId,
          group_name: selectedGroupId ? getGroupName(selectedGroupId) : null,
          creation_scope: selectedScope,
          indicator_description: indicatorDescription
        }),
        signal: controller.signal
      });

      const data = await response.json();

      if (data.status === 'success') {
        setAiResponse(data);
        setValidationResult(data.validation);
        toast.success('Formula generated successfully! 🎉');

        // Generate test data from variables
        const sampleData = {};
        if (data.variables) {
          Object.entries(data.variables).forEach(([varName, varInfo]) => {
            const defaultVal = typeof varInfo === 'object' ? varInfo.default_value : varInfo;
            sampleData[varName] = defaultVal !== undefined ? defaultVal : 10;
          });
        }
        setTestData(sampleData);
      } else {
        toast.error('Failed to generate formula: ' + (data.error || data.message || 'Unknown error'));
      }
    } catch (error) {
      toast.error(error.name === 'AbortError' ? 'Request timeout, coba lagi.' : ('Error generating formula: ' + error.message));
    } finally {
      clearTimeout(abortTimer);
      setIsGenerating(false);
    }
  };

  // Test formula
  const handleTestFormula = async () => {
    if (!aiResponse?.formula) return;

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/v1/kpi/evaluate-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          formula: aiResponse.formula,
          context: testData
        })
      });

      const data = await response.json();

      if (data.status === 'success') {
        setTestResult({ success: true, value: data.result });
        toast.success(`Test result: ${data.result}`);
      } else {
        setTestResult({ success: false, error: data.message });
        toast.error('Formula error: ' + data.message);
      }
    } catch (error) {
      toast.error('Test error: ' + error.message);
    }
  };

  // Use generated formula
  const handleUseFormula = () => {
    if (!aiResponse?.formula) return;

    onFormulaGenerated({
      formula_expression: aiResponse.formula,
      variables: aiResponse.variables,
      cap_score: aiResponse.cap_score || 100.0
    });

    toast.success('Formula added to indicator! ✅');
  };

  // Copy formula to clipboard
  const handleCopyFormula = () => {
    if (!aiResponse?.formula) return;
    
    navigator.clipboard.writeText(aiResponse.formula);
    toast.success('Formula copied to clipboard');
  };

  // Use example prompt
  const handleUseExample = (example) => {
    setIndicatorDescription(example);
  };

  return (
    <div className="ai-indicator-creator-overlay">
      <div className="ai-indicator-creator">
        {/* Header */}
        <div className="creator-header">
          <div className="header-title">
            <Wand2 size={20} className="title-icon" />
            <h3>AI-Powered Indicator Creator</h3>
          </div>
          <div className="header-actions">
            <button 
              className="btn-icon"
              onClick={() => setShowVariableHelper(true)}
              title="Show Available Variables"
            >
              <Database size={18} />
            </button>
            <button 
              className="btn-icon"
              onClick={loadAIContext}
              title="Refresh Context"
            >
              <RefreshCw size={18} />
            </button>
            <button 
              className="btn-icon btn-close"
              onClick={onCancel}
              title="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Context Display */}
        <div className="context-display">
          <div className="context-badges">
            <div className="context-badge role-badge">
              {getUserRoleIcon()}
              <span>{getUserRoleLabel()}</span>
            </div>
            <div className="context-badge scope-badge">
              <Layers size={14} />
              <span>{selectedScope.toUpperCase()} CREATION</span>
            </div>
            <div className="context-badge division-badge">
              <Building2 size={14} />
              <span>{getDivisionName(selectedDivisionId)}</span>
            </div>
            {selectedGroupId && (
              <div className="context-badge group-badge">
                <Users size={14} />
                <span>{getGroupName(selectedGroupId)}</span>
              </div>
            )}
          </div>
          <div className="permission-info">
            <ShieldCheck size={14} />
            <span>{getPermissionLevel()}</span>
          </div>
        </div>

        {/* Scope Selection for Admins */}
        {currentUser.roles?.includes('ROLE_ADMIN') && (
          <div className="scope-selector">
            <label className="scope-label">
              <Layers size={16} />
              Creation Scope:
            </label>
            <div className="scope-options">
              <button 
                className={`scope-option ${selectedScope === 'division' ? 'active' : ''}`}
                onClick={() => setSelectedScope('division')}
              >
                <Building2 size={16} />
                <div className="scope-info">
                  <span className="scope-name">Division-Wide</span>
                  <span className="scope-desc">Affects all groups in {getDivisionName(selectedDivisionId)}</span>
                </div>
              </button>
              <button 
                className={`scope-option ${selectedScope === 'group' ? 'active' : ''}`}
                onClick={() => setSelectedScope('group')}
              >
                <Users size={16} />
                <div className="scope-info">
                  <span className="scope-name">Group-Specific</span>
                  <span className="scope-desc">Affects your group only</span>
                </div>
              </button>
            </div>
          </div>
        )}

        {/* Division Examples */}
        {aiContext?.division_context?.example_prompts && (
          <div className="division-examples">
            <div className="examples-header">
              <Lightbulb size={16} />
              <h4>Examples for {getDivisionName(selectedDivisionId)}:</h4>
            </div>
            <div className="examples-list">
              {aiContext.division_context.example_prompts.slice(0, 3).map((example, idx) => (
                <button 
                  key={idx} 
                  className="example-button"
                  onClick={() => handleUseExample(example)}
                >
                  <MessageSquare size={14} />
                  <span>"{example}"</span>
                  <ArrowRight size={14} />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* AI Input */}
        <div className="ai-input-section">
          <label className="input-label">
            <Sparkles size={16} />
            Describe Your Indicator:
          </label>
          <textarea
            value={indicatorDescription}
            onChange={(e) => setIndicatorDescription(e.target.value)}
            placeholder={`Describe the KPI indicator you want to create for ${getDivisionName(selectedDivisionId)}...`}
            rows={4}
            className="description-textarea"
          />
          <button 
            className="btn-generate"
            onClick={handleGenerateFormula}
            disabled={isGenerating || !indicatorDescription.trim()}
          >
            {isGenerating ? (
              <>
                <RefreshCw size={18} className="animate-spin" />
                <span>Generating Formula...</span>
              </>
            ) : (
              <>
                <Wand2 size={18} />
                <span>Generate Formula for {getDivisionName(selectedDivisionId)}</span>
              </>
            )}
          </button>
        </div>

        {/* AI Response */}
        {aiResponse && (
          <div className="ai-response-section">
            <div className="response-header">
              <div className="response-badges">
                <span className="badge-division">
                  <Building2 size={12} />
                  {getDivisionName(selectedDivisionId)}
                </span>
                {validationResult?.is_valid ? (
                  <span className="badge-validation-success">
                    <CheckCircle size={12} />
                    Formula Valid
                  </span>
                ) : (
                  <span className="badge-validation-error">
                    <AlertCircle size={12} />
                    Formula Issues
                  </span>
                )}
              </div>
              <button 
                className="btn-copy"
                onClick={handleCopyFormula}
                title="Copy Formula"
              >
                <Copy size={14} />
              </button>
            </div>

            {/* Generated Formula */}
            <div className="formula-display">
              <div className="formula-header">
                <FunctionSquare size={14} />
                <h4>Generated Formula:</h4>
              </div>
              <code className="formula-code">{aiResponse.formula}</code>
              
              {/* Validation Errors */}
              {validationResult && !validationResult.is_valid && (
                <div className="validation-errors">
                  <AlertCircle size={14} />
                  <div className="error-list">
                    {validationResult.undefined_variables?.length > 0 && (
                      <div className="error-item">
                        <span>Undefined variables: {validationResult.undefined_variables.join(', ')}</span>
                      </div>
                    )}
                    {validationResult.evaluation_error && (
                      <div className="error-item">
                        <span>Evaluation error: {validationResult.evaluation_error}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Generated Variables */}
            {aiResponse.variables && Object.keys(aiResponse.variables).length > 0 && (
              <div className="variables-display">
                <div className="variables-header">
                  <Hash size={14} />
                  <h4>Generated Variables:</h4>
                </div>
                <div className="variables-list">
                  {Object.entries(aiResponse.variables).map(([varName, varInfo]) => (
                    <div key={varName} className="variable-item">
                      <code className="variable-name">{varName}</code>
                      <span className="variable-desc">
                        {typeof varInfo === 'string' ? varInfo : varInfo.description}
                      </span>
                      {typeof varInfo === 'object' && varInfo.default_value !== undefined && (
                        <span className="variable-default">
                          <Settings size={12} />
                          Default: {varInfo.default_value}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Alternative Formulas */}
            {aiResponse.alternatives && aiResponse.alternatives.length > 0 && (
              <div className="alternatives-section">
                <div className="alternatives-header">
                  <Sparkles size={14} />
                  <h4>Alternative Formulas:</h4>
                </div>
                <div className="alternatives-list">
                  {aiResponse.alternatives.map((alt, idx) => (
                    <div key={idx} className="alternative-item">
                      <code className="alternative-formula">{alt}</code>
                      <button 
                        className="btn-use-alternative"
                        onClick={() => setAiResponse({...aiResponse, formula: alt})}
                      >
                        Use This
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Explanation */}
            {aiResponse.explanation && (
              <div className="explanation-section">
                <div className="explanation-header">
                  <Info size={14} />
                  <h4>How This Formula Works:</h4>
                </div>
                <p>{aiResponse.explanation}</p>
              </div>
            )}

            {/* Test Section */}
            <div className="test-section">
              <div className="test-header">
                <Beaker size={14} />
                <h4>Test Formula:</h4>
              </div>
              <div className="test-inputs">
                {Object.entries(testData).map(([varName, value]) => (
                  <div key={varName} className="test-input-item">
                    <label>{varName}:</label>
                    <input
                      type="number"
                      step="0.01"
                      value={value}
                      onChange={(e) => setTestData({...testData, [varName]: parseFloat(e.target.value)})}
                    />
                  </div>
                ))}
              </div>
              <button className="btn-test" onClick={handleTestFormula}>
                <Beaker size={16} />
                Test Formula
              </button>

              {/* Test Result */}
              {testResult && (
                <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
                  {testResult.success ? (
                    <div className="result-success">
                      <CheckCircle size={20} />
                      <div className="result-info">
                        <span className="result-value">{testResult.value}</span>
                        <span className="result-label">Test Result</span>
                      </div>
                    </div>
                  ) : (
                    <div className="result-error">
                      <AlertCircle size={20} />
                      <div className="result-info">
                        <span className="result-error-msg">{testResult.error}</span>
                        <span className="result-label">Formula Error</span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="action-buttons">
              <button className="btn-regenerate" onClick={handleGenerateFormula}>
                <RefreshCw size={16} />
                Regenerate
              </button>
              <button 
                className="btn-use-formula" 
                onClick={handleUseFormula}
                disabled={!validationResult?.is_valid}
              >
                <CheckCircle size={16} />
                Use This Formula
              </button>
            </div>
          </div>
        )}

        {/* Variable Helper */}
        {showVariableHelper && (
          <VariableHelper 
            currentUser={currentUser}
            selectedDivisionId={selectedDivisionId}
            aiContext={aiContext}
            onClose={() => setShowVariableHelper(false)}
            onUseVariable={(variable) => {
              // Add variable to description or handle as needed
              const variableText = `${variable.name}: ${variable.description}`;
              setIndicatorDescription(prev => prev + (prev ? ' ' : '') + variableText);
            }}
          />
        )}
      </div>
    </div>
  );
};

// Variable Helper Component
const VariableHelper = ({ currentUser, selectedDivisionId, aiContext, onClose, onUseVariable }) => {
  if (!aiContext) return null;

  const variables = aiContext.division_context?.variables || {};
  const isAdmin = currentUser.roles?.includes('ROLE_ADMIN');

  return (
    <div className="variable-helper-overlay">
      <div className="variable-helper">
        <div className="helper-header">
          <div className="header-title">
            <Database size={20} />
            <h4>Available Variables</h4>
          </div>
          <div className="header-actions">
            <span className={`user-scope-badge ${isAdmin ? 'admin' : 'manager'}`}>
              {isAdmin ? <Crown size={14} /> : <UserCog size={14} />}
              {isAdmin ? 'Admin View' : 'Manager View'}
            </span>
            <button className="btn-icon" onClick={onClose}>
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="variable-categories">
          {/* Core Variables */}
          {variables.core && variables.core.length > 0 && (
            <div className="variable-category">
              <div className="category-header">
                <Hash size={16} />
                <h5>Standard Variables</h5>
                <span className="variable-count">{variables.core.length}</span>
              </div>
              <div className="variable-list">
                {variables.core.map((variable, idx) => (
                  <VariableItem 
                    key={idx} 
                    variable={variable}
                    onUse={() => onUseVariable(variable)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Division-Specific Variables */}
          {variables.advanced && variables.advanced.length > 0 && (
            <div className="variable-category">
              <div className="category-header">
                <Braces size={16} />
                <h5>Division-Specific Variables</h5>
                <span className="variable-count">{variables.advanced.length}</span>
              </div>
              <div className="variable-list">
                {variables.advanced.map((variable, idx) => (
                  <VariableItem 
                    key={idx} 
                    variable={variable}
                    onUse={() => onUseVariable(variable)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* AI-Suggested Variables (Admin Only) */}
          {isAdmin && variables.ai_suggested && variables.ai_suggested.length > 0 && (
            <div className="variable-category ai-suggested">
              <div className="category-header">
                <Sparkles size={16} />
                <h5>AI-Suggested Variables</h5>
                <span className="variable-count">{variables.ai_suggested.length}</span>
                <ShieldCheck size={14} className="admin-badge" />
              </div>
              <div className="variable-list">
                {variables.ai_suggested.map((variable, idx) => (
                  <VariableItem 
                    key={idx} 
                    variable={variable}
                    onUse={() => onUseVariable(variable)}
                    isAISuggested
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const VariableItem = ({ variable, onUse, isAISuggested }) => {
  const getVariableIcon = () => {
    if (isAISuggested) return <Sparkles size={14} className="variable-icon ai-icon" />;
    if (variable.type === 'division_specific') return <Building2 size={14} className="variable-icon division-icon" />;
    return <Hash size={14} className="variable-icon standard-icon" />;
  };

  return (
    <div className={`variable-item ${isAISuggested ? 'ai-suggested' : ''}`}>
      {getVariableIcon()}
      <div className="variable-content">
        <code className="variable-name">{variable.name}</code>
        <span className="variable-desc">{variable.description}</span>
        {variable.unit && (
          <span className="variable-unit">
            <Clock size={12} />
            {variable.unit}
          </span>
        )}
        {variable.default_value !== undefined && (
          <span className="variable-default">
            <Settings size={12} />
            Default: {variable.default_value}
          </span>
        )}
      </div>
      <button className="btn-use-variable" onClick={onUse} title="Use this variable">
        <Plus size={12} />
      </button>
    </div>
  );
};

export default AIIndicatorCreator;