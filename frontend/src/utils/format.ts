/** Display formatting, using the browser's locale. */

const numberFormat = new Intl.NumberFormat();
const relativeFormat = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
const listFormat = new Intl.ListFormat(undefined, { style: "long", type: "conjunction" });

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
