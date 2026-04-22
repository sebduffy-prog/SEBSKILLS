"use client";
import React, { useId, useState } from "react";

export type FloatingLabelInputProps = {
  label: string;
  value?: string;
  defaultValue?: string;
  onChange?: (v: string) => void;
  type?: string;
  error?: string;
  helper?: string;
  accentColor?: string;
  className?: string;
  style?: React.CSSProperties;
  inputProps?: Omit<React.InputHTMLAttributes<HTMLInputElement>, "onChange" | "value">;
};

export default function FloatingLabelInput({
  label,
  value,
  defaultValue = "",
  onChange,
  type = "text",
  error,
  helper,
  accentColor = "#6366f1",
  className,
  style,
  inputProps,
}: FloatingLabelInputProps) {
  const id = useId();
  const isControlled = value !== undefined;
  const [inner, setInner] = useState(defaultValue);
  const [focused, setFocused] = useState(false);
  const v = isControlled ? value! : inner;
  const floated = focused || v.length > 0;
  const borderColor = error ? "#ef4444" : focused ? accentColor : "rgba(0,0,0,0.15)";

  return (
    <div className={className} style={{ display: "flex", flexDirection: "column", gap: 4, ...style }}>
      <div
        style={{
          position: "relative",
          border: `1.5px solid ${borderColor}`,
          borderRadius: 10,
          background: "white",
          transition: "border-color 160ms ease, box-shadow 160ms ease",
          boxShadow: focused && !error ? `0 0 0 4px ${accentColor}22` : "none",
        }}
      >
        <label
          htmlFor={id}
          style={{
            position: "absolute",
            left: 14,
            top: floated ? -9 : "50%",
            transform: floated ? "translateY(0)" : "translateY(-50%)",
            fontSize: floated ? 12 : 15,
            color: error ? "#ef4444" : floated ? (focused ? accentColor : "rgba(0,0,0,0.6)") : "rgba(0,0,0,0.45)",
            background: floated ? "white" : "transparent",
            padding: floated ? "0 6px" : "0",
            pointerEvents: "none",
            transition: "all 160ms ease",
          }}
        >
          {label}
        </label>
        <input
          id={id}
          type={type}
          value={v}
          onChange={(e) => {
            if (!isControlled) setInner(e.target.value);
            onChange?.(e.target.value);
          }}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          {...inputProps}
          style={{
            width: "100%",
            padding: "16px 14px",
            border: "none",
            outline: "none",
            background: "transparent",
            fontSize: 15,
            borderRadius: 10,
          }}
        />
      </div>
      {(error || helper) && (
        <span style={{ fontSize: 12, color: error ? "#ef4444" : "rgba(0,0,0,0.55)", paddingLeft: 2 }}>
          {error || helper}
        </span>
      )}
    </div>
  );
}
