/** Display formatting, using the browser's locale. */

import type { WorkMode } from "../api/types";

const numberFormat = new Intl.NumberFormat();
const relativeFormat = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
const listFormat = new Intl.ListFormat(undefined, { style: "long", type: "conjunction" });
const orListFormat = new Intl.ListFormat(undefined, { style: "long", type: "disjunction" });
const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium" });

export function formatNumber(value: number): string {
  return numberFormat.format(value);
}

/** "3 jobs", "1 job". */
export function formatJobCount(count: number): string {
  return `${formatNumber(count)} ${count === 1 ? "job" : "jobs"}`;
}

/** "Toronto, Atlanta and Chicago"; long lists end with "and N more". */
export function formatList(items: string[], max = 3): string {
  if (items.length <= max) return listFormat.format(items);
  return listFormat.format([...items.slice(0, max), `${items.length - max} more`]);
}

/** "23 Apr 2026" (order and wording follow the browser's locale).
 *  An unreadable date is shown as given rather than throwing. */
export function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : dateFormat.format(date);
}

const WORK_MODE_LABELS: Record<WorkMode, string> = {
  on_site: "on-site",
  hybrid: "hybrid",
  remote: "remote",
};

/** ["on_site", "remote"] becomes "On-site or remote". */
export function formatWorkModes(modes: WorkMode[]): string {
  const text = orListFormat.format(modes.map((mode) => WORK_MODE_LABELS[mode] ?? mode));
  return text.charAt(0).toUpperCase() + text.slice(1);
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["year", 365 * 24 * 3600],
  ["month", 30 * 24 * 3600],
  ["week", 7 * 24 * 3600],
  ["day", 24 * 3600],
  ["hour", 3600],
  ["minute", 60],
];

/** "3 hours ago", "yesterday", "just now". */
export function formatRelativeTime(iso: string, now: Date = new Date()): string {
  const seconds = (new Date(iso).getTime() - now.getTime()) / 1000;
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) {
      return relativeFormat.format(Math.round(seconds / size), unit);
    }
  }
  return "just now";
}