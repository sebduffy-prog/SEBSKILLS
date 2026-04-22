"use client";

import * as React from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useReducedMotion,
  MotionValue,
} from "framer-motion";

/* ============================================================================
 * ImageShatter — tile-grid hover shatter effect with spring physics + magnet.
 * Adapted from the Framer Image_Shatter module.
 * Requires framer-motion.
 * ============================================================================ */

/** Simple seeded RNG for stable tile targets. */
function makeRng(seed: number) {
  let s = seed || 1;
  return () => (s = (s * 1664525 + 1013904223) % 4294967296) / 4294967296;
}

type FitMode = "cover" | "contain" | "fill" | "none" | "scale-down";

function normalizeFit(fit?: string): FitMode {
  const f = (fit || "cover").toLowerCase();
  if (f === "fit") return "contain";
  if (f === "stretch") return "fill";
  if (["cover", "contain", "fill", "none", "scale-down"].includes(f)) return f as FitMode;
  return "cover";
}

/** Compute object-fit: returns image size inside container and its top-left position. */
function computeObjectFit(
  natural: { w: number; h: number },
  w: number,
  h: number,
  posX: number,
  posY: number,
  fit: string,
) {
  const mode = normalizeFit(fit);
  const nw = Math.max(1, natural.w);
  const nh = Math.max(1, natural.h);
  let scaledW = nw;
  let scaledH = nh;
  let imgLeft = 0;
  let imgTop = 0;
  let resolved: FitMode = mode;

  if (mode === "scale-down") resolved = nw <= w && nh <= h ? "none" : "contain";

  if (resolved === "fill") {
    scaledW = w;
    scaledH = h;
  } else if (resolved === "contain") {
    const s = Math.min(w / nw, h / nh);
    scaledW = nw * s;
    scaledH = nh * s;
    imgLeft = (w - scaledW) * posX;
    imgTop = (h - scaledH) * posY;
  } else if (resolved === "cover") {
    const s = Math.max(w / nw, h / nh);
    scaledW = nw * s;
    scaledH = nh * s;
    imgLeft = -(scaledW - w) * posX;
    imgTop = -(scaledH - h) * posY;
  } else if (resolved === "none") {
    scaledW = nw;
    scaledH = nh;
    imgLeft = (w - scaledW) * posX;
    imgTop = (h - scaledH) * posY;
  }
  return { scaledW, scaledH, imgLeft, imgTop, mode: resolved };
}

interface TileProps {
  i: number;
  left: number;
  top: number;
  width: number;
  height: number;
  centerX: number;
  centerY: number;
  target: { x: number; y: number; r: number };
  hoverMV: MotionValue<number>;
  cursorX: MotionValue<number>;
  cursorY: MotionValue<number>;
  stiffness: number;
  damping: number;
  magnetStrength: number;
  magnetRadius: number;
  bleed: number;
  bgUrl: string;
  bgSizeW: number;
  bgSizeH: number;
  imgLeft: number;
  imgTop: number;
}

function Tile({
  i,
  left,
  top,
  width,
  height,
  centerX,
  centerY,
  target,
  hoverMV,
  cursorX,
  cursorY,
  stiffness,
  damping,
  magnetStrength,
  magnetRadius,
  bleed,
  bgUrl,
  bgSizeW,
  bgSizeH,
  imgLeft,
  imgTop,
}: TileProps) {
  const baseX = useTransform(hoverMV, (h) => h * target.x);
  const baseY = useTransform(hoverMV, (h) => h * target.y);
  const baseR = useTransform(hoverMV, (h) => h * target.r);

  const magX = useTransform([hoverMV, cursorX, cursorY], ([h, mx, my]: number[]) => {
    if (!h || magnetStrength <= 0) return 0;
    const dx = mx - centerX;
    const dy = my - centerY;
    const dist = Math.max(1, Math.hypot(dx, dy));
    if (dist > magnetRadius) return 0;
    const falloff = 1 - dist / magnetRadius;
    const mag = magnetStrength * falloff;
    return (dx / dist) * mag;
  });
  const magY = useTransform([hoverMV, cursorX, cursorY], ([h, mx, my]: number[]) => {
    if (!h || magnetStrength <= 0) return 0;
    const dx = mx - centerX;
    const dy = my - centerY;
    const dist = Math.max(1, Math.hypot(dx, dy));
    if (dist > magnetRadius) return 0;
    const falloff = 1 - dist / magnetRadius;
    const mag = magnetStrength * falloff;
    return (dy / dist) * mag;
  });

  const rawX = useTransform([baseX, magX], ([b, m]: number[]) => b + m);
  const rawY = useTransform([baseY, magY], ([b, m]: number[]) => b + m);
  const x = useSpring(rawX, { stiffness, damping, restDelta: 0.01 });
  const y = useSpring(rawY, { stiffness, damping, restDelta: 0.01 });
  const r = useSpring(baseR, { stiffness, damping, restDelta: 0.01 });

  const style: React.CSSProperties = {
    position: "absolute",
    left: left - bleed,
    top: top - bleed,
    width: width + bleed * 2,
    height: height + bleed * 2,
    backgroundImage: bgUrl ? `url("${bgUrl}")` : undefined,
    backgroundRepeat: "no-repeat",
    backgroundSize: `${bgSizeW}px ${bgSizeH}px`,
    backgroundPosition: `${imgLeft - (left - bleed)}px ${imgTop - (top - bleed)}px`,
    pointerEvents: "none",
    backfaceVisibility: "hidden",
    transformStyle: "flat",
    willChange: "transform",
  };

  return <motion.div key={i} style={{ ...style, x, y, rotate: r }} />;
}

