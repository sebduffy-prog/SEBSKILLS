"use client";
import React, { useMemo } from "react";

export type AuroraGradientProps = {
  colors?: string[];
  speed?: number;
  blur?: number;
  opacity?: number;
  blendMode?: React.CSSProperties["mixBlendMode"];
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
};

export default function AuroraGradient({
  colors = ["#7c3aed", "#ec4899", "#06b6d4", "#f59e0b"],
  speed = 18,
  blur = 80,
  opacity = 0.8,
  blendMode = "screen",
  className,
  style,
  children,
}: AuroraGradientProps) {
  const id = useMemo(() => `aurora-${Math.random().toString(36).slice(2, 9)}`, []);

  const blobs = colors.map((c, i) => {
    const delay = (i * speed) / colors.length;
    const size = 45 + (i % 3) * 15;
    return { color: c, delay, size, i };
  });

  return (
    <div
      className={className}
      style={{
        position: "relative",
        overflow: "hidden",
        isolation: "isolate",
        ...style,
      }}
    >
      <div
        aria-hidden
        style={{
          position: "absolute",
          inset: 0,
          filter: `blur(${blur}px)`,
          opacity,
          zIndex: 0,
        }}
      >
        {blobs.map((b) => (
          <span
            key={b.i}
            style={{
              position: "absolute",
              width: `${b.size}%`,
              aspectRatio: "1 / 1",
              borderRadius: "50%",
              background: b.color,
              mixBlendMode: blendMode,
              animation: `${id}-drift ${speed}s ease-in-out ${b.delay}s infinite alternate`,
              top: `${(b.i * 23) % 60}%`,
              left: `${(b.i * 37) % 60}%`,
            }}
          />
        ))}
      </div>
      <style>{`
        @keyframes ${id}-drift {
          0%   { transform: translate(0%, 0%)   scale(1); }
          25%  { transform: translate(20%, -10%) scale(1.15); }
          50%  { transform: translate(-15%, 25%) scale(0.9); }
          75%  { transform: translate(10%, 15%)  scale(1.1); }
          100% { transform: translate(-20%, -5%) scale(1.05); }
        }
      `}</style>
      <div style={{ position: "relative", zIndex: 1 }}>{children}</div>
    </div>
  );
}
