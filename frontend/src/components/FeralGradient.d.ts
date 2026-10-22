import type { CSSProperties, ReactElement } from "react";

export interface FeralGradientProps {
  className?: string;
  style?: CSSProperties;
  speed?: number;
  paused?: boolean;
}

export default function FeralGradient(props: FeralGradientProps): ReactElement;
export function paintRecipe(canvas: HTMLCanvasElement, recipe: unknown, t?: number): void;