export interface ImageShatterImage {
  src: string;
  alt?: string;
  srcSet?: string;
  positionX?: string;
  positionY?: string;
  fit?: string;
}

export interface ImageShatterProps {
  image: ImageShatterImage;
  imageFit?: FitMode;
  tilesX?: number;
  tilesY?: number;
  maxOffset?: number;
  maxRotate?: number;
  seed?: number;
  springStiffness?: number;
  springDamping?: number;
  magnetStrength?: number;
  reassembleDelay?: number;
  dprCap?: number;
  magnetRadius?: number;
  responsiveTiles?: boolean;
  style?: React.CSSProperties;
  className?: string;
}

export default function ImageShatter({
  image,
  imageFit = "cover",
  tilesX = 14,
  tilesY = 8,
  maxOffset = 120,
  maxRotate = 18,
  seed = 42,
  springStiffness = 220,
  springDamping = 22,
  magnetStrength = 0,
  reassembleDelay = 0,
  dprCap = 1.5,
  magnetRadius = 200,
  responsiveTiles = true,
  style,
  className,
}: ImageShatterProps) {
  const rootRef = React.useRef<HTMLDivElement>(null);
  const [size, setSize] = React.useState({ w: 600, h: 360 });

  // Measure container.
  React.useLayoutEffect(() => {
    const el = rootRef.current;
    if (!el) return;
    const update = () => setSize({ w: Math.max(1, el.clientWidth), h: Math.max(1, el.clientHeight) });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Load image.
  const [natural, setNatural] = React.useState<{ w: number; h: number } | null>(null);
  const [bgUrl, setBgUrl] = React.useState<string | null>(null);
  const imgSrc = image?.src ?? "";
  const imgAlt = image?.alt ?? "";

  React.useEffect(() => {
    let cancelled = false;
    const i = new Image();
    i.crossOrigin = "anonymous";
    if (image?.srcSet) i.srcset = image.srcSet;
    i.src = imgSrc;
    const onReady = () => {
      if (cancelled) return;
      setNatural({ w: i.naturalWidth || 1, h: i.naturalHeight || 1 });
      setBgUrl(i.currentSrc || i.src);
    };
    if (i.complete) onReady();
    else i.onload = onReady;
    return () => {
      cancelled = true;
      i.onload = null;
    };
  }, [imgSrc, image?.srcSet]);

  const dpr =
    typeof window !== "undefined"
      ? Math.min(window.devicePixelRatio || 1, Math.max(1, dprCap))
      : 1;

  const txRaw = Math.max(2, Math.floor(tilesX));
  const tyRaw = Math.max(2, Math.floor(tilesY));
  const tx = responsiveTiles && size.w < 640 ? Math.max(2, Math.floor(txRaw * 0.7)) : txRaw;
  const ty = responsiveTiles && size.w < 640 ? Math.max(2, Math.floor(tyRaw * 0.7)) : tyRaw;

  const Nw = Math.max(1, Math.round(size.w * dpr));
  const Nh = Math.max(1, Math.round(size.h * dpr));

  const colEdges = React.useMemo(() => {
    const edges = new Array(tx + 1);
    for (let i = 0; i <= tx; i++) edges[i] = Math.floor((i * Nw) / tx) / dpr;
    edges[tx] = Nw / dpr;
    return edges;
  }, [tx, Nw, dpr]);

  const rowEdges = React.useMemo(() => {
    const edges = new Array(ty + 1);
    for (let i = 0; i <= ty; i++) edges[i] = Math.floor((i * Nh) / ty) / dpr;
    edges[ty] = Nh / dpr;
    return edges;
  }, [ty, Nh, dpr]);

  const posX =
    image?.positionX && image.positionX.endsWith("%")
      ? Math.min(1, Math.max(0, parseFloat(image.positionX) / 100))
      : 0.5;
  const posY =
    image?.positionY && image.positionY.endsWith("%")
      ? Math.min(1, Math.max(0, parseFloat(image.positionY) / 100))
      : 0.5;

  const layout = React.useMemo(() => {
    if (!natural) return null;
    const chosenFit = imageFit ?? image?.fit ?? "cover";
    const raw = computeObjectFit(natural, size.w, size.h, posX, posY, chosenFit);
    const scaledW = Math.round(raw.scaledW * dpr) / dpr;
    const scaledH = Math.round(raw.scaledH * dpr) / dpr;
    const imgLeft = Math.round(raw.imgLeft * dpr) / dpr;
    const imgTop = Math.round(raw.imgTop * dpr) / dpr;
    return { ...raw, scaledW, scaledH, imgLeft, imgTop };
  }, [natural, size.w, size.h, posX, posY, imageFit, image?.fit, dpr]);

  const BLEED = 1;

  const targets = React.useMemo(() => {
    const rng = makeRng(seed || 1);
    const arr: { x: number; y: number; r: number }[] = [];
    for (let i = 0; i < tx * ty; i++) {
      const a = rng() * Math.PI * 2;
      const d = rng() * maxOffset;
      arr.push({ x: Math.cos(a) * d, y: Math.sin(a) * d, r: (rng() * 2 - 1) * maxRotate });
    }
    return arr;
  }, [tx, ty, maxOffset, maxRotate, seed]);

  const cursorX = useMotionValue(0);
  const cursorY = useMotionValue(0);
  const hoverMV = useMotionValue(0);
  const prefersReduced = useReducedMotion();

  const rafRef = React.useRef<number | null>(null);
  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = rootRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    if (rafRef.current == null) {
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null;
        cursorX.set(x);
        cursorY.set(y);
      });
    }
  };

  const leaveTimer = React.useRef<number | null>(null);
  const onEnter = () => {
    if (leaveTimer.current) {
      window.clearTimeout(leaveTimer.current);
      leaveTimer.current = null;
    }
    hoverMV.set(1);
  };
  const onLeave = () => {
    if (reassembleDelay > 0) {
      leaveTimer.current = window.setTimeout(() => {
        hoverMV.set(0);
        leaveTimer.current = null;
      }, reassembleDelay);
    } else {
      hoverMV.set(0);
    }
  };

  React.useEffect(() => {
    return () => {
      if (leaveTimer.current) window.clearTimeout(leaveTimer.current);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <div
      ref={rootRef}
      className={className}
      onMouseEnter={onEnter}
      onMouseLeave={onLeave}
      onMouseMove={onMove}
      style={{
        ...style,
        position: "relative",
        overflow: "hidden",
        userSelect: "none",
        isolation: "isolate",
        transform: "translateZ(0)",
        touchAction: "none",
      }}
      role="img"
      aria-label={imgAlt}
    >
      {natural && layout && bgUrl
        ? Array.from({ length: ty }).map((_, row) =>
            Array.from({ length: tx }).map((__, col) => {
              const i = row * tx + col;
              const left = colEdges[col];
              const right = colEdges[col + 1];
              const top = rowEdges[row];
              const bottom = rowEdges[row + 1];
              const tileW = right - left;
              const tileH = bottom - top;
              const cx = left + tileW / 2;
              const cy = top + tileH / 2;
              return (
                <Tile
                  key={i}
                  i={i}
                  left={left}
                  top={top}
                  width={tileW}
                  height={tileH}
                  centerX={cx}
                  centerY={cy}
                  target={{
                    x: prefersReduced ? 0 : targets[i].x,
                    y: prefersReduced ? 0 : targets[i].y,
                    r: prefersReduced ? 0 : targets[i].r,
                  }}
                  hoverMV={hoverMV}
                  cursorX={cursorX}
                  cursorY={cursorY}
                  stiffness={springStiffness}
                  damping={springDamping}
                  magnetStrength={magnetStrength * (prefersReduced ? 0 : 1)}
                  magnetRadius={magnetRadius}
                  bleed={BLEED}
                  bgUrl={bgUrl}
                  bgSizeW={layout.scaledW}
                  bgSizeH={layout.scaledH}
                  imgLeft={layout.imgLeft}
                  imgTop={layout.imgTop}
                />
              );
            }),
          )
        : null}
    </div>
  );
}
