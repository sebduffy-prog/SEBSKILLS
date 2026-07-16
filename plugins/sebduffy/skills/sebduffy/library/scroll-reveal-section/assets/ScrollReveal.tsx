"use client";
import React, { Children, useEffect, useRef, useState } from "react";

export type ScrollRevealProps = {
  children: React.ReactNode;
  direction?: "up" | "down" | "left" | "right" | "none";
  distance?: number;
  duration?: number;
  delay?: number;
  stagger?: number;
  threshold?: number;
  once?: boolean;
  className?: string;
  style?: React.CSSProperties;
};

export default function ScrollReveal({
  children,
  direction = "up",
  distance = 32,
  duration = 700,
  delay = 0,
  stagger = 80,
  threshold = 0.2,
  once = true,
  className,
  style,
}: ScrollRevealProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            setVisible(true);
            if (once) io.disconnect();
          } else if (!once) {
            setVisible(false);
          }
        }
      },
      { threshold }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [threshold, once]);

  const hidden: React.CSSProperties = (() => {
    switch (direction) {
      case "up": return { transform: `translate3d(0, ${distance}px, 0)`, opacity: 0 };
      case "down": return { transform: `translate3d(0, -${distance}px, 0)`, opacity: 0 };
      case "left": return { transform: `translate3d(${distance}px, 0, 0)`, opacity: 0 };
      case "right": return { transform: `translate3d(-${distance}px, 0, 0)`, opacity: 0 };
      default: return { opacity: 0 };
    }
  })();
  const shown: React.CSSProperties = { transform: "translate3d(0,0,0)", opacity: 1 };

  const items = Children.toArray(children);

  return (
    <div ref={ref} className={className} style={style}>
      {items.map((child, i) => (
        <div
          key={i}
          style={{
            transition: `transform ${duration}ms cubic-bezier(0.2,0.8,0.2,1) ${delay + i * stagger}ms, opacity ${duration}ms ease ${delay + i * stagger}ms`,
            willChange: "transform, opacity",
            ...(visible ? shown : hidden),
          }}
        >
          {child}
        </div>
      ))}
    </div>
  );
}
