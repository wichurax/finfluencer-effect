import React from "react";
import { Composition } from "remotion";
import { FPS, H, W } from "./shared";
import { DURATION_A, VersionA } from "./VersionA";

export const Root: React.FC = () => (
  <Composition id="Finfluencer-EN" component={VersionA} durationInFrames={DURATION_A} fps={FPS} width={W} height={H} />
);
