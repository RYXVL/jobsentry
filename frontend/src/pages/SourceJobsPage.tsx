import { Link, useParams, useSearchParams } from "react-router-dom";

import { useJobFacets, useJobs, useRefreshSource, useSource } from "../api/queries";
import type { JobSort } from "../api/types";
import { Button } from "../components/Button";
import { JobList } from "../components/JobList";
import { JobListToolbar } from "../components/JobListToolbar";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatJobCount, formatNumber, formatRelativeTime } from "../utils/format";
import { hasFilters, type JobFilterValues } from "../utils/jobFilters";
import {
  PAGE_SIZE,
  jobListParams,
  jobListSearch,
  readJobListView,
  type JobListView,
} from "../utils/jobListView";
import styles from "./SourceJobsPage.module.css";

/** /sources/:source — one company's jobs: filtered by keywords and countries,
 *  in date-posted order, a page at a time (URL format in utils/jobListView.ts). */
export function SourceJobsPage() {
  const { source = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const view = readJobListView(searchParams);
  const { filters, sort, page } = view;
  const filtered = hasFilters(filters);

  const sourceInfo = useSource(source);
  const jobs = useJobs(source, jobListParams(view));
  const facets = useJobFacets(source, { enabled: jobs.isSuccess });
  const refresh = useRefreshSource(source);

  const company = sourceInfo.data?.company ?? source;
  useDocumentTitle(`${company} jobs`);

  const setView = (next: Partial<JobListView>) => setSearchParams(jobListSearch({ ...view, ...next }));

  const goToPage = (next: number) => {
    setView({ page: next });
    window.scrollTo({ top: 0 });
  };

  // New filters or a new order start again from page 1.
  const applyFilters = (next: JobFilterValues) => setView({ filters: next, page: 1 });
  const changeSort = (next: JobSort) => setView({ sort: next, page: 1 });

  const totalJobs = sourceInfo.data?.job_count;
  const intro = jobs.data
    ? filtered && totalJobs != null
      ? `${formatNumber(jobs.data.total)} of ${formatJobCount(totalJobs)} match, updated ${formatRelativeTime(jobs.data.fetched_at)}`
      : `${formatJobCount(jobs.data.total)}, updated ${formatRelativeTime(jobs.data.fetched_at)}`
    : undefined;

  const refreshButton = (
    <>
      <Button busy={refresh.isPending} onClick={() => refresh.mutate()}>
        {refresh.isPending ? "Refreshing…" : "Refresh jobs"}
      </Button>
      <p className={styles.refreshed} role="status">
        {refresh.isSuccess && `Jobs refreshed: ${formatNumber(refresh.data.job_count)} found`}
      </p>
    </>
  );

  return (
    <>
      <PageHeader
        back={{ to: "/sources", label: "All sources" }}
        title={company}
        intro={intro}
        actions={jobs.isSuccess ? refreshButton : undefined}
      />

      {refresh.isError && (
        <div className={styles.refreshError}>
          <ErrorNotice error={refresh.error} />
        </div>
      )}

      {jobs.isPending ? (
        <StatusMessage>
          {sourceInfo.data?.fetched_at === null
            ? `Fetching jobs from ${company} for the first time. This can take a minute.`
            : "Loading jobs…"}
        </StatusMessage>
      ) : jobs.isError ? (
        <ErrorNotice error={jobs.error} onRetry={() => jobs.refetch()} />
      ) : (
        <>
          {/* Keep the filters on screen when they match nothing, so they can be changed. */}
          {(filtered || jobs.data.total > 0) && (
            <JobListToolbar
              filters={filters}
              countryOptions={facets.data?.countries ?? []}
              countriesLoading={facets.isPending}
              sort={sort}
              onApplyFilters={applyFilters}
              onChangeSort={changeSort}
            />
          )}

          <div className={jobs.isPlaceholderData ? styles.loading : undefined} aria-busy={jobs.isFetching}>
            {jobs.data.total === 0 ? (
              filtered ? (
                <StatusMessage>No jobs match these filters.</StatusMessage>
              ) : (
                <StatusMessage>{company} has no open jobs right now. Refresh to check again.</StatusMessage>
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
                <JobList jobs={jobs.data.jobs} />
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