import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import GooeyNav from "../components/GooeyNav";
import GradientText from "../components/GradientText";
import BrandLogo from "../components/BrandLogo";
import { api } from "../services/api";
import "./InfoPage.css";

export default function RosterPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [rosterData, setRosterData] = useState(null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    checkSession();
    fetchRoster();
  }, []);

  const checkSession = async () => {
    try {
      const userData = await api.getMe();
      setUser(userData);
    } catch (err) {
      console.error("Session check failed", err);
      navigate("/login");
    }
  };

  const fetchRoster = async () => {
    setLoading(true);
    try {
      const response = await fetch("http://localhost:8000/get-roster", {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to fetch roster");
      }

      const data = await response.json();
      setRosterData(data);
    } catch (err) {
      console.error("Error fetching roster:", err);
      setRosterData({ exists: false });
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadRoster = () => {
    if (rosterData?.roster_file) {
      window.open(
        `http://localhost:8000/download-roster/${rosterData.roster_file}`,
        "_blank"
      );
    }
  };

  const handleDownloadReport = (isJson = false) => {
    const fileKey = isJson ? "report_json_file" : "report_file";
    if (rosterData?.[fileKey]) {
      window.open(
        `http://localhost:8000/download-report/${rosterData[fileKey]}`,
        "_blank"
      );
    }
  };

  const navItems = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "ROSTER", href: "/roster" },
    user?.role === "admin"
      ? { label: "Set Roster", href: "/set-roster" }
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
          paddingTop: "2rem",
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
            <GradientText colors={["#fff", "#aaa", "#fff"]}>
              Roster
            </GradientText>
          </h1>

          {loading ? (
            <div className="contact-form-card" style={{ textAlign: "center" }}>
              <p className="info-text">Loading roster data...</p>
            </div>
          ) : !rosterData?.exists ? (
            <div className="contact-form-card" style={{ textAlign: "center" }}>
              <h2
                className="info-subtitle"
                style={{
                  color: "#9ca3af",
                  marginBottom: "1rem",
                  borderBottom: "none",
                }}
              >
                Yet to Set Roster
              </h2>
              <p className="info-text" style={{ color: "#d1d5db" }}>
                No roster has been generated yet. Please set a roster first.
              </p>
              {user?.role === "admin" && (
                <button
                  onClick={() => navigate("/set-roster")}
                  className="form-button"
                  style={{
                    marginTop: "1.5rem",
                    background: "linear-gradient(to right, #ec4899, #8b5cf6)",
                  }}
                >
                  Go to Set Roster
                </button>
              )}
            </div>
          ) : (
            <div className="contact-form-card">
              <h3
                className="info-subtitle"
                style={{
                  marginBottom: "1rem",
                  borderBottom: "2px solid #8b5cf6",
                  paddingBottom: "0.5rem",
                }}
              >
                Current Roster
              </h3>

              <div style={{ marginBottom: "1.5rem" }}>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                    gap: "1rem",
                    marginBottom: "1rem",
                  }}
                >
                  <div
                    style={{
                      background: "rgba(139, 92, 246, 0.2)",
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
                      {rosterData.coverage_percent?.toFixed(1) || 0}%
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
                      {rosterData.filled_slots || 0}/
                      {rosterData.total_slots || 0}
                    </p>
                  </div>
                  <div
                    style={{
                      background: "rgba(236, 72, 153, 0.2)",
                      padding: "1rem",
                      borderRadius: "8px",
                    }}
                  >
                    <p
                      style={{
                        margin: 0,
                        fontSize: "0.9rem",
                        color: "#f472b6",
                      }}
                    >
                      Status
                    </p>
                    <p
                      style={{
                        margin: "0.5rem 0 0 0",
                        fontSize: "1.5rem",
                        fontWeight: "bold",
                        textTransform: "uppercase",
                        color:
                          rosterData.roster_status === "approved"
                            ? "#4ade80"
                            : "#fbbf24",
                      }}
                    >
                      {rosterData.roster_status || "unknown"}
                    </p>
                  </div>
                </div>

                {rosterData.summary && (
                  <div style={{ marginBottom: "1rem" }}>
                    <p
                      style={{
                        margin: "0.5rem 0",
                        fontSize: "0.9rem",
                        color: "#d1d5db",
                      }}
                    >
                      {rosterData.summary}
                    </p>
                  </div>
                )}
              </div>

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
                    background: "linear-gradient(to right, #10b981, #059669)",
                    flex: "1",
                    minWidth: "200px",
                  }}
                >
                  📥 Download Roster (Excel)
                </button>
                {rosterData.report_file && (
                  <button
                    onClick={() => handleDownloadReport(false)}
                    className="form-button"
                    style={{
                      background: "linear-gradient(to right, #3b82f6, #2563eb)",
                      flex: "1",
                      minWidth: "200px",
                    }}
                  >
                    📄 Download Report (Text)
                  </button>
                )}
                {rosterData.report_json_file && (
                  <button
                    onClick={() => handleDownloadReport(true)}
                    className="form-button"
                    style={{
                      background: "linear-gradient(to right, #8b5cf6, #7c3aed)",
                      flex: "1",
                      minWidth: "200px",
                    }}
                  >
                    📊 Download Report (JSON)
                  </button>
                )}
              </div>

              {/* Recommendations */}
              {rosterData?.recommendations &&
                rosterData.recommendations.length > 0 && (
                  <div style={{ marginTop: "1.5rem" }}>
                    <h4
                      className="info-subtitle"
                      style={{ marginBottom: "1rem", fontSize: "1.1rem" }}
                    >
                      Recommendations
                    </h4>
                    <ul style={{ listStyle: "none", padding: 0 }}>
                      {rosterData.recommendations.map((rec, idx) => (
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
          )}
        </div>
      </div>
    </div>
  );
}
