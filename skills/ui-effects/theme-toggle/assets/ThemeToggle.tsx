"use client";
import React, { useEffect, useState } from "react";

export type ThemeToggleProps = {
  size?: number;
  storageKey?: string;
  target?: "html" | "body";
  attribute?: string;
  lightValue?: string;
  darkValue?: string;
  className?: string;
  style?: React.CSSProperties;
};

type Theme = "light" | "dark";

function getInitial(storageKey: string): Theme {
  if (typeof window === "undefined") return "light";
  const saved = window.localStorage.getItem(storageKey) as Theme | null;
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function ThemeToggle({
  size = 40,
  storageKey = "theme",
  target = "html",
  attribute = "data-theme",
  lightValue = "light",
  darkValue = "dark",
  className,
  style,
}: ThemeToggleProps) {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setTheme(getInitial(storageKey));
    setMounted(true);
  }, [storageKey]);

  useEffect(() => {
    if (!mounted) return;
    const el = target === "html" ? document.documentElement : document.body;
    el.setAttribute(attribute, theme === "dark" ? darkValue : lightValue);
    window.localStorage.setItem(storageKey, theme);
  }, [theme, mounted, target, attribute, lightValue, darkValue, storageKey]);

  const isDark = theme === "dark";

  return (
    <button
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={className}
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        border: "1px solid currentColor",
        background: "transparent",
        color: "currentColor",
        cursor: "pointer",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        padding: 0,
        transition: "transform 300ms cubic-bezier(0.2, 0.8, 0.2, 1)",
        ...style,
      }}
    >
      <svg
        width={size * 0.55}
        height={size * 0.55}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{
          transition: "transform 500ms cubic-bezier(0.2, 0.8, 0.2, 1)",
          transform: isDark ? "rotate(-35deg) scale(0.9)" : "rotate(0) scale(1)",
        }}
      >
        {/* Sun core — shrinks into the moon as theme darkens */}
        <circle
          cx="12"
          cy="12"
          r={isDark ? 8.5 : 5}
          style={{ transition: "r 400ms ease" }}
        />
        {/* Moon "bite" mask — a second circle overlapping to carve a crescent */}
        <circle
          cx={isDark ? 16 : 30}
          cy={isDark ? 9 : 12}
          r={7.5}
          fill="var(--theme-toggle-bg, white)"
          stroke="none"
          style={{ transition: "cx 400ms ease, cy 400ms ease" }}
        />
        {/* Sun rays — fade out in dark mode */}
        {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
          <line
            key={deg}
            x1="12"
            y1="2"
            x2="12"
            y2="4"
            transform={`rotate(${deg} 12 12)`}
            style={{
              transition: "opacity 300ms ease",
              opacity: isDark ? 0 : 1,
            }}
          />
        ))}
      </svg>
    </button>
  );
}
