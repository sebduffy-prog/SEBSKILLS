"use client";

import { useState, useEffect, useRef, useMemo, CSSProperties } from "react";

/* ============================================================================
 * InteractiveDistortion — WebGL2 mouse-driven pixel distortion for image/video
 *
 * Technique: Akella's DistortedPixels (MIT) — https://github.com/akella/DistortedPixels
 * This implementation adapts the Framer module (Fugu 4D port) into a
 * single-file self-contained React component with no external deps.
 *
 * FOR PERSONAL / EXPERIMENTAL USE.
 * ============================================================================ */

/* -------------------- Presets -------------------- */

const IMAGE_PRESETS = {
  smoothDistortion: { grid: 50, mouseInfluence: 0.25, strength: 0.11, relaxation: 0.9, distortionStrength: 1 },
  highDetail:       { grid: 607, mouseInfluence: 0.11, strength: 0.36, relaxation: 0.96, distortionStrength: 1 },
  pixelated:        { grid: 15, mouseInfluence: 0.13, strength: 0.15, relaxation: 0.9, distortionStrength: 1 },
} as const;

const VIDEO_PRESETS = {
  smoothDistortion: { grid: 30, mouseInfluence: 0.25, strength: 0.11, relaxation: 0.9, distortionStrength: 1 },
  highDetail:       { grid: 80, mouseInfluence: 0.11, strength: 0.36, relaxation: 0.96, distortionStrength: 1 },
  pixelated:        { grid: 12, mouseInfluence: 0.13, strength: 0.15, relaxation: 0.9, distortionStrength: 1 },
} as const;

type PresetName = keyof typeof IMAGE_PRESETS | "custom";

/* -------------------- Shaders -------------------- */

const vertexShaderSource = `#version 300 es
in vec2 aPosition;
out vec2 vUv;
void main() {
  vUv = vec2((aPosition.x + 1.0) / 2.0, 1.0 - (aPosition.y + 1.0) / 2.0);
  gl_Position = vec4(aPosition, 0.0, 1.0);
}`;

const fragmentShaderSource = `#version 300 es
precision highp float;
in vec2 vUv;
out vec4 fragColor;
uniform float uTime;
uniform sampler2D uTexture;
uniform sampler2D uDataTexture;
uniform vec4 uResolution; // width, height, imageAspectX, imageAspectY
uniform float uDistortionStrength;
void main() {
  vec2 newUV = (vUv - vec2(0.5)) * uResolution.zw + vec2(0.5);
  vec4 offset = texture(uDataTexture, vUv);
  vec2 distortedUV = newUV - (uDistortionStrength * 0.02) * offset.rg;
  if (distortedUV.x < 0.0 || distortedUV.x > 1.0 || distortedUV.y < 0.0 || distortedUV.y > 1.0) {
    fragColor = vec4(0.0, 0.0, 0.0, 0.0);
  } else {
    fragColor = texture(uTexture, distortedUV);
  }
}`;

/* -------------------- Helpers -------------------- */

const clamp = (n: number, min: number, max: number) => Math.max(min, Math.min(n, max));

