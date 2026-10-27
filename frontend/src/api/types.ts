/**
 * Response shapes from the backend. These mirror the Pydantic models in
 * backend/jobsentry/api/schemas.py; keep the two in sync.
 */

export interface Source {
  name: string;
  company: string;
  /** Which platform the jobs come from, e.g. "greenhouse". */
  strategy: string;
  homepage: string;
  /** ISO 8601 time of the last refresh, or null if never fetched. */
  fetched_at: string | null;
  job_count: number | null;
}

/** How a job can be worked (backend: core.models.WORK_MODES). */
export type WorkMode = "on_site" | "hybrid" | "remote";

/** Job list order by date posted (backend: services.queries.JobSort). */
export type JobSort = "newest" | "oldest";

export interface Job {
  source: string;
  id: string;
  title: string;
  url: string;
  company: string;
  teams: string[];
  locations: string[];
  /** ISO 3166-1 alpha-2 codes, e.g. ["CA", "US"]. */
  countries: string[];
  /** Only the modes the source states; empty if it doesn't say. */
  work_modes: WorkMode[];
  employment_type: string | null;
  /** ISO 8601: when the job was first published, null if unknown. */
  posted_at: string | null;
  /** ISO 8601: when the platform last changed the job, null if unknown.
   *  Can reflect bulk edits, so many jobs may share one time. */
  updated_at: string | null;
}

export interface JobPage {
  source: string;
  fetched_at: string;
  /** All jobs matching the filters, not just this page. */
  total: number;
  limit: number;
  offset: number;
  jobs: Job[];
}

/** One value and how many saved jobs have it. */
export interface FacetValue {
  value: string;
  count: number;
}

/** GET /sources/{source}/jobs/facets: values present in the saved jobs. */
export interface JobFacets {
  source: string;
  teams: FacetValue[];
  locations: FacetValue[];
  /** Values are ISO country codes. */
  countries: FacetValue[];
}

export interface RefreshResult {
  source: string;
  fetched_at: string;
  job_count: number;
}

/** One source's result inside a refresh-all. */
export interface RefreshItem {
  source: string;
  company: string;
  ok: boolean;
  fetched_at: string | null;
  job_count: number | null;
  /** Why it failed; null when ok. */
  error: ApiErrorBody["error"] | null;
}

export interface RefreshAllResult {
  results: RefreshItem[];
  succeeded: number;
  failed: number;
}

export interface ClearResult {
  /** How many sources had saved data. */
  cleared_sources: number;
}

/** Optional filters, order and paging for GET /sources/{source}/jobs. */
export interface JobListParams {
  /** Keywords: every word must appear in the title or a team name. */
  q?: string;
  /** ISO country codes; a job in any of them matches. */
  country?: string[];
  /** Defaults to "newest" on the backend. */
  sort?: JobSort;
  limit?: number;
  offset?: number;
}

/** Every API error has this body (see backend/jobsentry/api/errors.py). */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown[];
  };
}