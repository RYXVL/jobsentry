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

export interface Job {
  source: string;
  id: string;
  title: string;
  url: string;
  company: string;
  teams: string[];
  locations: string[];
  remote: boolean;
  employment_type: string | null;
  tags: string[];
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
