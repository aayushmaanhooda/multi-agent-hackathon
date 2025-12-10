import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import GooeyNav from "../components/GooeyNav";
import GradientText from "../components/GradientText";
import BrandLogo from "../components/BrandLogo";
import { api } from "../services/api";
import "./InfoPage.css"; // Reusing existing premium styles

export default function SetRoster() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [progressMessages, setProgressMessages] = useState([]);
  const [currentStep, setCurrentStep] = useState("");
  const [timer, setTimer] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    checkSession();
  }, []);

  // Timer effect - count seconds while loading
  useEffect(() => {
    let interval = null;
    if (loading && currentStep.includes("Running multi-agent workflow")) {
      setTimer(0); // Reset timer when starting
      interval = setInterval(() => {
        setTimer((prevTimer) => prevTimer + 1);
      }, 1000);
    } else {
      setTimer(0); // Reset when not loading
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loading, currentStep]);

  const checkSession = async () => {
    try {
      const userData = await api.getMe();
      setUser(userData);
      // Only admins can access this page
      if (userData.role !== "admin") {
        navigate("/dashboard");
      }
    } catch (err) {
      console.error("Session check failed", err);
      navigate("/login");
    }
  };
  const [employeeFile, setEmployeeFile] = useState(null);
  const [storeFile, setStoreFile] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [generatedRoster, setGeneratedRoster] = useState(null);
  const [violations, setViolations] = useState([]);
  const [reportData, setReportData] = useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!employeeFile || !storeFile) {
      setCurrentStep("Please select both files to continue.");
      return;
    }

    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("employee_file", employeeFile);
      formData.append("store_file", storeFile);

      const response = await fetch("http://localhost:8000/upload-roster", {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Upload failed");
      }

      const data = await response.json();
      console.log("Upload success:", data);
      setUploadSuccess(true);
      // Removed alert - user stays on page
    } catch (err) {
      console.error("Upload error:", err);
      // Removed alert - error will be shown in UI
      setCurrentStep(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    setProgressMessages([]);
    setCurrentStep("Running multi-agent workflow...");

    try {
      const response = await fetch("http://localhost:8000/generate-roster", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Generation failed");
      }

      const data = await response.json();
      console.log("Roster generated:", data);

      // Update progress messages if available
      if (data.progress && Array.isArray(data.progress)) {
        setProgressMessages(data.progress);
        // Update currentStep to show the latest progress message
        if (data.progress.length > 0) {
          setCurrentStep(data.progress[data.progress.length - 1]);
        }
      }

      setGeneratedRoster(data);
      setViolations(data.violations || []);
      setReportData({
        coverage_percent: data.coverage_percent,
        filled_slots: data.filled_slots,
        total_slots: data.total_slots,
        roster_status: data.roster_status,
        summary: data.summary,
        recommendations: data.recommendations || [],
        violation_count: data.violation_count,
        critical_violations: data.critical_violations,
        iterations: data.iterations,
      });

      setCurrentStep("✅ Roster generation completed!");

      // Navigate to roster page after successful generation
      setTimeout(() => {
        navigate("/roster");
      }, 1500);
    } catch (err) {
      console.error("Generation error:", err);
      setCurrentStep(`❌ Error: ${err.message}`);
      // Removed alert - error shown in currentStep
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadRoster = () => {
    if (generatedRoster?.roster_file) {
      const filename = generatedRoster.roster_file.split("/").pop();
      window.open(
        `http://localhost:8000/download-roster/${filename}`,
        "_blank"
      );
    }
  };

  const handleDownloadReport = (isJson = false) => {
    const fileKey = isJson ? "report_json_file" : "report_file";
    if (generatedRoster?.[fileKey]) {
      const filename = generatedRoster[fileKey].split("/").pop();
      window.open(
        `http://localhost:8000/download-report/${filename}`,
        "_blank"
      );
    }
  };

  const navItems = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Roster", href: "/roster" },
    user?.role === "admin"
      ? { label: "Generate Roster", href: "/set-roster" }
      : null,
    { label: "Subscription", href: "/subscription" },
  ].filter(Boolean);

  return (
    <div className="info-page">
      <div className="info-nav-wrapper">
        <div className="roster-ai-logo">
          <BrandLogo />
        </div>
        <GooeyNav items={navItems} />
      </div>

      <div
        className="section-wrapper"
        style={{
          justifyContent: "center",
          minHeight: "100vh",
          paddingBottom: "2rem",
        }}
      >
        <div
          className="info-container"
          style={{ maxWidth: "900px", width: "100%" }}
        >
          <h1
            className="info-title"
            style={{ textAlign: "center", marginBottom: "2rem" }}
          >
            Generate Roster
          </h1>

          {!uploadSuccess ? (
            <>
              <p
                className="info-text"
                style={{ textAlign: "center", marginBottom: "2rem" }}
              >
                Upload the required files to generate the weekly roster.
              </p>
              {currentStep && currentStep.includes("Please select") && (
                <div
                  style={{
                    padding: "1rem",
                    marginBottom: "1rem",
                    background: "rgba(239, 68, 68, 0.2)",
                    border: "1px solid rgba(239, 68, 68, 0.5)",
                    borderRadius: "8px",
                    color: "#fca5a5",
                    textAlign: "center",
                  }}
                >
                  {currentStep}
                </div>
              )}

              <form onSubmit={handleUpload} className="contact-form-card">
                <div className="form-group">
                  <label className="form-label">
                    Employee Availability File (Excel/CSV)
                  </label>
                  <input
                    type="file"
                    className="form-input"
                    accept=".xlsx,.csv"
                    onChange={(e) => setEmployeeFile(e.target.files[0])}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">
                    Store Requirements File (CSV)
                  </label>
                  <input
                    type="file"
                    className="form-input"
                    accept=".csv,.xlsx"
                    onChange={(e) => setStoreFile(e.target.files[0])}
                    required
                  />
                </div>

                <button
                  type="submit"
                  className="form-button"
                  disabled={loading}
                >
                  {loading ? "Uploading..." : "Submit"}
                </button>
              </form>
            </>
          ) : (
            <div className="contact-form-card" style={{ textAlign: "center" }}>
              <h2
                className="info-subtitle"
                style={{
                  color: "#4ade80",
                  marginBottom: "1rem",
                  borderBottom: "none",
                }}
              >
                Files Uploaded Successfully!
              </h2>
              <div
                className="info-grid"
                style={{ marginBottom: "2rem", gridTemplateColumns: "1fr" }}
              >
                <div className="info-card" style={{ padding: "1rem" }}>
                  <p className="info-text" style={{ color: "#fff" }}>
                    <strong>Employees:</strong> {employeeFile?.name}
                  </p>
                  <p className="info-text" style={{ color: "#fff" }}>
                    <strong>Stores:</strong> {storeFile?.name}
                  </p>
                </div>
              </div>

              {loading && (
                <div
                  className="contact-form-card"
                  style={{ marginBottom: "1rem", textAlign: "center" }}
                >
                  <h3
                    className="info-subtitle"
                    style={{ marginBottom: "1rem", color: "#3b82f6" }}
                  >
                    {currentStep || "🔄 Starting roster generation..."}
                    {loading &&
                      currentStep.includes("Running multi-agent workflow") && (
                        <span
                          style={{
                            marginLeft: "1rem",
                            fontSize: "1.2rem",
                            fontWeight: "bold",
                            color: "#10b981",
                            fontFamily: "monospace",
                          }}
                        >
                          ({timer}s)
                        </span>
                      )}
                  </h3>
                  {progressMessages.length > 0 && (
                    <div
                      style={{
                        textAlign: "left",
                        maxHeight: "400px",
                        overflowY: "auto",
                      }}
                    >
                      {progressMessages.map((msg, idx) => {
                        // Extract agent number from message for better display
                        const isAgent1 = msg.toLowerCase().includes("agent 1");
                        const isAgent2 = msg.toLowerCase().includes("agent 2");
                        const isAgent3 = msg.toLowerCase().includes("agent 3");
                        const isAgent4 = msg.toLowerCase().includes("agent 4");
                        const isAgent5 = msg.toLowerCase().includes("agent 5");
                        const isCompleted = msg
                          .toLowerCase()
                          .includes("completed");
                        const isRunning = msg.toLowerCase().includes("running");

                        let icon = "🔄";
                        if (isCompleted) icon = "✅";
                        if (isAgent1) icon = "🔄";
                        if (isAgent2) icon = "🔄";
                        if (isAgent3) icon = "🔄";
                        if (isAgent4) icon = "🔄";
                        if (isAgent5) icon = "🔄";

                        return (
                          <div
                            key={idx}
                            style={{
                              padding: "0.75rem",
                              marginBottom: "0.5rem",
                              background: isCompleted
                                ? "rgba(16, 185, 129, 0.2)"
                                : "rgba(59, 130, 246, 0.2)",
                              borderRadius: "6px",
                              fontSize: "0.9rem",
                              borderLeft: isCompleted
                                ? "3px solid #10b981"
                                : "3px solid #3b82f6",
                              transition: "all 0.3s ease",
                            }}
                          >
                            <strong>{icon}</strong> {msg}
                          </div>
                        );
                      })}
                    </div>
                  )}
                  <div style={{ marginTop: "1rem" }}>
                    <div
                      className="spinner"
                      style={{
                        border: "3px solid rgba(59, 130, 246, 0.3)",
                        borderTop: "3px solid #3b82f6",
                        borderRadius: "50%",
                        width: "40px",
                        height: "40px",
                        animation: "spin 1s linear infinite",
                        margin: "0 auto",
                      }}
                    ></div>
                  </div>
                </div>
              )}
              <button
                onClick={handleGenerate}
                className="form-button"
                disabled={loading}
                style={{
                  background: "linear-gradient(to right, #3b82f6, #10b981)",
                }}
              >
                {loading ? "Generating..." : "Generate Roster"}
              </button>

              {generatedRoster && (
                <div style={{ marginTop: "2rem", color: "#fff" }}>
                  <div
                    className="info-card"
                    style={{ marginBottom: "1.5rem", padding: "1.5rem" }}
                  >
                    <h3
                      className="info-subtitle"
                      style={{
                        marginBottom: "1rem",
                        borderBottom: "2px solid #3b82f6",
                        paddingBottom: "0.5rem",
                      }}
                    >
                      Roster Generation Complete! ✅
                    </h3>

                    {reportData && (
                      <div style={{ marginBottom: "1.5rem" }}>
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns:
                              "repeat(auto-fit, minmax(200px, 1fr))",
                            gap: "1rem",
                            marginBottom: "1rem",
                          }}
                        >
                          <div
                            style={{
                              background: "rgba(59, 130, 246, 0.2)",
                              padding: "1rem",
                              borderRadius: "8px",
                            }}
                          >
                            <p
                              style={{
                                margin: 0,
                                fontSize: "0.9rem",
                                color: "#a78bfa",
                              }}
                            >
                              Coverage
                            </p>
                            <p
                              style={{
                                margin: "0.5rem 0 0 0",
                                fontSize: "1.5rem",
                                fontWeight: "bold",
                              }}
                            >
                              {reportData.coverage_percent?.toFixed(1)}%
                            </p>
                          </div>
                          <div
                            style={{
                              background: "rgba(16, 185, 129, 0.2)",
                              padding: "1rem",
                              borderRadius: "8px",
                            }}
                          >
                            <p
                              style={{
                                margin: 0,
                                fontSize: "0.9rem",
                                color: "#34d399",
                              }}
                            >
                              Violations
                            </p>
                            <p
                              style={{
                                margin: "0.5rem 0 0 0",
                                fontSize: "1.5rem",
                                fontWeight: "bold",
                              }}
                            >
                              {reportData.violation_count} (
                              {reportData.critical_violations} critical)
                            </p>
                          </div>
                          <div
                            style={{
                              background: "rgba(34, 197, 94, 0.2)",
                              padding: "1rem",
                              borderRadius: "8px",
                            }}
                          >
                            <p
                              style={{
                                margin: 0,
                                fontSize: "0.9rem",
                                color: "#4ade80",
                              }}
                            >
                              Iterations
                            </p>
                            <p
                              style={{
                                margin: "0.5rem 0 0 0",
                                fontSize: "1.5rem",
                                fontWeight: "bold",
                              }}
                            >
                              {reportData.iterations}
                            </p>
                          </div>
                          <div
                            style={{
                              background: "rgba(59, 130, 246, 0.2)",
                              padding: "1rem",
                              borderRadius: "8px",
                            }}
                          >
                            <p
                              style={{
                                margin: 0,
                                fontSize: "0.9rem",
                                color: "#60a5fa",
                              }}
                            >
                              Slots Filled
                            </p>
                            <p
                              style={{
                                margin: "0.5rem 0 0 0",
                                fontSize: "1.5rem",
                                fontWeight: "bold",
                              }}
                            >
                              {reportData.filled_slots}/{reportData.total_slots}
                            </p>
                          </div>
                        </div>

                        <div style={{ marginBottom: "1rem" }}>
                          <p style={{ margin: "0.5rem 0", fontSize: "0.9rem" }}>
                            <strong>Status:</strong>{" "}
                            <span
                              style={{
                                color:
                                  reportData.roster_status === "approved"
                                    ? "#4ade80"
                                    : "#fbbf24",
                                textTransform: "uppercase",
                              }}
                            >
                              {reportData.roster_status || "needs_review"}
                            </span>
                          </p>
                          {reportData.summary && (
                            <p
                              style={{
                                margin: "0.5rem 0",
                                fontSize: "0.9rem",
                                color: "#d1d5db",
                              }}
                            >
                              {reportData.summary}
                            </p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Download Buttons */}
                    <div
                      style={{
                        display: "flex",
                        gap: "1rem",
                        flexWrap: "wrap",
                        marginBottom: "1.5rem",
                      }}
                    >
                      <button
                        onClick={handleDownloadRoster}
                        className="form-button"
                        style={{
                          background:
                            "linear-gradient(to right, #10b981, #059669)",
                          flex: "1",
                          minWidth: "200px",
                        }}
                      >
                        📥 Download Roster (Excel)
                      </button>
                      {generatedRoster.report_file && (
                        <button
                          onClick={() => handleDownloadReport(false)}
                          className="form-button"
                          style={{
                            background:
                              "linear-gradient(to right, #3b82f6, #2563eb)",
                            flex: "1",
                            minWidth: "200px",
                          }}
                        >
                          📄 Download Report (Text)
                        </button>
                      )}
                      {generatedRoster.report_json_file && (
                        <button
                          onClick={() => handleDownloadReport(true)}
                          className="form-button"
                          style={{
                            background:
                              "linear-gradient(to right, #3b82f6, #10b981)",
                            flex: "1",
                            minWidth: "200px",
                          }}
                        >
                          📊 Download Report (JSON)
                        </button>
                      )}
                    </div>

                    {/* Violations Display */}
                    {violations.length > 0 && (
                      <div style={{ marginTop: "1.5rem" }}>
                        <h4
                          className="info-subtitle"
                          style={{ marginBottom: "1rem", fontSize: "1.1rem" }}
                        >
                          Violations ({violations.length})
                        </h4>
                        <div
                          style={{
                            maxHeight: "300px",
                            overflowY: "auto",
                            background: "rgba(0, 0, 0, 0.3)",
                            borderRadius: "8px",
                            padding: "1rem",
                          }}
                        >
                          {violations.slice(0, 20).map((violation, idx) => (
                            <div
                              key={idx}
                              style={{
                                marginBottom: "0.75rem",
                                padding: "0.75rem",
                                background:
                                  violation.severity === "critical"
                                    ? "rgba(239, 68, 68, 0.2)"
                                    : "rgba(251, 191, 36, 0.2)",
                                borderRadius: "6px",
                                borderLeft: `3px solid ${
                                  violation.severity === "critical"
                                    ? "#ef4444"
                                    : "#fbbf24"
                                }`,
                              }}
                            >
                              <div
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "start",
                                  marginBottom: "0.25rem",
                                }}
                              >
                                <span
                                  style={{
                                    fontSize: "0.75rem",
                                    fontWeight: "bold",
                                    textTransform: "uppercase",
                                    color:
                                      violation.severity === "critical"
                                        ? "#ef4444"
                                        : "#fbbf24",
                                  }}
                                >
                                  {violation.severity}
                                </span>
                                <span
                                  style={{
                                    fontSize: "0.75rem",
                                    color: "#9ca3af",
                                  }}
                                >
                                  {violation.type}
                                </span>
                              </div>
                              <p
                                style={{
                                  margin: "0.25rem 0",
                                  fontSize: "0.9rem",
                                  fontWeight: "bold",
                                }}
                              >
                                {violation.employee} - {violation.date}
                              </p>
                              <p
                                style={{
                                  margin: "0.25rem 0",
                                  fontSize: "0.85rem",
                                  color: "#d1d5db",
                                }}
                              >
                                {violation.message}
                              </p>
                              {violation.recommendation && (
                                <p
                                  style={{
                                    margin: "0.25rem 0",
                                    fontSize: "0.8rem",
                                    color: "#9ca3af",
                                    fontStyle: "italic",
                                  }}
                                >
                                  💡 {violation.recommendation}
                                </p>
                              )}
                            </div>
                          ))}
                          {violations.length > 20 && (
                            <p
                              style={{
                                textAlign: "center",
                                color: "#9ca3af",
                                marginTop: "1rem",
                              }}
                            >
                              ... and {violations.length - 20} more violations
                            </p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Recommendations */}
                    {reportData?.recommendations &&
                      reportData.recommendations.length > 0 && (
                        <div style={{ marginTop: "1.5rem" }}>
                          <h4
                            className="info-subtitle"
                            style={{ marginBottom: "1rem", fontSize: "1.1rem" }}
                          >
                            Recommendations
                          </h4>
                          <ul style={{ listStyle: "none", padding: 0 }}>
                            {reportData.recommendations.map((rec, idx) => (
                              <li
                                key={idx}
                                style={{
                                  marginBottom: "0.5rem",
                                  padding: "0.75rem",
                                  background: "rgba(59, 130, 246, 0.2)",
                                  borderRadius: "6px",
                                  fontSize: "0.9rem",
                                }}
                              >
                                💡 {rec}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
