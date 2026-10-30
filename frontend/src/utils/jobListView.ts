/**
 * The URL state shared by every job list page (filters, sort, page), and
 * how it maps to API parameters. Keeping it here means /sources/:source and
 * /today read and write the URL the same way:
 *
 *   ?q=engineer&country=CA&country=US&sort=oldest&page=2
 */

import type { JobListParams, JobSort } from "../api/types";
import { normalizeFilters, type JobFilterValues } from "./jobFilters";

/** Jobs shown per page (sent to the API as `limit`). */
export const PAGE_SIZE = 10;
export const DEFAULT_SORT: JobSort = "newest";

export interface JobListView {
  filters: JobFilterValues;
  sort: JobSort;
  page: number;
}

/** Read a view from the URL, falling back to defaults for anything missing or unknown. */
export function readJobListView(params: URLSearchParams): JobListView {
  const sort = params.get("sort");
  return {
    filters: normalizeFilters({ keywords: params.get("q") ?? "", countries: params.getAll("country") }),
    sort: sort === "oldest" || sort === "newest" ? sort : DEFAULT_SORT,
    page: Math.max(1, Number.parseInt(params.get("page") ?? "1", 10) || 1),
  };
}

/** The URL query for a view, leaving out values that are the default. */
export function jobListSearch({ filters, sort, page }: JobListView): URLSearchParams {
  const search = new URLSearchParams();
  if (filters.keywords) search.set("q", filters.keywords);
  for (const country of filters.countries) search.append("country", country);
  if (sort !== DEFAULT_SORT) search.set("sort", sort);
  if (page > 1) search.set("page", String(page));
  return search;
}

/** API parameters for a view: its filters, order and the page's slice. */
export function jobListParams({ filters, sort, page }: JobListView): JobListParams {
  return {
    q: filters.keywords || undefined,
    country: filters.countries,
    sort,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  };
}

/** A key that changes whenever the applied filters do, for resetting the filter form. */
export function filtersKey(filters: JobFilterValues): string {
  return `${filters.keywords}\n${filters.countries.join(",")}`;
}