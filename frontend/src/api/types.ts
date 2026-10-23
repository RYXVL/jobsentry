/**
 * Response shapes from the backend. These mirror the Pydantic models in
 * backend/jobsentry/api/schemas.py; keep the two in sync.
 */

export interface Source {
  name: string;
  company: string;
  strategy: string;
  homepage: string;
  /** ISO 8601 time of the last refresh, or null if never fetched. */
  fetched_at: string | null;
  job_count: number | null;
}

/** How a job can be worked (backend: core.models.WORK_MODES). */
export type WorkMode = "on_site" | "hybrid" | "remote";

export interface Job {
  source: string;
  id: string;
  title: string;
  url: string;
  company: string;
  teams: string[];
  locations: string[];
  /** True if any location is remote. */
  remote: boolean;
  /** Only the modes the site states; empty if it doesn't say. */
  work_modes: WorkMode[];
  employment_type: string | null;
  tags: string[];
  /** ISO 8601: when the job was first published, null if unknown. */
  posted_at: string | null;
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

/** Optional filters for GET /sources/{source}/jobs. */
export interface JobListParams {
  q?: string;
  team?: string;
  location?: string;
  remote?: boolean;
  employment_type?: string;
  tag?: string;
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