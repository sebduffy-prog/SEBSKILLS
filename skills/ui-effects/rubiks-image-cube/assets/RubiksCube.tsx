"use client";

import { useState, useRef, useEffect, CSSProperties } from "react";
import { motion } from "framer-motion";

/* ============================================================================
 * RubiksCube — interactive 3D cube with colour or image faces
 * Adapted from the Framer Rubix Image Cube module.
 * Pure CSS 3D + framer-motion. No WebGL.
 * ============================================================================ */

export interface FaceImage {
  src: string;
  segmentIndex?: number;
  totalSegments?: number;
}

export interface RubiksCubeProps {
  cubeSize?: number;
  gap?: number;
  rotationSpeed?: number;
  shuffleSpeed?: number;
  autoRotate?: boolean;
  showControls?: boolean;
  frontImages?: FaceImage[];
  backImages?: FaceImage[];
  topImages?: FaceImage[];
  bottomImages?: FaceImage[];
  leftImages?: FaceImage[];
  rightImages?: FaceImage[];
  backgroundColor?: string;
  borderRadius?: number;
  useImages?: boolean;
  style?: CSSProperties;
  className?: string;
}

type FaceKey = "front" | "back" | "top" | "bottom" | "left" | "right";
type Segment = string | FaceImage | null;
type CubeState = Record<FaceKey, Segment[]>;

const DEFAULT_COLORS = ["#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff9900", "#ffffff"];

