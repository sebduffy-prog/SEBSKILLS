"use client";
import React, { useEffect, useRef } from "react";

export type MagneticButtonProps = {
  children: React.ReactNode;
  strength?: number;
  radius?: number;
  stiffness?: number;
  damping?: number;
  as?: keyof JSX.IntrinsicElements;
  onClick?: (e: React.MouseEvent) => void;
  className?: string;
  style?: React.CSSProperties;
};

export default function MagneticButton({
  children,
  strength = 0.4,
  radius = 120,
  stiffness = 0.12,
  damping = 0.7,
  as = "button",
  onClick,
  className,
  style,
}: MagneticButtonProps) {
  const ref = useRef<HTMLElement | null>(null);
  const targetRef = useRef({ x: 0, y: 0 });
  const currentRef = useRef({ x: 0, y: 0, vx: 0, vy: 0 });
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const onMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      const dist = Math.hypot(dx, dy);
      if (dist < radius) {
        targetRef.current = { x: dx * strength, y: dy * strength };
      } else {
        targetRef.current = { x: 0, y: 0 };
      }
    };
    const onLeave = () => {
      targetRef.current = { x: 0, y: 0 };
    };

    const tick = () => {
      const cur = currentRef.current;
      const t = targetRef.current;
      cur.vx = (cur.vx + (t.x - cur.x) * stiffness) * damping;
      cur.vy = (cur.vy + (t.y - cur.y) * stiffness) * damping;
      cur.x += cur.vx;
      cur.y += cur.vy;
      el.style.transform = `translate3d(${cur.x.toFixed(2)}px, ${cur.y.toFixed(2)}px, 0)`;
      rafRef.current = requestAnimationFrame(tick);
    };

    window.addEventListener("mousemove", onMove);
    el.addEventListener("mouseleave", onLeave);
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      window.removeEventListener("mousemove", onMove);
      el.removeEventListener("mouseleave", onLeave);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [radius, strength, stiffness, damping]);

  const Tag = as as any;
  return (
    <Tag
      ref={ref as any}
      onClick={onClick}
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "14px 28px",
        borderRadius: 999,
        border: "1px solid rgba(255,255,255,0.2)",
        background: "rgba(255,255,255,0.08)",
        color: "white",
        cursor: "pointer",
        willChange: "transform",
        ...style,
      }}
    >
      <span style={{ display: "inline-block", pointerEvents: "none" }}>{children}</span>
    </Tag>
  );
}
