import React from "react";
import { useNavigate } from "react-router-dom";
import GradientText from "../components/GradientText";
import GooeyNav from "../components/GooeyNav";
import Footer from "../components/Footer";
import BrandLogo from "../components/BrandLogo";
import AboutSection from "../components/AboutSection";
import ContactSection from "../components/ContactSection";
import SubscriptionSection from "../components/SubscriptionSection";
import "./LandingPage.css";

export default function LandingPage() {
  const navigate = useNavigate();

  const navItems = [
    { label: "Home", href: "#home" },
    { label: "About", href: "#about" },
    { label: "Contact", href: "#contact" },
    { label: "Subscription", href: "/subscription" },
  ];

  return (
    <div className="landing-page-container">
      <BrandLogo />
      {/* Navbar - Fixed Position */}
      <div className="landing-nav-wrapper">
        <GooeyNav items={navItems} />
      </div>

      {/* Section 1: Hero */}
      <section id="home" className="landing-section hero-section">
        <div className="hero-content">
          <div className="hero-inner">
            <h2 className="branch-name">McDonald's Branch Management</h2>

            <div className="main-title">
              <GradientText
                colors={["#40ffaa", "#4079ff", "#40ffaa", "#4079ff", "#40ffaa"]}
                animationSpeed={5}
                showBorder={false}
              >
                Multi-Agent Roster Builder
              </GradientText>
            </div>

            <p className="subtitle">
              Harness the power of AI Agents to optimize your workforce
              scheduling. Autonomous, efficient, and futuristic.
            </p>

            <div className="cta-buttons">
              <button
                onClick={() => navigate("/register")}
                className="btn-primary"
              >
                Get Started
              </button>

              <button
                onClick={() => navigate("/login")}
                className="btn-secondary"
              >
                Login
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: About */}
      <AboutSection />

      {/* Section 3: Subscription */}
      <SubscriptionSection />

      {/* Section 4: Contact */}
      <ContactSection />

      <Footer />
    </div>
  );
}
