"use client";

import { useState, CSSProperties, MouseEvent as ReactMouseEvent, ReactNode } from "react";

/* ============================================================================
 * LiquidGlassButton — Apple-style liquid glass button (pure CSS).
 * Adapted from the Framer GlassBackButton module.
 * Renders best over busy/photo backgrounds (backdrop-filter needs content to blur).
 * ============================================================================ */

type BuiltInIcon = "chevron-left" | "chevron-right" | "x" | "check" | null;

export interface LiquidGlassButtonProps {
  label?: string;
  showText?: boolean;
  icon?: BuiltInIcon;
  customIcon?: ReactNode;
  onClick?: (e: ReactMouseEvent<HTMLButtonElement>) => void;

  iconSize?: number;
  iconWeight?: number;
  textSize?: number;
  textWeight?: number;
  textColor?: string;

  glassBackground?: string;
  glassBorderColor?: string;
  highlightColor?: string;
  outerShadowColor?: string;
  innerShadowColor?: string;
  hoverTint?: string;

  paddingTop?: number;
  paddingRight?: number;
  paddingBottom?: number;
  paddingLeft?: number;
  gap?: number;
  borderRadius?: number;

  blurAmount?: number;
  glassOpacity?: number;
  glassTransparency?: number;
  highlightIntensity?: number;
  lightDirection?: number;

  outerShadowIntensity?: number;
  outerShadowBlur?: number;
  outerShadowSpread?: number;
  innerShadowIntensity?: number;
  innerShadowBlur?: number;
  innerShadowSpread?: number;
  noiseOpacity?: number;

  style?: CSSProperties;
  className?: string;
  ariaLabel?: string;
}

/** Replace the alpha channel of an rgba() string. Passes through unchanged if not rgba. */
const withAlpha = (rgba: string, alpha: number): string => {
  return rgba.replace(/[\d.]+\)$/g, `${alpha})`);
};

const ICON_PATHS: Record<Exclude<BuiltInIcon, null>, string> = {
  "chevron-left": "M15 18l-6-6 6-6",
  "chevron-right": "M9 18l6-6-6-6",
  "x": "M18 6L6 18 M6 6l12 12",
  "check": "M20 6L9 17l-5-5",
};

