import React, { useEffect, useRef } from 'react';

/**
 * Orb component.
 * Renders a glowing, moving orb using HTML5 Canvas.
 */
export default function Orb({
  hoverIntensity = 0.5,
  rotateOnHover = true,
  hue = 0,
  forceHoverState = false,
}) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    // Resize handler
    const resizeConsumer = () => {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener('resize', resizeConsumer);
    resizeConsumer();

    let time = 0;
    
    // Gradient colors based on hue
    // hue 0 -> roughly blue/purple/green mix for "Multi-Agent" feel
    const baseHuel = hue || 200; 

    function render() {
      time += 0.01;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      const width = canvas.width;
      const height = canvas.height;
      const centerX = width / 2;
      const centerY = height / 2;
      
      // Ring config
      const ringRadius = Math.min(width, height) * 0.35;
      const ringThickness = 20;

      // Base Hue
      const baseHuel = hue || 200; 
      
      // Floating movement
      const floatX = Math.sin(time) * 20;
      const floatY = Math.cos(time * 0.8) * 20;
      
      const x = centerX + floatX;
      const y = centerY + floatY;

      // Draw Outer Glow (Atmosphere)
      const glowGradient = ctx.createRadialGradient(x, y, ringRadius * 0.8, x, y, ringRadius * 1.5);
      glowGradient.addColorStop(0, `hsla(${baseHuel}, 100%, 50%, 0)`);
      glowGradient.addColorStop(0.5, `hsla(${baseHuel}, 100%, 60%, 0.1)`);
      glowGradient.addColorStop(1, `hsla(${baseHuel}, 100%, 60%, 0)`);
      
      ctx.fillStyle = glowGradient;
      ctx.fillRect(0, 0, width, height);

      // Draw the Ring
      ctx.shadowBlur = 40;
      ctx.shadowColor = `hsla(${baseHuel}, 100%, 70%, 0.6)`;
      ctx.lineWidth = ringThickness;
      
      // Gradient Stroke for the ring
      const strokeGradient = ctx.createLinearGradient(x - ringRadius, y - ringRadius, x + ringRadius, y + ringRadius);
      strokeGradient.addColorStop(0, `hsla(${baseHuel}, 100%, 70%, 1)`);
      strokeGradient.addColorStop(0.5, `hsla(${baseHuel + 40}, 100%, 60%, 1)`);
      strokeGradient.addColorStop(1, `hsla(${baseHuel}, 100%, 70%, 1)`);

      ctx.strokeStyle = strokeGradient;
      ctx.beginPath();
      ctx.arc(x, y, ringRadius, 0, Math.PI * 2);
      ctx.stroke();

      // Reset Shadow
      ctx.shadowBlur = 0;

      animationFrameId = requestAnimationFrame(render);
    }

    render();

    return () => {
      window.removeEventListener('resize', resizeConsumer);
      cancelAnimationFrame(animationFrameId);
    };
  }, [hue]);

  return (
    <canvas 
        ref={canvasRef} 
        style={{ 
            width: '100%', 
            height: '100%', 
            display: 'block' // Remove inline spacing
        }} 
    />
  );
}
