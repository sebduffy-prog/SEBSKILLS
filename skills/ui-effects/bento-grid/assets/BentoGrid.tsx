"use client";
import React, { useRef } from "react";

export type BentoCardProps = {
  children?: React.ReactNode;
  colSpan?: 1 | 2 | 3 | 4;
  rowSpan?: 1 | 2 | 3;
  tilt?: number;
  lift?: number;
  className?: string;
  style?: React.CSSProperties;
};

export function BentoCard({
  children,
  colSpan = 1,
  rowSpan = 1,
  tilt = 6,
  lift = 6,
  className,
  style,
}: BentoCardProps) {
  const ref = useRef<HTMLDivElement | null>(null);

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    const rx = (-py * tilt).toFixed(2);
    const ry = (px * tilt).toFixed(2);
    el.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-${lift}px)`;
  };
  const onLeave = () => {
    const el = ref.current;
    if (el) el.style.transform = "perspective(900px) rotateX(0) rotateY(0) translateY(0)";
  };

  return (
    <div
      ref={ref}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      className={className}
      style={{
        gridColumn: `span ${colSpan}`,
        gridRow: `span ${rowSpan}`,
        borderRadius: 20,
        padding: 24,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.08)",
        backdropFilter: "blur(12px)",
        transformStyle: "preserve-3d",
        transition: "transform 280ms cubic-bezier(0.2, 0.8, 0.2, 1)",
        willChange: "transform",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export type BentoGridProps = {
  children: React.ReactNode;
  columns?: number;
  gap?: number;
  rowHeight?: number | string;
  className?: string;
  style?: React.CSSProperties;
};

export default function BentoGrid({
  children,
  columns = 4,
  gap = 16,
  rowHeight = 180,
  className,
  style,
}: BentoGridProps) {
  return (
    <div
      className={className}
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
        gridAutoRows: typeof rowHeight === "number" ? `${rowHeight}px` : rowHeight,
        gap,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
