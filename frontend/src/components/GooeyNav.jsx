import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './GooeyNav.css';

export default function GooeyNav({ items = [], className = "" }) {
  const [activeIndex, setActiveIndex] = useState(null);

  return (
    <div className={`gooey-nav-container ${className}`}>
      <nav className="glass-nav">
        {items.map((item, index) => (
          <a
            key={index}
            href={item.href}
            onMouseEnter={() => setActiveIndex(index)}
            onMouseLeave={() => setActiveIndex(null)}
            className="nav-item"
            onClick={(e) => {
               // Smooth scroll behavior is handled by CSS, but good to be explicit
            }}
          >
            {item.label}
             {activeIndex === index && (
                <span className="nav-indicator"></span>
             )}
          </a>
        ))}
      </nav>
    </div>
  );
}