export default function RubiksCube({
  cubeSize = 60,
  gap = 2,
  rotationSpeed = 0.5,
  shuffleSpeed = 500,
  autoRotate = false,
  showControls = true,
  frontImages = [],
  backImages = [],
  topImages = [],
  bottomImages = [],
  leftImages = [],
  rightImages = [],
  backgroundColor = "#000000",
  borderRadius = 4,
  useImages = false,
  style,
  className,
}: RubiksCubeProps) {
  const createImageSegments = (images: FaceImage[]): Segment[] => {
    if (useImages && images && images.length > 0) {
      if (images.length === 9) return images as Segment[];
      if (images.length === 1) {
        return Array(9)
          .fill(null)
          .map((_, index) => ({ ...images[0], segmentIndex: index, totalSegments: 9 }));
      }
      return Array(9)
        .fill(null)
        .map((_, index) => {
          const img = images[index % images.length];
          return img ? { ...img, segmentIndex: index, totalSegments: 9 } : null;
        });
    }
    return Array(9)
      .fill(null)
      .map((_, index) => DEFAULT_COLORS[Math.floor(index / 3) % DEFAULT_COLORS.length]);
  };

  const [cubeState, setCubeState] = useState<CubeState>({
    front: createImageSegments(frontImages),
    back: createImageSegments(backImages),
    top: createImageSegments(topImages),
    bottom: createImageSegments(bottomImages),
    left: createImageSegments(leftImages),
    right: createImageSegments(rightImages),
  });

  const [rotation, setRotation] = useState({ x: -25, y: 45, z: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [isShuffling, setIsShuffling] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setCubeState({
      front: createImageSegments(frontImages),
      back: createImageSegments(backImages),
      top: createImageSegments(topImages),
      bottom: createImageSegments(bottomImages),
      left: createImageSegments(leftImages),
      right: createImageSegments(rightImages),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frontImages, backImages, topImages, bottomImages, leftImages, rightImages, useImages]);

  // Auto-rotate.
  useEffect(() => {
    if (autoRotate && !isDragging && !isShuffling) {
      const id = setInterval(() => {
        setRotation((prev) => ({ ...prev, y: prev.y + 1 }));
      }, 50);
      return () => clearInterval(id);
    }
  }, [autoRotate, isDragging, isShuffling]);

  // Global drag handlers.
  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e: MouseEvent) => {
      const dx = e.clientX - dragStart.x;
      const dy = e.clientY - dragStart.y;
      setRotation((prev) => ({
        x: prev.x + dy * rotationSpeed,
        y: prev.y + dx * rotationSpeed,
        z: prev.z,
      }));
      setDragStart({ x: e.clientX, y: e.clientY });
    };
    const onUp = () => setIsDragging(false);
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    return () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
  }, [isDragging, dragStart, rotationSpeed]);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  // Rotate one face clockwise + adjacent edges (front only — cosmetic).
  const rotateFace = (face: FaceKey) => {
    setCubeState((prev) => {
      const newState: CubeState = { ...prev };
      const f = [...prev[face]];
      const t = [...f];
      f[0] = t[6]; f[1] = t[3]; f[2] = t[0];
      f[3] = t[7]; f[4] = t[4]; f[5] = t[1];
      f[6] = t[8]; f[7] = t[5]; f[8] = t[2];
      newState[face] = f;

      if (face === "front") {
        const saved = [newState.top[6], newState.top[7], newState.top[8]];
        newState.top = [...newState.top];
        newState.left = [...newState.left];
        newState.bottom = [...newState.bottom];
        newState.right = [...newState.right];
        newState.top[6] = newState.left[8];
        newState.top[7] = newState.left[5];
        newState.top[8] = newState.left[2];
        newState.left[2] = newState.bottom[0];
        newState.left[5] = newState.bottom[1];
        newState.left[8] = newState.bottom[2];
        newState.bottom[0] = newState.right[6];
        newState.bottom[1] = newState.right[3];
        newState.bottom[2] = newState.right[0];
        newState.right[0] = saved[0];
        newState.right[3] = saved[1];
        newState.right[6] = saved[2];
      }
      return newState;
    });
  };

  const shuffleCube = async () => {
    setIsShuffling(true);
    const faces: FaceKey[] = ["front", "back", "top", "bottom", "left", "right"];
    const moves = 20;
    for (let i = 0; i < moves; i++) {
      const f = faces[Math.floor(Math.random() * faces.length)];
      rotateFace(f);
      await new Promise((r) => setTimeout(r, shuffleSpeed / moves));
    }
    setIsShuffling(false);
  };

  const resetCube = () => {
    setCubeState({
      front: createImageSegments(frontImages),
      back: createImageSegments(backImages),
      top: createImageSegments(topImages),
      bottom: createImageSegments(bottomImages),
      left: createImageSegments(leftImages),
      right: createImageSegments(rightImages),
    });
    setRotation({ x: -25, y: 45, z: 0 });
  };

  const createFace = (faceData: Segment[], facePosition: FaceKey) => {
    const transformMap: Record<FaceKey, string> = {
      front: `translateZ(${cubeSize * 1.5}px)`,
      back: `rotateY(180deg) translateZ(${cubeSize * 1.5}px)`,
      top: `rotateX(90deg) translateZ(${cubeSize * 1.5}px)`,
      bottom: `rotateX(-90deg) translateZ(${cubeSize * 1.5}px)`,
      left: `rotateY(-90deg) translateZ(${cubeSize * 1.5}px)`,
      right: `rotateY(90deg) translateZ(${cubeSize * 1.5}px)`,
    };

    const renderSegment = (segment: Segment, index: number) => {
      if (useImages && segment && typeof segment === "object" && segment.src) {
        const { src, totalSegments } = segment;
        const row = Math.floor(index / 3);
        const col = index % 3;
        return (
          <motion.div
            key={index}
            style={{
              backgroundImage: `url(${src})`,
              backgroundSize: totalSegments ? `${cubeSize * 3}px ${cubeSize * 3}px` : "cover",
              backgroundPosition: totalSegments
                ? `-${col * (cubeSize - gap)}px -${row * (cubeSize - gap)}px`
                : "center",
              backgroundRepeat: "no-repeat",
              borderRadius: `${borderRadius}px`,
              border: `1px solid rgba(0,0,0,0.1)`,
              width: "100%",
              height: "100%",
            }}
            whileHover={{ scale: 1.1 }}
            transition={{ duration: 0.2 }}
          />
        );
      }
      return (
        <motion.div
          key={index}
          style={{
            backgroundColor: typeof segment === "string" ? segment : "#cccccc",
            borderRadius: `${borderRadius}px`,
            border: `1px solid rgba(0,0,0,0.1)`,
          }}
          whileHover={{ scale: 1.1 }}
          transition={{ duration: 0.2 }}
        />
      );
    };

    return (
      <div
        className="face"
        style={{
          position: "absolute",
          width: `${cubeSize * 3}px`,
          height: `${cubeSize * 3}px`,
          display: "grid",
          gridTemplateColumns: `repeat(3, ${cubeSize - gap}px)`,
          gridTemplateRows: `repeat(3, ${cubeSize - gap}px)`,
          gap: `${gap}px`,
          padding: `${gap}px`,
          transform: transformMap[facePosition],
          backgroundColor,
        }}
      >
        {faceData.map((segment, index) => renderSegment(segment, index))}
      </div>
    );
  };

  const containerStyle: CSSProperties = {
    width: "100%",
    height: "100%",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    perspective: "1000px",
    ...style,
  };

  const cubeContainerStyle: CSSProperties = {
    width: `${cubeSize * 3}px`,
    height: `${cubeSize * 3}px`,
    position: "relative",
    transformStyle: "preserve-3d",
    cursor: isDragging ? "grabbing" : "grab",
    transition: isDragging ? "none" : `transform ${rotationSpeed}s ease-out`,
  };

  const buttonStyle: CSSProperties = {
    padding: "8px 16px",
    backgroundColor: "#6366f1",
    color: "white",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 500,
    transition: "all 0.2s ease",
  };

  return (
    <div className={className} style={containerStyle}>
      <div
        ref={containerRef}
        style={cubeContainerStyle}
        onMouseDown={handleMouseDown}
        onClick={() => {
          if (!isDragging) {
            const quickShuffle = async () => {
              const faces: FaceKey[] = ["front", "back", "top", "bottom", "left", "right"];
              for (let i = 0; i < 5; i++) {
                rotateFace(faces[Math.floor(Math.random() * faces.length)]);
                await new Promise((r) => setTimeout(r, 50));
              }
            };
            quickShuffle();
          }
        }}
      >
        <motion.div
          animate={{ rotateX: rotation.x, rotateY: rotation.y, rotateZ: rotation.z }}
          style={{
            width: "100%",
            height: "100%",
            transformStyle: "preserve-3d",
            transition: isDragging ? "none" : "transform 0.1s ease-out",
          }}
        >
          {createFace(cubeState.front, "front")}
          {createFace(cubeState.back, "back")}
          {createFace(cubeState.top, "top")}
          {createFace(cubeState.bottom, "bottom")}
          {createFace(cubeState.left, "left")}
          {createFace(cubeState.right, "right")}
        </motion.div>
      </div>
      {showControls && (
        <div
          style={{
            display: "flex",
            gap: 8,
            marginTop: 20,
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          <button
            style={buttonStyle}
            onClick={(e) => {
              e.stopPropagation();
              shuffleCube();
            }}
            disabled={isShuffling}
          >
            {isShuffling ? "Shuffling..." : "Shuffle"}
          </button>
          <button
            style={buttonStyle}
            onClick={(e) => {
              e.stopPropagation();
              resetCube();
            }}
          >
            Reset
          </button>
          <button
            style={buttonStyle}
            onClick={(e) => {
              e.stopPropagation();
              rotateFace("front");
            }}
          >
            Rotate Front
          </button>
          <button
            style={buttonStyle}
            onClick={(e) => {
              e.stopPropagation();
              setRotation({ x: -25, y: 45, z: 0 });
            }}
          >
            Reset View
          </button>
        </div>
      )}
    </div>
  );
}