function hexToRgb(hex: string): [number, number, number, number] {
  if (!hex || hex === "transparent" || hex === "none") return [0, 0, 0, 0];
  let h = hex.trim();
  if (h.startsWith("rgba") || h.startsWith("rgb")) {
    const parts = h.replace(/rgba?\(|\)/g, "").split(",");
    if (parts.length >= 3) {
      return [
        parseInt(parts[0], 10) / 255,
        parseInt(parts[1], 10) / 255,
        parseInt(parts[2], 10) / 255,
        parts.length === 4 ? parseFloat(parts[3]) : 1,
      ];
    }
    return [1, 1, 1, 1];
  }
  if (!h.startsWith("#")) h = "#" + h;
  h = h.replace(/^#?([a-f\d])([a-f\d])([a-f\d])$/i, (_m, r, g, b) => r + r + g + g + b + b);
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(h);
  return m
    ? [parseInt(m[1], 16) / 255, parseInt(m[2], 16) / 255, parseInt(m[3], 16) / 255, 1]
    : [1, 1, 1, 0];
}

class PerfMonitor {
  frameCount = 0;
  lastTime = performance.now();
  avgFPS = 60;
  samples: number[] = [];
  maxSamples = 30;
  update() {
    this.frameCount++;
    const now = performance.now();
    if (now - this.lastTime >= 1000) {
      this.samples.push(this.frameCount);
      if (this.samples.length > this.maxSamples) this.samples.shift();
      this.avgFPS = this.samples.reduce((a, b) => a + b, 0) / this.samples.length;
      this.frameCount = 0;
      this.lastTime = now;
    }
  }
  shouldReduce() { return this.avgFPS < 25 && this.samples.length >= 10; }
  shouldIncrease() { return this.avgFPS > 50 && this.samples.length >= 10; }
}

/* -------------------- Component -------------------- */

export interface InteractiveDistortionProps {
  preset?: PresetName;
  mediaType?: "image" | "video";
  imageUrl?: string;
  videoUrl?: string;
  backgroundColor?: string;
  objectFit?: "cover" | "contain";
  spinnerColor?: string;
  autoPlay?: boolean;
  autoLoop?: boolean;
  videoPerformanceMode?: boolean;
  adaptiveQuality?: boolean;
  grid?: number;
  mouseInfluence?: number;
  strength?: number;
  relaxation?: number;
  distortionStrength?: number;
  style?: CSSProperties;
  className?: string;
}

export default function InteractiveDistortion({
  preset = "pixelated",
  mediaType = "image",
  imageUrl,
  videoUrl,
  backgroundColor = "transparent",
  objectFit = "cover",
  spinnerColor = "#ffffff",
  autoPlay = true,
  autoLoop = true,
  videoPerformanceMode = true,
  adaptiveQuality = true,
  grid = 15,
  mouseInfluence = 0.12,
  strength = 0.15,
  relaxation = 0.9,
  distortionStrength = 1,
  style,
  className,
}: InteractiveDistortionProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const mouseRef = useRef({ x: 0, y: 0, prevX: 0, prevY: 0, vX: 0, vY: 0 });
  const perfRef = useRef(new PerfMonitor());

  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [video, setVideo] = useState<HTMLVideoElement | null>(null);
  const [imageDims, setImageDims] = useState({ width: 1, height: 1 });
  const [containerSize, setContainerSize] = useState({ width: 1, height: 1 });
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);

  // Resolve effective config (preset or custom).
  const effectiveConfig = useMemo(() => {
    if (preset !== "custom") {
      const presets = mediaType === "video" && videoPerformanceMode ? VIDEO_PRESETS : IMAGE_PRESETS;
      return presets[preset];
    }
    return { grid, mouseInfluence, strength, relaxation, distortionStrength };
  }, [preset, mediaType, videoPerformanceMode, grid, mouseInfluence, strength, relaxation, distortionStrength]);

  // Track container size.
  useEffect(() => {
    if (!containerRef.current) return;
    const el = containerRef.current;
    const update = () => {
      const r = el.getBoundingClientRect();
      setContainerSize({ width: r.width, height: r.height });
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Load image.
  useEffect(() => {
    if (mediaType !== "image" || !imageUrl) return;
    setIsLoading(true);
    setLoadError(null);
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => {
      setImage(img);
      setImageDims({ width: img.width, height: img.height });
      setVideo(null);
    };
    img.onerror = () => {
      setLoadError("Failed to load image");
      setIsLoading(false);
    };
    img.src = imageUrl;
  }, [imageUrl, mediaType]);

  // Load video.
  useEffect(() => {
    if (mediaType !== "video" || !videoUrl) return;
    setIsLoading(true);
    setLoadError(null);
    const v = document.createElement("video");
    v.crossOrigin = "anonymous";
    v.muted = true;
    v.loop = autoLoop;
    v.playsInline = true;
    v.preload = "metadata";
    v.onloadedmetadata = () => {
      setVideo(v);
      setImageDims({ width: v.videoWidth, height: v.videoHeight });
      setImage(null);
      if (autoPlay) v.play().then(() => setIsVideoPlaying(true)).catch(() => setIsVideoPlaying(false));
    };
    v.onplay = () => setIsVideoPlaying(true);
    v.onpause = () => setIsVideoPlaying(false);
    v.onerror = () => {
      setLoadError("Failed to load video");
      setIsLoading(false);
    };
    videoRef.current = v;
    v.src = videoUrl;
    return () => {
      v.pause();
      videoRef.current = null;
    };
  }, [videoUrl, mediaType, autoPlay, autoLoop]);

  // Aspect ratio for object-fit.
  const aspect = useMemo(() => {
    if (!image && !video) return { a1: 1, a2: 1 };
    const imageAspect = imageDims.width / imageDims.height;
    const containerAspect = containerSize.width / containerSize.height;
    if (objectFit === "contain") {
      return containerAspect > imageAspect
        ? { a1: containerAspect / imageAspect, a2: 1 }
        : { a1: 1, a2: imageAspect / containerAspect };
    }
    return containerAspect > imageAspect
      ? { a1: 1, a2: imageAspect / containerAspect }
      : { a1: containerAspect / imageAspect, a2: 1 };
  }, [image, video, imageDims, containerSize, objectFit]);

  // Mouse/touch tracking.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const mouseMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width;
      const y = (e.clientY - r.top) / r.height;
      const m = mouseRef.current;
      m.vX = x - m.prevX;
      m.vY = y - m.prevY;
      m.x = x; m.y = y; m.prevX = x; m.prevY = y;
    };
    const touchMove = (e: TouchEvent) => {
      e.preventDefault();
      const r = el.getBoundingClientRect();
      const t = e.touches[0];
      const x = (t.clientX - r.left) / r.width;
      const y = (t.clientY - r.top) / r.height;
      const m = mouseRef.current;
      m.vX = x - m.prevX;
      m.vY = y - m.prevY;
      m.x = x; m.y = y; m.prevX = x; m.prevY = y;
    };
    el.addEventListener("mousemove", mouseMove);
    el.addEventListener("touchmove", touchMove, { passive: false });
    return () => {
      el.removeEventListener("mousemove", mouseMove);
      el.removeEventListener("touchmove", touchMove);
    };
  }, []);

  // Main WebGL2 render loop.
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const gl = canvas.getContext("webgl2", {
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
      preserveDrawingBuffer: false,
    }) as WebGL2RenderingContext | null;

    if (!gl) {
      setLoadError("WebGL2 not supported");
      return;
    }

    // Compile shaders.
    const compile = (src: string, type: number) => {
      const sh = gl.createShader(type)!;
      gl.shaderSource(sh, src);
      gl.compileShader(sh);
      if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
        console.error("Shader compile error:", gl.getShaderInfoLog(sh));
        return null;
      }
      return sh;
    };
    const vs = compile(vertexShaderSource, gl.VERTEX_SHADER);
    const fs = compile(fragmentShaderSource, gl.FRAGMENT_SHADER);
    if (!vs || !fs) return;

    const program = gl.createProgram()!;
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      console.error("Program link error:", gl.getProgramInfoLog(program));
      return;
    }

    // Fullscreen quad via VAO.
    const vao = gl.createVertexArray()!;
    gl.bindVertexArray(vao);
    const vbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const posLoc = gl.getAttribLocation(program, "aPosition");
    gl.enableVertexAttribArray(posLoc);
    gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);

    // Main texture.
    const mainTexture = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, mainTexture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);

    const hasValidMedia = mediaType === "image" ? !!image : !!video;
    if (mediaType === "video" && video) {
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([0, 0, 0, 255]));
    } else if (mediaType === "image" && image) {
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
    } else {
      const size = 256;
      const data = new Uint8Array(size * size * 4);
      const [r, g, b, a] = hexToRgb(backgroundColor);
      for (let i = 0; i < size * size; i++) {
        data[i * 4] = Math.floor(r * 255);
        data[i * 4 + 1] = Math.floor(g * 255);
        data[i * 4 + 2] = Math.floor(b * 255);
        data[i * 4 + 3] = Math.floor(a * 255);
      }
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, size, size, 0, gl.RGBA, gl.UNSIGNED_BYTE, data);
    }
    gl.bindTexture(gl.TEXTURE_2D, null);

    // Data texture: grid × grid of RGB32F offsets.
    const makeDataTexture = (gridSize: number) => {
      const width = gridSize;
      const height = gridSize;
      const total = width * height;
      const data = new Float32Array(3 * total);
      for (let i = 0; i < total; i++) {
        data[i * 3] = Math.random() * 255 - 125;
        data[i * 3 + 1] = Math.random() * 255 - 125;
        data[i * 3 + 2] = Math.random() * 255 - 125;
      }
      const tex = gl.createTexture()!;
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB32F, width, height, 0, gl.RGB, gl.FLOAT, data);
      gl.bindTexture(gl.TEXTURE_2D, null);
      return { tex, data, width, height };
    };

    let currentGrid = effectiveConfig.grid;
    let dataTex = makeDataTexture(currentGrid);

    // Uniform locations.
    gl.useProgram(program);
    const uTime = gl.getUniformLocation(program, "uTime");
    const uTexture = gl.getUniformLocation(program, "uTexture");
    const uDataTexture = gl.getUniformLocation(program, "uDataTexture");
    const uResolution = gl.getUniformLocation(program, "uResolution");
    const uDistortionStrength = gl.getUniformLocation(program, "uDistortionStrength");

    let frame = 0;
    let lastQualityAdjust = 0;
    let videoUpdateCounter = 0;
    let animationFrame = 0;
    const settings = { ...effectiveConfig };

    const resize = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      canvas.width = w;
      canvas.height = h;
      gl.viewport(0, 0, w, h);
    };
    resize();
    const handleResize = () => resize();
    window.addEventListener("resize", handleResize);

    const render = () => {
      frame++;
      if (adaptiveQuality) perfRef.current.update();

      // Upload current video frame.
      if (mediaType === "video" && video && isVideoPlaying && !video.paused && !video.ended) {
        const interval = perfRef.current.avgFPS < 30 ? 2 : 1;
        videoUpdateCounter++;
        if (videoUpdateCounter >= interval) {
          gl.bindTexture(gl.TEXTURE_2D, mainTexture);
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, video);
          gl.bindTexture(gl.TEXTURE_2D, null);
          videoUpdateCounter = 0;
        }
      }

      // Adaptive quality for video.
      if (adaptiveQuality && mediaType === "video" && frame - lastQualityAdjust > 120) {
        const m = perfRef.current;
        if (m.shouldReduce() && settings.grid > 10) {
          settings.grid = Math.max(10, Math.floor(settings.grid * 0.8));
          gl.deleteTexture(dataTex.tex);
          dataTex = makeDataTexture(settings.grid);
          lastQualityAdjust = frame;
        } else if (m.shouldIncrease() && settings.grid < effectiveConfig.grid) {
          settings.grid = Math.min(effectiveConfig.grid, Math.floor(settings.grid * 1.2));
          gl.deleteTexture(dataTex.tex);
          dataTex = makeDataTexture(settings.grid);
          lastQualityAdjust = frame;
        }
      }

      // Update data texture: relax then apply mouse velocity.
      const { data, width: dw, height: dh } = dataTex;
      for (let i = 0; i < data.length; i += 3) {
        data[i] *= settings.relaxation;
        data[i + 1] *= settings.relaxation;
      }
      const m = mouseRef.current;
      const gridX = dw * m.x;
      const gridY = dw * m.y;
      const maxDist = dw * settings.mouseInfluence;
      const aspectRatio = canvas.height / canvas.width;
      for (let i = 0; i < dw; i++) {
        for (let j = 0; j < dh; j++) {
          const dist = (gridX - i) ** 2 / aspectRatio + (gridY - j) ** 2;
          const maxSq = maxDist ** 2;
          if (dist < maxSq) {
            const idx = 3 * (i + dw * j);
            let power = maxDist / Math.sqrt(dist);
            power = clamp(power, 0, 10);
            data[idx] += settings.strength * 100 * m.vX * power;
            data[idx + 1] -= settings.strength * 100 * m.vY * power;
          }
        }
      }
      gl.bindTexture(gl.TEXTURE_2D, dataTex.tex);
      gl.texSubImage2D(gl.TEXTURE_2D, 0, 0, 0, dw, dh, gl.RGB, gl.FLOAT, data);
      gl.bindTexture(gl.TEXTURE_2D, null);
      m.vX *= 0.9;
      m.vY *= 0.9;

      // Clear + draw.
      const [br, bg, bb, ba] = hexToRgb(backgroundColor);
      gl.clearColor(br, bg, bb, ba);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

      gl.useProgram(program);
      gl.uniform1f(uTime, frame * 0.01);
      gl.uniform4f(uResolution, canvas.width, canvas.height, aspect.a1, aspect.a2);
      gl.uniform1f(uDistortionStrength, settings.distortionStrength);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, mainTexture);
      gl.uniform1i(uTexture, 0);
      gl.activeTexture(gl.TEXTURE1);
      gl.bindTexture(gl.TEXTURE_2D, dataTex.tex);
      gl.uniform1i(uDataTexture, 1);

      gl.bindVertexArray(vao);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      gl.bindVertexArray(null);
      gl.disable(gl.BLEND);

      animationFrame = requestAnimationFrame(render);
    };

    if (hasValidMedia || mediaType) {
      setIsLoading(false);
      render();
    }

    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener("resize", handleResize);
      gl.deleteTexture(mainTexture);
      gl.deleteTexture(dataTex.tex);
      gl.deleteBuffer(vbo);
      gl.deleteVertexArray(vao);
      gl.deleteProgram(program);
    };
  }, [image, video, mediaType, backgroundColor, effectiveConfig, aspect, adaptiveQuality, isVideoPlaying]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        overflow: "hidden",
        backgroundColor,
        ...style,
      }}
    >
      <canvas ref={canvasRef} style={{ display: "block", width: "100%", height: "100%" }} />
      {isLoading && !loadError && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            zIndex: 20,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              border: `3px solid rgba(255, 255, 255, 0.2)`,
              borderTop: `3px solid ${spinnerColor}`,
              borderRadius: "50%",
              animation: "id-spin 1s linear infinite",
            }}
          />
          <style>{`@keyframes id-spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}
      {loadError && (
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            backgroundColor: "rgba(255, 0, 0, 0.8)",
            color: "white",
            padding: "12px 20px",
            borderRadius: 8,
            fontSize: 14,
            zIndex: 20,
          }}
        >
          {loadError}
        </div>
      )}
    </div>
  );
}
