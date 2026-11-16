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

/** GET /jobs: one page of jobs from every fetched source. */
export interface AllJobsPage {
  /** All matching jobs across every source, not just this page. */
  total: number;
  limit: number;
  offset: number;
  /** Oldest last refresh among the sources included; null if none fetched. */
  fetched_at: string | null;
  /** Companies never fetched, so not included. */
  unfetched: string[];
  /** Countries among jobs matching the date filter only, for the country picker. */
  countries: FacetValue[];
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

/** One source's result inside a fetch-all run. */
export interface RefreshItem {
  source: string;
  company: string;
  ok: boolean;
  fetched_at: string | null;
  job_count: number | null;
  /** Why it failed; null when ok. */
  error: ApiErrorBody["error"] | null;
}

/** GET and POST /sources/refresh: progress of fetching every source. */
export interface RefreshRun {
  /** "idle" means none has run since the API started. */
  state: "idle" | "running" | "done";
  /** What started the run: the "Fetch all jobs" button or the monitor. */
  trigger: "manual" | "monitor" | null;
  started_at: string | null;
  finished_at: string | null;
  /** Sources in this run. */
  total: number;
  /** Sources finished, successfully or not. */
  completed: number;
  succeeded: number;
  failed: number;
  /** Jobs saved so far, across finished sources. */
  jobs_fetched: number;
  /** Companies being fetched right now. */
  in_progress: string[];
  /** One per finished source, in finishing order. */
  results: RefreshItem[];
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

/** GET /jobs takes the same options, plus a date filter. */
export interface AllJobsParams extends JobListParams {
  /** Only jobs first published on this date (YYYY-MM-DD), in `tz`. */
  posted_on?: string;
  /** IANA time zone for posted_on, e.g. "Asia/Kolkata". Defaults to UTC. */
  tz?: string;
}

/** Every API error has this body (see backend/jobsentry/api/errors.py). */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown[];
  };
}

// Managing sources (/catalog) ------------------------------------------------

/** A platform sources can be added for. */
export interface Platform {
  key: string;
  label: string;
  /** True for Lever: global or EU instance. */
  has_region: boolean;
}

/** GET /catalog. */
export interface CatalogInfo {
  /** JOBSENTRY_ALLOW_CATALOG_EDITS. */
  edits_allowed: boolean;
  platforms: Platform[];
}

export type LeverRegion = "global" | "eu";

/** A source's catalog entry, as the form edits it. */
export interface CatalogEntry {
  platform: string;
  name: string;
  company: string;
  board_names: string[];
  homepage: string | null;
  region: LeverRegion | null;
  /** Keys the form doesn't edit, kept as they are (e.g. country_hints). */
  extra_keys: string[];
}

/** What the form sends to add or edit a source. */
export type CatalogEntryInput = Omit<CatalogEntry, "extra_keys">;

/** POST /catalog/check body. */
export interface CheckInput {
  platform: string;
  board_names: string[];
  region: LeverRegion | null;
}

/** The result of checking one board name. */
export interface BoardCheckResult {
  board_name: string;
  ok: boolean;
  status: number | null;
  job_count: number | null;
  message: string;
  /** The request that was made. */
  url: string;
}

/** POST /catalog/check. */
export interface CheckResult {
  /** True when every board passed. */
  ok: boolean;
  boards: BoardCheckResult[];
}

// Monitor (/monitor) ---------------------------------------------------------

export type MonitorUnit = "minutes" | "hours";

export interface MonitorSettings {
  /** 15, 30 or 45 (minutes), or 1 to 24 (hours). */
  every: number;
  unit: MonitorUnit;
  /** Same matching as Today's jobs; empty = every new job. */
  keywords: string;
  sound: boolean;
  email: boolean;
  email_to: string;
}

/** GET /monitor. */
export interface MonitorStatus {
  settings: MonitorSettings;
  active: boolean;
  started_at: string | null;
  next_fetch_at: string | null;
  /** A fetch of every source is running. */
  fetching: boolean;
  /** When the last fetch of every source started (the watermark). */
  last_fetch_started_at: string | null;
  /** JOBSENTRY_SMTP_* is set in backend/.env. */
  email_configured: boolean;
  /** A test email to settings.email_to was confirmed. */
  email_verified: boolean;
  last_email: { at: string; ok: boolean; error: string | null } | null;
  latest_event_id: number;
}

export interface MonitorJob {
  source: string;
  id: string;
  title: string;
  company: string;
  url: string;
  locations: string[];
  posted_at: string | null;
}

/** One alert: the new jobs one fetch found. The chime was already played
 *  by the computer when it happened. */
export interface MonitorEvent {
  id: number;
  at: string;
  count: number;
  jobs: MonitorJob[];
}

/** GET /monitor/poll. */
export interface MonitorPoll {
  monitor: MonitorStatus;
  events: MonitorEvent[];
}