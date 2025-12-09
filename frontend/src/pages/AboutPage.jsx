import React from "react";
import BrandLogo from "../components/BrandLogo";
import Footer from "../components/Footer";
import GooeyNav from "../components/GooeyNav";
import "./InfoPage.css";

export default function AboutPage() {
  const navItems = [
    { label: "Home", href: "/" },
    { label: "About", href: "/about" },
    { label: "Contact", href: "/contact" },
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

      <div className="info-container">
        <h1 className="info-title">About Us</h1>
        
        <div className="info-section">
          <h2 className="info-subtitle">Our Mission</h2>
          <p className="info-text">
            At Roster AI, we are revolutionizing workforce management through
            the power of autonomous agents. Our mission is to eliminate manual
            scheduling bottlenecks and empower managers to focus on what truly
            matters—their people and their customers. By leveraging advanced
            algorithms, we predict demand, optimize shifts, and ensure
            compliance instantly.
          </p>
        </div>

        <div className="info-section">
          <h2 className="info-subtitle">The Vision</h2>
          <p className="info-text">
            We envision a future where McDonald's branches operate with seamless
            efficiency. Imagine a world where rosters build themselves,
            conflicts are resolved before they happen, and every employee is
            perfectly matched to their best shifts. That is the future we are
            building today.
          </p>
        </div>

        <div className="info-section">
          <h2 className="info-subtitle">Our Team</h2>
          <div className="info-grid">
            <div className="info-card">
              <h3 className="font-bold text-white mb-1">Aayushmaan Hooda</h3>
              <p className="text-sm text-green-400">Lead Engineer</p>
            </div>
             <div className="info-card">
              <h3 className="font-bold text-white mb-1">AI Agent Alpha</h3>
              <p className="text-sm text-blue-400">Scheduler Bot</p>
            </div>
             <div className="info-card">
              <h3 className="font-bold text-white mb-1">AI Agent Beta</h3>
              <p className="text-sm text-purple-400">Compliance Bot</p>
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
