"use client";
import React, { useEffect, useRef, useState } from "react";

export type AnimatedCounterProps = {
  to: number;
  from?: number;
  duration?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  locale?: string;
  easing?: (t: number) => number;
  once?: boolean;
  className?: string;
  style?: React.CSSProperties;
};

const easeOutExpo = (t: number) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t));

export default function AnimatedCounter({
  to,
  from = 0,
  duration = 1800,
  decimals = 0,
  prefix = "",
  suffix = "",
  locale,
  easing = easeOutExpo,
  once = true,
  className,
  style,
}: AnimatedCounterProps) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const [value, setValue] = useState(from);
  const hasRun = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const run = () => {
      const start = performance.now();
      const loop = (now: number) => {
        const t = Math.min(1, (now - start) / duration);
        const eased = easing(t);
        setValue(from + (to - from) * eased);
        if (t < 1) requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    };

    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting && (!once || !hasRun.current)) {
            hasRun.current = true;
            run();
            if (once) io.disconnect();
          }
        }
      },
      { threshold: 0.3 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [from, to, duration, easing, once]);

  const formatter = new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  return (
    <span ref={ref} className={className} style={style}>
      {prefix}
      {formatter.format(value)}
      {suffix}
    </span>
  );
}
