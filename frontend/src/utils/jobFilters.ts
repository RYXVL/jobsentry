/**
 * The job list filters a person can apply, and helpers for comparing them.
 * Shared by SourceJobsPage (which keeps the applied filters in the URL) and
 * JobFilters (which edits a draft until "Apply filters" is pressed).
 * To add a filter: add a field here, handle it in normalizeFilters,
 * hasFilters and sameFilters, then in the page's URL helpers and the form.
 */

export interface JobFilterValues {
  /** Words that must all appear in the title or a team name. */
  keywords: string;
  /** ISO country codes; a job in any of them matches. */
  countries: string[];
}

export const EMPTY_FILTERS: JobFilterValues = { keywords: "", countries: [] };

/** Trim keywords and collapse their spaces; upper-case, de-duplicate and
 *  sort countries. Equal filters then always look the same, in the URL and
 *  in React Query's cache keys. */
export function normalizeFilters({ keywords, countries }: JobFilterValues): JobFilterValues {
  return {
    keywords: keywords.trim().replace(/\s+/g, " "),
    countries: [...new Set(countries.map((c) => c.trim().toUpperCase()).filter(Boolean))].sort(),
  };
}

/** True if any filter is set. */
export function hasFilters(filters: JobFilterValues): boolean {
  const { keywords, countries } = normalizeFilters(filters);
  return keywords !== "" || countries.length > 0;
}

/** True if both filter the same jobs once normalised. */
export function sameFilters(a: JobFilterValues, b: JobFilterValues): boolean {
  const x = normalizeFilters(a);
  const y = normalizeFilters(b);
  return x.keywords === y.keywords && x.countries.join(",") === y.countries.join(",");
}