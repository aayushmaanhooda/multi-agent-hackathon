import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../services/api";
import GradientText from "../components/GradientText";
import GooeyNav from "../components/GooeyNav";
import AdminChat from "../components/AdminChat";
import BrandLogo from "../components/BrandLogo";
import "./Dashboard.css";

export default function Dashboard() {
    const location = useLocation();
    const navigate = useNavigate();
    const [user, setUser] = useState(location.state?.user || null);
    const [loading, setLoading] = useState(!user);

    useEffect(() => {
        if (!user) {
            checkSession();
        }
    }, []);

    const checkSession = async () => {
        try {
            const userData = await api.getMe();
            setUser(userData);
        } catch (err) {
            console.error("Session check failed", err);
      // Redirect to login if not authenticated
      navigate("/login");
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = async () => {
        try {
            await api.logout();
      navigate("/login");
        } catch (err) {
            console.error("Logout failed", err);
        }
    };

    const navItems = [
        { label: "Dashboard", href: "/dashboard" },
    user?.role === "admin"
            ? { label: "Set Roster", href: "/set-roster" }
            : { label: "Rosters", href: "#" },
    { label: "Subscription", href: "/subscription" },
    ];

  return (
    <div className="dashboard-page">
       <div className="dashboard-nav-wrapper">
        <div className="roster-ai-logo">
          <BrandLogo />
        </div>
         <GooeyNav items={navItems} />
        <button
          onClick={handleLogout}
          className="logout-btn"
          style={{
            position: "absolute",
            top: "2rem",
            right: "2rem",
            padding: "0.5rem 1rem",
            background: "rgba(255, 50, 50, 0.2)",
            color: "#fff",
            border: "1px solid rgba(255, 50, 50, 0.5)",
            borderRadius: "8px",
            cursor: "pointer",
            zIndex: 1000,
          }}
        >
            Logout
         </button>
       </div>

      <div className="dashboard-content">
        <div className="dashboard-title-container">
            <h1 className="dashboard-title">
                <GradientText colors={["#fff", "#aaa", "#fff"]}>
                    {user ? `Welcome, ${user.name}` : "Command Center"}
                </GradientText>
            </h1>
          {user && (
            <p
              style={{
                color: "#888",
                marginTop: "0.25rem",
                fontSize: "0.85rem",
              }}
            >
              Role: {user.role}
            </p>
          )}
        </div>

        {/* Admin Chatbot Interface - Full Screen */}
        {user && user.role === "admin" && <AdminChat />}
        
        {/* Placeholder Content */}
        {!user && !loading && (
          <div style={{ textAlign: "center", color: "#666" }}>
                <p>Please login to view dashboard data.</p>
            <button
              onClick={() => navigate("/login")}
              style={{
                marginTop: "1rem",
                padding: "0.5rem 1rem",
                cursor: "pointer",
              }}
            >
              Go to Login
            </button>
            </div>
        )}
      </div>
    </div>
  );
}
