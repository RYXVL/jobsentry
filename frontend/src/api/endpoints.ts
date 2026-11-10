/**
 * One function per backend endpoint. Components never call fetch directly;
 * they use the hooks in ./queries.ts, which call these.
 */

import { request, toQueryString } from "./client";
import type {
  AllJobsPage,
  AllJobsParams,
  CatalogEntry,
  CatalogEntryInput,
  CatalogInfo,
  CheckInput,
  CheckResult,
  ClearResult,
  JobFacets,
  JobListParams,
  JobPage,
  MonitorPoll,
  MonitorSettings,
  MonitorStatus,
  RefreshResult,
  RefreshRun,
  Source,
} from "./types";

const sourcePath = (source: string) => `/sources/${encodeURIComponent(source)}`;
const catalogPath = (name: string) => `/catalog/sources/${encodeURIComponent(name)}`;

/** A JSON request body with the given method. */
const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  listSources: () => request<Source[]>("/sources"),

  getSource: (source: string) => request<Source>(sourcePath(source)),

  listJobs: (source: string, params: JobListParams = {}) =>
    request<JobPage>(`${sourcePath(source)}/jobs${toQueryString(params)}`),

  getJobFacets: (source: string) => request<JobFacets>(`${sourcePath(source)}/jobs/facets`),

  listAllJobs: (params: AllJobsParams = {}) =>
    request<AllJobsPage>(`/jobs${toQueryString(params)}`),

  refreshSource: (source: string) =>
    request<RefreshResult>(`${sourcePath(source)}/refresh`, { method: "POST" }),

  /** Starts fetching every source in the background (or returns the running run). */
  startRefreshAll: () => request<RefreshRun>("/sources/refresh", { method: "POST" }),

  /** Progress of the current or last fetch-all. */
  getRefreshRun: () => request<RefreshRun>("/sources/refresh"),

  clearAll: () => request<ClearResult>("/sources/clear", { method: "POST" }),

  // Managing sources

  getCatalog: () => request<CatalogInfo>("/catalog"),

  getCatalogEntry: (name: string) => request<CatalogEntry>(catalogPath(name)),

  checkBoards: (input: CheckInput) => request<CheckResult>("/catalog/check", json("POST", input)),

  addSource: (input: CatalogEntryInput) =>
    request<CatalogEntry>("/catalog/sources", json("POST", input)),

  updateSource: (name: string, input: CatalogEntryInput) =>
    request<CatalogEntry>(catalogPath(name), json("PUT", input)),

  deleteSource: (name: string) => request<{ name: string }>(catalogPath(name), { method: "DELETE" }),

  /** Sends the PNG file itself as the body; saved as public/logos/<name>.png. */
  uploadLogo: (name: string, file: Blob) =>
    request<{ name: string }>(`${catalogPath(name)}/logo`, {
      method: "PUT",
      headers: { "Content-Type": "image/png" },
      body: file,
    }),

  deleteLogo: (name: string) =>
    request<{ name: string }>(`${catalogPath(name)}/logo`, { method: "DELETE" }),

  // Monitor

  getMonitor: () => request<MonitorStatus>("/monitor"),

  saveMonitorSettings: (settings: MonitorSettings) =>
    request<MonitorStatus>("/monitor/settings", json("PUT", settings)),

  startMonitor: () => request<MonitorStatus>("/monitor/start", { method: "POST" }),

  stopMonitor: () => request<MonitorStatus>("/monitor/stop", { method: "POST" }),

  /** Called every 15 seconds by AlertListener; also tells the backend a tab is open. */
  pollMonitor: (after: number | null) =>
    request<MonitorPoll>(`/monitor/poll${toQueryString({ after: after ?? undefined })}`),

  sendTestEmail: (emailTo: string) =>
    request<{ message: string }>("/monitor/test-email", json("POST", { email_to: emailTo })),

  confirmEmail: (emailTo: string, received: boolean) =>
    request<MonitorStatus>("/monitor/confirm-email", json("POST", { email_to: emailTo, received })),
};