import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { useAllJobs } from "../api/queries";
import type { JobSort } from "../api/types";
import { JobList } from "../components/JobList";
import { JobListToolbar } from "../components/JobListToolbar";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { localDateString, localTimeZone } from "../utils/dates";
import { formatDate, formatJobCount, formatList, formatRelativeTime } from "../utils/format";
import { hasFilters, type JobFilterValues } from "../utils/jobFilters";
import {
  PAGE_SIZE,
  jobListParams,
  jobListSearch,
  readJobListView,
  type JobListView,
} from "../utils/jobListView";
import styles from "./TodayJobsPage.module.css";

/**
 * /today: jobs from every company posted on today's date, in the viewer's
 * own time zone (only the date counts, not the time). Reads saved data only,
 * so it's instant; "Fetch all jobs" on the sources page gets fresh data.
 */
export function TodayJobsPage() {
  useDocumentTitle("Today's jobs");
  const [searchParams, setSearchParams] = useSearchParams();
  const view = readJobListView(searchParams);
  const { filters, sort, page } = view;
  const filtered = hasFilters(filters);

  // Fixed when the page opens, so the list doesn't shift at midnight mid-browse.
  const [now] = useState(() => new Date());
  const [timeZone] = useState(localTimeZone);
  const today = localDateString(now);

  const jobs = useAllJobs({ ...jobListParams(view), posted_on: today, tz: timeZone });

  const setView = (next: Partial<JobListView>) => setSearchParams(jobListSearch({ ...view, ...next }));

  const goToPage = (next: number) => {
    setView({ page: next });
    window.scrollTo({ top: 0 });
  };

  // New filters or a new order start again from page 1.
  const applyFilters = (next: JobFilterValues) => setView({ filters: next, page: 1 });
  const changeSort = (next: JobSort) => setView({ sort: next, page: 1 });

  const todayLabel = formatDate(now.toISOString());
  const intro = jobs.data
    ? `${formatJobCount(jobs.data.total)} posted on ${todayLabel}` +
      (jobs.data.fetched_at ? `, oldest saved data from ${formatRelativeTime(jobs.data.fetched_at)}` : "")
    : undefined;

  return (
    <>
      <PageHeader back={{ to: "/sources", label: "All sources" }} title="Today's jobs" intro={intro} />

      {jobs.data && jobs.data.unfetched.length > 0 && (
        <p className={styles.notice}>
          Not included yet, because they haven't been fetched:{" "}
          {formatList(jobs.data.unfetched, jobs.data.unfetched.length)}.{" "}
          <Link to="/sources">Fetch all jobs</Link> to include them.
        </p>
      )}

      {jobs.isPending ? (
        <StatusMessage>Loading today's jobs…</StatusMessage>
      ) : jobs.isError ? (
        <ErrorNotice error={jobs.error} onRetry={() => jobs.refetch()} />
      ) : (
        <>
          {/* Keep the filters on screen when they match nothing, so they can be changed. */}
          {(filtered || jobs.data.total > 0) && (
            <JobListToolbar
              filters={filters}
              countryOptions={jobs.data.countries}
              sort={sort}
              onApplyFilters={applyFilters}
              onChangeSort={changeSort}
            />
          )}

          <div className={jobs.isPlaceholderData ? styles.loading : undefined} aria-busy={jobs.isFetching}>
            {jobs.data.total === 0 ? (
              filtered ? (
                <StatusMessage>No jobs posted today match these filters.</StatusMessage>
              ) : (
                <StatusMessage>
                  No jobs posted today in the saved data.{" "}
                  <Link to="/sources">Fetch all jobs</Link> to check for new ones.
                </StatusMessage>
              )
            ) : jobs.data.jobs.length === 0 ? (
              <StatusMessage>
                This page is past the last job.{" "}
                <Link to={{ search: jobListSearch({ ...view, page: 1 }).toString() }}>
                  Go to the first page
                </Link>
              </StatusMessage>
            ) : (
              <>
                <JobList jobs={jobs.data.jobs} showCompany />
                <Pagination
                  page={page}
                  totalPages={Math.ceil(jobs.data.total / PAGE_SIZE)}
                  onChange={goToPage}
                />
              </>
            )}
          </div>
        </>
      )}
    </>
  );
}