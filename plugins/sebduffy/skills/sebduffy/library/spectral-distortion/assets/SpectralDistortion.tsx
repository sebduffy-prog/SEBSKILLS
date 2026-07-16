"use client";

import {
  CSSProperties,
  ReactNode,
  useEffect,
  useRef,
} from "react";
import SpectraNoise, { SpectraNoiseProps } from "./SpectraNoise";
import InteractiveDistortion, {
  InteractiveDistortionProps,
} from "./InteractiveDistortion";

/* ============================================================================
 * SpectralDistortion — layers a red SpectraNoise background behind an
 * InteractiveDistortion image, and continuously feeds the shader's oscillation
 * into the distortion field so the spectra itself warps the image.
 *
 * Pure composition: zero WebGL code here. Depends on SpectraNoise and
 * InteractiveDistortion being present as siblings.
 * ============================================================================ */

const RED_SPECTRA_DEFAULTS: Partial<SpectraNoiseProps> = {
  useCustomColors: true,
  primaryColor: [0.15, 0.0, 0.0],
  secondaryColor: [0.7, 0.05, 0.1],
  accentColor: [1.0, 0.25, 0.2],
  colorIntensity: 0.85,
  warpAmount: 0.35,
  noiseIntensity: 0.06,
  scanlineIntensity: 0.12,
  scanlineFrequency: 0.5,
  speed: 0.45,
  resolutionScale: 1,
};

export interface SpectralDistortionProps {
  imageUrl?: string;
  videoUrl?: string;
  mediaType?: "image" | "video";
  /** 0 = mouse only. 1 = strong continuous shader-driven warp. */
  ambientStrength?: number;
  /** Rough frequency of the ambient warp signal, in Hz. */
  ambientFrequency?: number;
  /** 0-1 opacity of the distorted image over the spectra background. */
  imageOpacity?: number;
  /** CSS mix-blend-mode for the image layer. "screen" keeps the red visible. */
  imageBlendMode?: CSSProperties["mixBlendMode"];
  /** Explicit height for the container (parent must be sized otherwise). */
  height?: CSSProperties["height"];
  width?: CSSProperties["width"];
  distortionPreset?: InteractiveDistortionProps["preset"];
  spectraProps?: Partial<SpectraNoiseProps>;
  distortionProps?: Partial<InteractiveDistortionProps>;
  style?: CSSProperties;
  className?: string;
  children?: ReactNode;
}

export default function SpectralDistortion({
  imageUrl,
  videoUrl,
  mediaType = videoUrl ? "video" : "image",
  ambientStrength = 0.6,
  ambientFrequency = 0.4,
  imageOpacity = 0.85,
  imageBlendMode = "screen",
  height = "100vh",
  width = "100%",
  distortionPreset = "pixelated",
  spectraProps,
  distortionProps,
  style,
  className,
  children,
}: SpectralDistortionProps) {
  const distortionLayerRef = useRef<HTMLDivElement>(null);

  // Drive InteractiveDistortion's internal mouse-velocity ref by dispatching
  // synthetic mousemove events that trace a slow Lissajous curve. The shader
  // component already reads those events, so we don't have to touch its
  // internals — we just feed it a synthetic cursor that oscillates the way the
  // spectra-noise field does.
  useEffect(() => {
    if (ambientStrength <= 0) return;
    const layer = distortionLayerRef.current;
    if (!layer) return;

    let raf = 0;
    const start = performance.now();

    const tick = () => {
      const rect = layer.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        const t = (performance.now() - start) / 1000;
        const omega = 2 * Math.PI * ambientFrequency;
        // Lissajous-ish path, amplitude scaled by ambientStrength.
        const nx = 0.5 + 0.4 * ambientStrength * Math.sin(omega * t);
        const ny = 0.5 + 0.4 * ambientStrength * Math.cos(omega * t * 1.3);
        const clientX = rect.left + nx * rect.width;
        const clientY = rect.top + ny * rect.height;
        // `bubbles: true` so it reaches the listener inside the
        // InteractiveDistortion container regardless of its internal mount.
        const ev = new MouseEvent("mousemove", {
          clientX,
          clientY,
          bubbles: true,
          cancelable: true,
          view: window,
        });
        layer.dispatchEvent(ev);
      }
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [ambientStrength, ambientFrequency]);

  const mergedSpectraProps: SpectraNoiseProps = {
    ...RED_SPECTRA_DEFAULTS,
    ...spectraProps,
  };

  const mergedDistortionProps: InteractiveDistortionProps = {
    preset: distortionPreset,
    mediaType,
    imageUrl,
    videoUrl,
    objectFit: "cover",
    backgroundColor: "transparent",
    ...distortionProps,
  };

  return (
    <div
      className={className}
      style={{
        position: "relative",
        width,
        height,
        overflow: "hidden",
        isolation: "isolate",
        ...style,
      }}
    >
      {/* Background: red spectra shader */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 0,
          pointerEvents: "none",
        }}
      >
        <SpectraNoise {...mergedSpectraProps} />
      </div>

      {/* Mid: distorted image, blended over the spectra */}
      <div
        ref={distortionLayerRef}
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 1,
          opacity: imageOpacity,
          mixBlendMode: imageBlendMode,
          pointerEvents: "auto",
        }}
      >
        <InteractiveDistortion {...mergedDistortionProps} />
      </div>

      {/* Foreground: user content, always on top and interactive */}
      {children !== undefined && (
        <div
          style={{
            position: "relative",
            zIndex: 10,
            width: "100%",
            height: "100%",
            pointerEvents: "auto",
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}