export default function LiquidGlassButton({
  label = "Back",
  showText = true,
  icon = "chevron-left",
  customIcon,
  onClick,

  iconSize = 28,
  iconWeight = 2,
  textSize = 28,
  textWeight = 500,
  textColor = "rgba(255, 255, 255, 0.85)",

  glassBackground = "rgba(199, 199, 199, 0.45)",
  glassBorderColor = "rgba(255, 255, 255, 0.3)",
  highlightColor = "rgba(163, 163, 163, 0.6)",
  outerShadowColor = "rgba(41, 41, 41, 0.1)",
  innerShadowColor = "rgba(255, 255, 255, 0.05)",
  hoverTint = "rgba(209, 209, 209, 0.15)",

  paddingTop = 14,
  paddingRight = 21,
  paddingBottom = 14,
  paddingLeft = 21,
  gap = 2,
  borderRadius = 21,

  blurAmount = 10,
  glassOpacity = 0.25,
  glassTransparency = 0.5,
  highlightIntensity = 0.15,
  lightDirection = 225,

  outerShadowIntensity = 0.2,
  outerShadowBlur = 5,
  outerShadowSpread = -2,
  innerShadowIntensity = 0.14,
  innerShadowBlur = 3,
  innerShadowSpread = -1,
  noiseOpacity = 0.06,

  style,
  className,
  ariaLabel,
}: LiquidGlassButtonProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isPressed, setIsPressed] = useState(false);

  const handleClick = (e: ReactMouseEvent<HTMLButtonElement>) => {
    if (onClick) {
      onClick(e);
    } else if (typeof window !== "undefined") {
      window.history.back();
    }
  };

  const finalGlassOpacity = glassOpacity * glassTransparency;
  const borderOpacity = 0.05 * glassTransparency;
  const borderHighlightOpacity = highlightIntensity * 0.4 * glassTransparency;

  // Base multi-layer gradient background.
  const buildBg = (hovered: boolean) => {
    const hiMul = hovered ? 1.4 : 0.8;
    const hi2Mul = hovered ? 0.8 : 0.3;
    const hi3Mul = hovered ? 0.5 : 0;
    const hi4Mul = hovered ? 1.1 : 0.6;
    const glassMul = hovered ? finalGlassOpacity + 0.15 : finalGlassOpacity;
    const innerMul = hovered ? innerShadowIntensity * 0.5 : innerShadowIntensity * 0.3;
    const noiseMul = hovered ? noiseOpacity * 0.7 : noiseOpacity;

    const layers = [
      `linear-gradient(${lightDirection}deg, ${withAlpha(highlightColor, highlightIntensity * hiMul)} 0%, transparent ${hovered ? 35 : 40}%)`,
      hovered
        ? `linear-gradient(${lightDirection + 45}deg, ${withAlpha(highlightColor, highlightIntensity * hi2Mul)} 0%, transparent 40%)`
        : null,
      `linear-gradient(${lightDirection + 90}deg, ${withAlpha(highlightColor, highlightIntensity * (hovered ? hi3Mul : 0.3))} 0%, transparent ${hovered ? 35 : 30}%)`,
      `linear-gradient(${lightDirection + 135}deg, ${withAlpha(highlightColor, highlightIntensity * hi4Mul)} 0%, ${withAlpha(glassBackground, glassMul)} 50%, ${withAlpha(innerShadowColor, innerMul)} 100%)`,
      hovered ? withAlpha(hoverTint, 0.2) : null,
      `linear-gradient(to bottom, transparent 0%, ${withAlpha(innerShadowColor, noiseMul)} 100%)`,
    ].filter(Boolean);

    return layers.join(", ");
  };

  const buildBoxShadow = (hovered: boolean) => {
    if (hovered) {
      return [
        `0 ${outerShadowBlur * 1.5}px ${outerShadowBlur * 2.5}px ${outerShadowSpread - 1}px ${withAlpha(outerShadowColor, outerShadowIntensity * 1.6)}`,
        `0 ${outerShadowBlur * 0.5}px ${outerShadowBlur}px ${outerShadowSpread + 2}px ${withAlpha(highlightColor, highlightIntensity * 0.3)}`,
        `inset 0 0 0 1px ${withAlpha(glassBorderColor, borderOpacity * 2)}`,
        `inset 0 2px 4px 0 ${withAlpha(highlightColor, borderHighlightOpacity * 2)}`,
        `inset 0 -${innerShadowBlur}px ${innerShadowBlur * 1.5}px ${innerShadowSpread}px ${withAlpha(innerShadowColor, innerShadowIntensity * 0.7)}`,
      ].join(", ");
    }
    return [
      `0 ${outerShadowBlur}px ${outerShadowBlur * 1.5}px ${outerShadowSpread}px ${withAlpha(outerShadowColor, outerShadowIntensity)}`,
      `inset 0 0 0 1px ${withAlpha(glassBorderColor, borderOpacity)}`,
      `inset 0 1px 1px 0 ${withAlpha(highlightColor, borderHighlightOpacity)}`,
      `inset 0 -${innerShadowBlur}px ${innerShadowBlur}px ${innerShadowSpread}px ${withAlpha(innerShadowColor, innerShadowIntensity)}`,
    ].join(", ");
  };

  const buttonStyle: CSSProperties = {
    position: "relative",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: style?.width ?? "auto",
    gap: showText ? gap : 0,
    paddingTop,
    paddingRight,
    paddingBottom,
    paddingLeft,
    minWidth: 44,
    minHeight: 44,
    borderRadius,
    border: "1px solid transparent",
    cursor: "pointer",
    userSelect: "none",
    outline: "none",
    overflow: "hidden",
    backdropFilter: `blur(${isHovered ? blurAmount * 1.2 : blurAmount}px)`,
    WebkitBackdropFilter: `blur(${isHovered ? blurAmount * 1.2 : blurAmount}px)`,
    background: buildBg(isHovered),
    boxShadow: buildBoxShadow(isHovered),
    transform: isPressed
      ? "scale(0.96) translateY(0px) translateZ(0)"
      : `scale(${isHovered ? 1.05 : 1}) translateY(${isHovered ? -2 : 0}px) translateZ(0)`,
    transition: isPressed
      ? "transform 0.08s cubic-bezier(0.25, 0.46, 0.45, 0.94), background 0.08s ease-out, filter 0.08s ease-out"
      : "transform 1.2s cubic-bezier(0.23, 1, 0.32, 1), background 0.8s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 1.0s cubic-bezier(0.4, 0, 0.2, 1), backdrop-filter 0.8s ease-out",
    willChange: "transform, background, box-shadow",
    ...style,
  };

  // Gradient border overlay (mask-composite trick).
  const borderOverlayStyle: CSSProperties = {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius,
    padding: 1,
    background: `linear-gradient(${lightDirection}deg, ${withAlpha(highlightColor, borderHighlightOpacity * 2)}, transparent 30%, transparent 70%, ${withAlpha(innerShadowColor, borderOpacity * 2)})`,
    WebkitMask: "linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)",
    WebkitMaskComposite: "xor",
    mask: "linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)",
    maskComposite: "exclude",
    pointerEvents: "none",
  };

  const iconStyle: CSSProperties = {
    width: iconSize,
    height: iconSize,
    color: textColor,
    flexShrink: 0,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  };

  const textStyle: CSSProperties = {
    color: textColor,
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    fontSize: textSize,
    fontWeight: textWeight,
    fontFamily: "system-ui, -apple-system, 'SF Pro Text', sans-serif",
  };

  const renderIcon = () => {
    if (customIcon) return customIcon;
    if (!icon) return null;
    return (
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={iconWeight}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d={ICON_PATHS[icon]} />
      </svg>
    );
  };

  return (
    <button
      className={className}
      style={buttonStyle}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => {
        setIsHovered(false);
        setIsPressed(false);
      }}
      onMouseDown={() => setIsPressed(true)}
      onMouseUp={() => setIsPressed(false)}
      onClick={handleClick}
      aria-label={ariaLabel ?? (!showText ? label : undefined)}
    >
      <div style={borderOverlayStyle} />
      <div style={iconStyle}>{renderIcon()}</div>
      {showText && <span style={textStyle}>{label}</span>}
    </button>
  );
}
