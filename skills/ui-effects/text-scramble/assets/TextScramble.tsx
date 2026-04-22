"use client";
import React, { useEffect, useRef, useState } from "react";

export type TextScrambleProps = {
  text: string;
  chars?: string;
  speed?: number;
  revealDelay?: number;
  trigger?: "viewport" | "hover" | "mount";
  threshold?: number;
  once?: boolean;
  className?: string;
  style?: React.CSSProperties;
  as?: keyof JSX.IntrinsicElements;
};

export default function TextScramble({
  text,
  chars = "!<>-_\\/[]{}—=+*^?#________",
  speed = 30,
  revealDelay = 35,
  trigger = "viewport",
  threshold = 0.4,
  once = true,
  className,
  style,
  as = "span",
}: TextScrambleProps) {
  const ref = useRef<HTMLElement | null>(null);
  const [output, setOutput] = useState(text);
  const runningRef = useRef(false);

  const run = () => {
    if (runningRef.current) return;
    runningRef.current = true;
    const len = text.length;
    const queue: { from: string; to: string; start: number; end: number; char?: string }[] = [];
    for (let i = 0; i < len; i++) {
      const from = "";
      const to = text[i];
      const start = Math.floor(Math.random() * (revealDelay * 0.8));
      const end = start + revealDelay + Math.floor(Math.random() * revealDelay);
      queue.push({ from, to, start, end });
    }
    let frame = 0;
    const tick = () => {
      let complete = 0;
      const out: string[] = [];
      for (let i = 0; i < queue.length; i++) {
        const q = queue[i];
        if (frame >= q.end) {
          complete++;
          out.push(q.to);
        } else if (frame >= q.start) {
          if (!q.char || Math.random() < 0.28) {
            q.char = chars[Math.floor(Math.random() * chars.length)];
          }
          out.push(q.char);
        } else {
          out.push(q.from);
        }
      }
      setOutput(out.join(""));
      if (complete === queue.length) {
        runningRef.current = false;
        return;
      }
      frame++;
      setTimeout(tick, speed);
    };
    tick();
  };

  useEffect(() => {
    if (trigger === "mount") {
      run();
      return;
    }
    if (trigger === "viewport") {
      const el = ref.current;
      if (!el) return;
      const io = new IntersectionObserver(
        (entries) => {
          for (const e of entries) {
            if (e.isIntersecting) {
              run();
              if (once) io.disconnect();
            }
          }
        },
        { threshold }
      );
      io.observe(el);
      return () => io.disconnect();
    }
    // trigger === "hover": handled via events below
  }, [trigger, threshold, once, text]);

  const Tag = as as any;
  const hoverProps = trigger === "hover" ? { onMouseEnter: run } : {};

  return (
    <Tag ref={ref as any} className={className} style={style} {...hoverProps}>
      {output}
    </Tag>
  );
}
