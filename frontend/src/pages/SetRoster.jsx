import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import GooeyNav from "../components/GooeyNav";
import GradientText from "../components/GradientText";
import BrandLogo from "../components/BrandLogo";
import { api } from "../services/api";
import "./InfoPage.css"; // Reusing existing premium styles

export default function SetRoster() {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [employeeFile, setEmployeeFile] = useState(null);
    const [storeFile, setStoreFile] = useState(null);
    const [uploadSuccess, setUploadSuccess] = useState(false);
    const [generatedRoster, setGeneratedRoster] = useState(null);

    const handleUpload = async (e) => {
        e.preventDefault();
        if (!employeeFile || !storeFile) {
            alert("Please select both files.");
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
            alert("Files uploaded successfully! You can now generate the roster.");
        } catch (err) {
            console.error("Upload error:", err);
            alert(`Error uploading files: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerate = async () => {
        setLoading(true);
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
            setGeneratedRoster(data);
            alert("Roster Generated Successfully!");
            // Here you could navigate to a Roster View page or show the JSON
        } catch (err) {
            console.error("Generation error:", err);
            alert(`Error generating roster: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    const navItems = [
        { label: "Dashboard", href: "/dashboard" },
        { label: "Set Roster", href: "#" }, 
    { label: "Subscription", href: "/subscription" },
    ];

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
        style={{ justifyContent: "center", height: "100vh", paddingTop: "0" }}
      >
        <div className="info-container" style={{ maxWidth: "600px" }}>
          <h1
            className="info-title"
            style={{ textAlign: "center", marginBottom: "2rem" }}
          >
                        Set Roster
                    </h1>
                    
                    {!uploadSuccess ? (
                        <>
              <p
                className="info-text"
                style={{ textAlign: "center", marginBottom: "2rem" }}
              >
                                Upload the required files to generate the weekly roster.
                            </p>

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
                            
                            <button 
                                onClick={handleGenerate} 
                                className="form-button" 
                                disabled={loading}
                style={{
                  background: "linear-gradient(to right, #ec4899, #8b5cf6)",
                }}
                            >
                                {loading ? "Generating..." : "Generate Roster"}
                            </button>
                            
                            {generatedRoster && (
                <div style={{ marginTop: "1rem", color: "#fff" }}>
                                    <p>Roster generated! (Status: {generatedRoster.status})</p>
                                    {/* Link to view roster could go here */}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
