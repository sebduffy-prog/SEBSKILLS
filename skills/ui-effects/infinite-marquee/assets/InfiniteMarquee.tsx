"use client";
import React, { Children, useMemo } from "react";

export type InfiniteMarqueeProps = {
  children: React.ReactNode;
  speed?: number;
  direction?: "left" | "right";
  pauseOnHover?: boolean;
  gap?: number;
  fade?: boolean;
  fadeColor?: string;
  className?: string;
  style?: React.CSSProperties;
};

export default function InfiniteMarquee({
  children,
  speed = 40,
  direction = "left",
  pauseOnHover = true,
  gap = 32,
  fade = true,
  fadeColor = "white",
  className,
  style,
}: InfiniteMarqueeProps) {
  const id = useMemo(() => `mq-${Math.random().toString(36).slice(2, 9)}`, []);
  const items = Children.toArray(children);
  const from = direction === "left" ? "0%" : "-50%";
  const to = direction === "left" ? "-50%" : "0%";

  return (
    <div
      className={className}
      style={{
        position: "relative",
        overflow: "hidden",
        width: "100%",
        ...style,
      }}
    >
      <div
        style={{
          display: "flex",
          width: "max-content",
          gap: `${gap}px`,
          animation: `${id}-scroll ${speed}s linear infinite`,
        }}
        data-mq-track
      >
        {[...items, ...items].map((child, i) => (
          <div key={i} style={{ flex: "none" }}>
            {child}
          </div>
        ))}
      </div>
      {fade && (
        <>
          <div
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              left: 0,
              width: 80,
              pointerEvents: "none",
              background: `linear-gradient(to right, ${fadeColor}, transparent)`,
            }}
          />
          <div
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              right: 0,
              width: 80,
              pointerEvents: "none",
              background: `linear-gradient(to left, ${fadeColor}, transparent)`,
            }}
          />
        </>
      )}
      <style>{`
        @keyframes ${id}-scroll {
          from { transform: translate3d(${from}, 0, 0); }
          to   { transform: translate3d(${to}, 0, 0); }
        }
        ${pauseOnHover ? `.${id}:hover [data-mq-track] { animation-play-state: paused; }` : ""}
      `}</style>
      <div className={id} style={{ position: "absolute", inset: 0, pointerEvents: pauseOnHover ? "auto" : "none" }} />
    </div>
  );
}
