"use client";

import React from "react";

type Tone = "wall" | "ink" | "cloud" | "path";

const TONE: Record<Tone, string> = {
  wall: "bg-pixel-wall text-black",
  ink: "bg-pixel-ink text-white",
  cloud: "bg-white text-black",
  path: "bg-pixel-path text-black",
};

interface Props extends React.HTMLAttributes<HTMLDivElement> {
  tone?: Tone;
  shadow?: boolean;
}

export default function PixelPanel({
  tone = "wall",
  shadow = true,
  className = "",
  children,
  ...rest
}: Props) {
  return (
    <div
      {...rest}
      className={`border-2 border-black rounded-xl ${shadow ? "shadow-pixel-md" : ""} ${TONE[tone]} ${className}`}
    >
      {children}
    </div>
  );
}
