import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "./BrandFooter.css";

export default function BrandLogo({ navigateTo = null }) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleClick = () => {
    // If navigateTo prop is provided, use it
    if (navigateTo) {
      navigate(navigateTo);
      return;
    }

    // If on a logged-in page (dashboard, set-roster), navigate to dashboard
    if (
      location.pathname === "/dashboard" ||
      location.pathname === "/set-roster"
    ) {
      navigate("/dashboard");
    } else {
      // Otherwise, navigate to home
      navigate("/");
    }
  };

  return (
    <div className="brand-logo-container" onClick={handleClick}>
      <div className="brand-logo-icon">
        <div className="agent-dot"></div>
        <div className="agent-dot"></div>
        <div className="agent-dot"></div>
        <div className="agent-dot"></div>
        <div className="agent-dot"></div>
      </div>
      <span className="brand-logo-text">
        ROSTER <span className="brand-text-highlight">AI</span>
      </span>
    </div>
  );
}
