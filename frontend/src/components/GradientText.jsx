import React from 'react';
import './GradientText.css';

export default function GradientText({
  children,
  className = "",
  colors = ["#40ffaa", "#4079ff", "#40ffaa", "#4079ff", "#40ffaa"],
  animationSpeed = 3,
  showBorder = false,
}) {
  const gradientStyle = {
    backgroundImage: `linear-gradient(to right, ${colors.join(", ")})`,
    animation: `gradient-anim ${animationSpeed}s linear infinite`,
  };

  return (
    <div className={`animated-gradient-text ${className}`}>
      <span className="gradient-text-span" style={gradientStyle}>
        {children}
      </span>
      {/* Border implementation omitted for cleaner look as generally handled by wrapper if needed */}
    </div>
  );
}
