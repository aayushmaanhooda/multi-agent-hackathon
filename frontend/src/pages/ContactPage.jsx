import React from "react";
import BrandLogo from "../components/BrandLogo";
import Footer from "../components/Footer";
import GooeyNav from "../components/GooeyNav";
import { Mail, Phone, MapPin, Bot } from "lucide-react";
import "./InfoPage.css";

export default function ContactPage() {
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
        <h1 className="info-title">Contact Us</h1>
        
        <div className="split-layout">
            {/* Left Column: Contact Info */}
            <div className="info-section">
              <h2 className="info-subtitle">Get in Touch</h2>
              <p className="info-text mb-8">
              Ready to transform your workforce management? Our team represents
              the intersection of human expertise and AI efficiency. Reach out
              for demos, support, or partnership opportunities.
              </p>

              <div className="space-y-6">
                  <div className="contact-item">
                <div className="contact-icon">
                  <Mail size={20} />
                </div>
                    <div>
                        <p className="text-sm text-gray-400">General Inquiries</p>
                        <p className="text-lg">support@roster.ai</p>
                    </div>
                  </div>

                  <div className="contact-item">
                <div className="contact-icon">
                  <Phone size={20} />
                </div>
                    <div>
                         <p className="text-sm text-gray-400">24/7 Support Line</p>
                         <p className="text-lg">+61 (2) 1234 5678</p>
                    </div>
                  </div>

                  <div className="contact-item">
                <div className="contact-icon">
                  <MapPin size={20} />
                </div>
                     <div>
                         <p className="text-sm text-gray-400">Sydney HQ</p>
                         <p className="text-lg">100 George Street, Sydney NSW 2000</p>
                    </div>
                  </div>
                  
                  <div className="contact-item">
                <div className="contact-icon">
                  <Bot size={20} />
                </div>
                     <div>
                         <p className="text-sm text-gray-400">AI Agent Support</p>
                         <p className="text-lg">Live Chat (Available in Dashboard)</p>
                    </div>
                  </div>
              </div>
            </div>

            {/* Right Column: Expanded Form */}
            <div className="info-section contact-form-card">
                <h2 className="info-subtitle mb-6 border-none">Send a Message</h2>
                <form className="space-y-4">
                    <div className="form-row">
                        <div className="form-group">
                            <label className="form-label">First Name</label>
                  <input
                    type="text"
                    placeholder="Jane"
                    className="form-input"
                  />
                        </div>
                        <div className="form-group">
                            <label className="form-label">Last Name</label>
                            <input type="text" placeholder="Doe" className="form-input" />
                        </div>
                    </div>
                    
                    <div className="form-group">
                        <label className="form-label">Email Address</label>
                <input
                  type="email"
                  placeholder="jane@company.com"
                  className="form-input"
                />
                    </div>
                    
                    <div className="form-group">
                        <label className="form-label">Subject</label>
                         <select className="form-select">
                            <option>Demo Request</option>
                            <option>Technical Support</option>
                            <option>Billing Inquiry</option>
                            <option>Partnership</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label className="form-label">Message</label>
                <textarea
                  placeholder="Tell us about your requirements..."
                  rows="3"
                  className="form-textarea"
                ></textarea>
                    </div>
                    
              <button className="form-button">Submit Inquiry</button>
                </form>
            </div>
        </div>
      </div>
      <Footer />
    </div>
  );
}
