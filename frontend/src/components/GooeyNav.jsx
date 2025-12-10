import React, { useState } from "react";
import { Link } from "react-router-dom";
import "./GooeyNav.css";

export default function GooeyNav({ items = [], className = "" }) {
  const [activeIndex, setActiveIndex] = useState(null);

  const isInternalLink = (href) => {
    return (
      href && href !== "#" && !href.startsWith("http") && !href.startsWith("#")
    );
  };

  const handleHashClick = (e, href) => {
    if (href && href.startsWith("#")) {
      e.preventDefault();
      const element = document.querySelector(href);
      if (element) {
        element.scrollIntoView({ behavior: "smooth" });
      }
    }
  };

  return (
    <div className={`gooey-nav-container ${className}`}>
      <nav className="glass-nav">
        {items.map((item, index) => {
          const isHashLink = item.href && item.href.startsWith("#");
          const NavComponent = isInternalLink(item.href) ? Link : "a";
          const navProps = isInternalLink(item.href)
            ? { to: item.href }
            : {
                href: item.href,
                onClick: isHashLink
                  ? (e) => handleHashClick(e, item.href)
                  : undefined,
              };

          return (
            <NavComponent
              key={index}
              {...navProps}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseLeave={() => setActiveIndex(null)}
              className="nav-item"
            >
              {item.label}
              {activeIndex === index && <span className="nav-indicator"></span>}
            </NavComponent>
          );
        })}
      </nav>
    </div>
  );
}
