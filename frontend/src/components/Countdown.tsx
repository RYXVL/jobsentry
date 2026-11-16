import { useEffect, useState } from "react";

interface CountdownProps {
  /** The moment counted down to (ISO 8601). */
  to: string;
  /** Shown once the time is up. */
  done?: string;
}

/**
 * A live countdown in hh:mm:ss, e.g. "00:12:34". It keeps its own one-second
 * timer, so only this text re-renders each second, not the page around it.
 * Not announced by screen readers on every tick; the time is in dateTime.
 */
export function Countdown({ to, done = "any moment" }: CountdownProps) {
  const target = new Date(to).getTime();
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    setNow(Date.now()); // a new target: correct straight away, not a second later
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [target]);

  if (Number.isNaN(target)) return null;
  const remaining = target - now;
  return <time dateTime={to}>{remaining > 0 ? formatCountdown(remaining) : done}</time>;
}

/** 754000 ms becomes "00:12:34"; hours keep counting past 24 ("26:00:00"). */
function formatCountdown(ms: number): string {
  const totalSeconds = Math.ceil(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}