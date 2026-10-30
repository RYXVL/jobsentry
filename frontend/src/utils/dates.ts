/** Dates in the browser's own time zone, for date filters like "today". */

/** The browser's IANA time zone, e.g. "Asia/Kolkata" (UTC if unknown). */
export function localTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
}

/** `date` as YYYY-MM-DD in local time; by default today's date. Built from
 *  the local parts rather than toISOString(), which would give the UTC date. */
export function localDateString(date: Date = new Date()): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}