import React from "react";
import { useNavigate } from "react-router-dom";
import { Check, Zap, Crown } from "lucide-react";
import "./SubscriptionSection.css";

export default function SubscriptionSection() {
  const navigate = useNavigate();

  const plans = [
    {
      name: "Free",
      price: "$0",
      period: "Forever",
      icon: <Zap size={28} />,
      features: ["14 days knowledge base", "Basic chat functionality"],
      gradient: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    },
    {
      name: "Premium",
      price: "$29",
      period: "per month",
      icon: <Zap size={28} />,
      features: ["Last 3 months data", "Advanced chat features"],
      gradient: "linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)",
      popular: true,
    },
    {
      name: "Ultra",
      price: "$99",
      period: "per month",
      icon: <Crown size={28} />,
      features: ["Unlimited access", "Full historical data"],
      gradient: "linear-gradient(135deg, #3b82f6 0%, #10b981 100%)",
    },
  ];

  return (
    <section id="subscription" className="subscription-section">
      <div className="subscription-section-content">
        <h2 className="subscription-section-title">
          Unlock Advanced Chatbot Features
        </h2>
        <p className="subscription-section-subtitle">
          Choose the perfect plan for your roster management needs
        </p>

        <div className="subscription-section-plans">
          {plans.map((plan, index) => (
            <div key={index} className="subscription-section-card">
              {plan.popular && (
                <div className="section-popular-badge">Popular</div>
              )}
              <div
                className="section-plan-icon"
                style={{ background: plan.gradient }}
              >
                {plan.icon}
              </div>
              <h3 className="section-plan-name">{plan.name}</h3>
              <div className="section-plan-price">
                <span className="section-price-amount">{plan.price}</span>
                <span className="section-price-period">/{plan.period}</span>
              </div>
              <ul className="section-plan-features">
                {plan.features.map((feature, idx) => (
                  <li key={idx}>
                    <Check size={16} />
                    {feature}
                  </li>
                ))}
              </ul>
              <button
                className="section-plan-button"
                style={{ background: plan.gradient }}
                onClick={() => navigate("/subscription")}
              >
                Learn More
              </button>
            </div>
          ))}
        </div>

        <button
          className="view-all-plans-btn"
          onClick={() => navigate("/subscription")}
        >
          View All Plans & Features
        </button>
      </div>
    </section>
  );
}
