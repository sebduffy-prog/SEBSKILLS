"use client";
import React, { useEffect, useRef } from "react";

export type MagneticCursorProps = {
  size?: number;
  color?: string;
  blendMode?: React.CSSProperties["mixBlendMode"];
  hoverScale?: number;
  hoverSelector?: string;
  hideNativeCursor?: boolean;
  stiffness?: number;
  damping?: number;
};

export default function MagneticCursor({
  size = 20,
  color = "white",
  blendMode = "difference",
  hoverScale = 2.8,
  hoverSelector = "a, button, [data-cursor]",
  hideNativeCursor = true,
  stiffness = 0.18,
  damping = 0.75,
}: MagneticCursorProps) {
  const dotRef = useRef<HTMLDivElement | null>(null);
  const pos = useRef({ x: -100, y: -100 });
  const cur = useRef({ x: -100, y: -100, vx: 0, vy: 0 });
  const scale = useRef(1);
  const targetScale = useRef(1);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.matchMedia("(pointer: coarse)").matches) return;

    const onMove = (e: MouseEvent) => {
      pos.current = { x: e.clientX, y: e.clientY };
    };
    const onDown = () => (targetScale.current = 0.8);
    const onUp = () => {
      targetScale.current = hoveringRef.current ? hoverScale : 1;
    };

    const hoveringRef = { current: false };
    const onOver = (e: MouseEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && t.closest(hoverSelector)) {
        hoveringRef.current = true;
        targetScale.current = hoverScale;
      }
    };
    const onOut = (e: MouseEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && t.closest(hoverSelector)) {
        hoveringRef.current = false;
        targetScale.current = 1;
      }
    };

    const tick = () => {
      const c = cur.current;
      c.vx = (c.vx + (pos.current.x - c.x) * stiffness) * damping;
      c.vy = (c.vy + (pos.current.y - c.y) * stiffness) * damping;
      c.x += c.vx;
      c.y += c.vy;
      scale.current += (targetScale.current - scale.current) * 0.15;
      const d = dotRef.current;
      if (d) {
        d.style.transform = `translate3d(${c.x - size / 2}px, ${c.y - size / 2}px, 0) scale(${scale.current.toFixed(3)})`;
      }
      raf.current = requestAnimationFrame(tick);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mousedown", onDown);
    window.addEventListener("mouseup", onUp);
    document.addEventListener("mouseover", onOver);
    document.addEventListener("mouseout", onOut);
    raf.current = requestAnimationFrame(tick);

    if (hideNativeCursor) document.documentElement.style.cursor = "none";

    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mousedown", onDown);
      window.removeEventListener("mouseup", onUp);
      document.removeEventListener("mouseover", onOver);
      document.removeEventListener("mouseout", onOut);
      if (raf.current) cancelAnimationFrame(raf.current);
      if (hideNativeCursor) document.documentElement.style.cursor = "";
    };
  }, [size, hoverScale, hoverSelector, hideNativeCursor, stiffness, damping]);

  return (
    <div
      ref={dotRef}
      aria-hidden
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: size,
        height: size,
        borderRadius: "50%",
        background: color,
        mixBlendMode: blendMode,
        pointerEvents: "none",
        zIndex: 9999,
        willChange: "transform",
      }}
    />
  );
}
