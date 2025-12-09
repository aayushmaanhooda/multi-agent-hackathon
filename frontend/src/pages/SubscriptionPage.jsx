import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import BrandLogo from "../components/BrandLogo";
import GooeyNav from "../components/GooeyNav";
import Footer from "../components/Footer";
import {
  Check,
  Zap,
  Crown,
  FileText,
  Shield,
  CreditCard,
  RefreshCw,
} from "lucide-react";
import { api } from "../services/api";
import "./SubscriptionPage.css";

export default function SubscriptionPage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Check if user is logged in
    const checkUser = async () => {
      try {
        const userData = await api.getMe();
        setUser(userData);
      } catch (err) {
        // User not logged in, that's fine
      }
    };
    checkUser();
  }, []);

  const navItems = user
    ? [
        { label: "Dashboard", href: "/dashboard" },
        user.role === "admin"
          ? { label: "Set Roster", href: "/set-roster" }
          : { label: "Rosters", href: "#" },
        { label: "Subscription", href: "/subscription" },
      ]
    : [
        { label: "Home", href: "/" },
        { label: "About", href: "/about" },
        { label: "Contact", href: "/contact" },
        { label: "Subscription", href: "/subscription" },
      ];

  const plans = [
    {
      name: "Free",
      price: "$0",
      period: "Forever",
      icon: <Zap size={26} />,
      features: [
        "14 days knowledge base access",
        "Basic chat functionality",
        "Limited roster queries",
        "Community support",
      ],
      gradient: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      popular: false,
    },
    {
      name: "Premium",
      price: "$29",
      period: "per month",
      icon: <Zap size={26} />,
      features: [
        "Last 3 months historical data",
        "Advanced chat features",
        "Extended roster queries",
        "Priority support",
        "Export capabilities",
      ],
      gradient: "linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)",
      popular: true,
    },
    {
      name: "Ultra",
      price: "$99",
      period: "per month",
      icon: <Crown size={26} />,
      features: [
        "Unlimited chat window access",
        "Full historical data access",
        "Unlimited roster queries",
        "24/7 priority support",
        "Advanced analytics",
        "API access",
        "Custom integrations",
      ],
      gradient: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
      popular: false,
    },
  ];

  return (
    <div className="subscription-page">
      <div className="subscription-nav-wrapper">
        <div className="roster-ai-logo">
          <BrandLogo />
        </div>
        <GooeyNav items={navItems} />
      </div>

      <div className="subscription-container">
        <div className="subscription-header">
          <h1 className="subscription-title">Choose Your Plan</h1>
          <p className="subscription-subtitle">
            Unlock advanced chatbot features with our flexible subscription
            plans
          </p>
        </div>

        <div className="subscription-plans">
          {plans.map((plan, index) => (
            <div
              key={index}
              className={`subscription-card ${plan.popular ? "popular" : ""}`}
            >
              {plan.popular && (
                <div className="popular-badge">Most Popular</div>
              )}
              <div className="plan-icon" style={{ background: plan.gradient }}>
                {plan.icon}
              </div>
              <h2 className="plan-name">{plan.name}</h2>
              <div className="plan-price">
                <span className="price-amount">{plan.price}</span>
                <span className="price-period">/{plan.period}</span>
              </div>
              <ul className="plan-features">
                {plan.features.map((feature, idx) => (
                  <li key={idx} className="feature-item">
                    <Check size={18} className="check-icon" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
              <button
                className="plan-button"
                style={{ background: plan.gradient }}
                onClick={() => {
                  // Handle subscription logic here
                  alert(`${plan.name} plan selected!`);
                }}
              >
                {plan.name === "Free" ? "Get Started" : "Subscribe Now"}
              </button>
            </div>
          ))}
        </div>

        <div className="subscription-info">
          <h3>All plans include:</h3>
          <div className="info-grid">
            <div className="info-item">
              <Check size={20} />
              <span>Secure data encryption</span>
            </div>
            <div className="info-item">
              <Check size={20} />
              <span>Regular updates</span>
            </div>
            <div className="info-item">
              <Check size={20} />
              <span>Mobile access</span>
            </div>
            <div className="info-item">
              <Check size={20} />
              <span>Basic analytics</span>
            </div>
          </div>
        </div>

        <div className="policy-section">
          <h2>Terms & Policies</h2>
          <div className="policy-grid">
            <div className="policy-card">
              <h3>
                <FileText size={18} />
                Subscription Terms
              </h3>
              <ul>
                <li>Subscriptions are billed monthly or annually</li>
                <li>All plans auto-renew unless cancelled</li>
                <li>You can cancel anytime from your dashboard</li>
                <li>No refunds for partial billing periods</li>
                <li>Price changes will be notified 30 days in advance</li>
              </ul>
            </div>

            <div className="policy-card">
              <h3>
                <Shield size={18} />
                Privacy & Data
              </h3>
              <ul>
                <li>Your data is encrypted and securely stored</li>
                <li>We never share your information with third parties</li>
                <li>You can export your data at any time</li>
                <li>Data retention follows your subscription tier</li>
                <li>GDPR compliant data handling</li>
              </ul>
            </div>

            <div className="policy-card">
              <h3>
                <CreditCard size={18} />
                Payment & Billing
              </h3>
              <ul>
                <li>Payments processed securely via Stripe</li>
                <li>Accepted payment methods: Credit/Debit cards</li>
                <li>Invoices available in your account</li>
                <li>Failed payments result in service suspension</li>
                <li>Contact support for billing inquiries</li>
              </ul>
            </div>

            <div className="policy-card">
              <h3>
                <RefreshCw size={18} />
                Cancellation & Refunds
              </h3>
              <ul>
                <li>Cancel anytime from subscription settings</li>
                <li>Service continues until end of billing period</li>
                <li>No refunds for used subscription periods</li>
                <li>Downgrades take effect on next billing cycle</li>
                <li>Upgrades take effect immediately</li>
              </ul>
            </div>

            <div className="policy-card">
              <h3>
                <Zap size={18} />
                Service Usage
              </h3>
              <ul>
                <li>Fair use policy applies to all tiers</li>
                <li>Abuse may result in account suspension</li>
                <li>API rate limits based on subscription tier</li>
                <li>Support response time varies by plan</li>
                <li>Service availability: 99.9% uptime SLA</li>
              </ul>
            </div>

            <div className="policy-card">
              <h3>
                <Shield size={18} />
                Account Security
              </h3>
              <ul>
                <li>You are responsible for account security</li>
                <li>Use strong, unique passwords</li>
                <li>Enable two-factor authentication when available</li>
                <li>Report suspicious activity immediately</li>
                <li>We monitor for unauthorized access</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
