import { Link, useParams, useSearchParams } from "react-router-dom";

import { useJobFacets, useJobs, useRefreshSource, useSource } from "../api/queries";
import type { JobSort } from "../api/types";
import { Button } from "../components/Button";
import { JobFilters } from "../components/JobFilters";
import { JobList } from "../components/JobList";
import { JobSortSelect } from "../components/JobSortSelect";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatJobCount, formatNumber, formatRelativeTime } from "../utils/format";
import {
  hasFilters,
  normalizeFilters,
  type JobFilterValues,
} from "../utils/jobFilters";
import styles from "./SourceJobsPage.module.css";

/** Jobs shown per page (sent to the API as `limit`). */
const PAGE_SIZE = 10;
const DEFAULT_SORT: JobSort = "newest";

/** Everything about the list that lives in the URL, so a view survives a
 *  reload and can be shared: ?q=engineer&country=CA&country=US&sort=oldest&page=2 */
interface View {
  filters: JobFilterValues;
  sort: JobSort;
  page: number;
}

function readView(params: URLSearchParams): View {
  const sort = params.get("sort");
  return {
    filters: normalizeFilters({ keywords: params.get("q") ?? "", countries: params.getAll("country") }),
    sort: sort === "oldest" || sort === "newest" ? sort : DEFAULT_SORT,
    page: Math.max(1, Number.parseInt(params.get("page") ?? "1", 10) || 1),
  };
}

/** The URL query for a view, leaving out values that are the default. */
function viewSearch({ filters, sort, page }: View): URLSearchParams {
  const search = new URLSearchParams();
  if (filters.keywords) search.set("q", filters.keywords);
  for (const country of filters.countries) search.append("country", country);
  if (sort !== DEFAULT_SORT) search.set("sort", sort);
  if (page > 1) search.set("page", String(page));
  return search;
}

/** /sources/:source — one company's jobs: filtered by keywords and countries,
 *  in date-posted order, a page at a time. */
export function SourceJobsPage() {
  const { source = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const view = readView(searchParams);
  const { filters, sort, page } = view;
  const filtered = hasFilters(filters);

  const sourceInfo = useSource(source);
  const jobs = useJobs(source, {
    q: filters.keywords || undefined,
    country: filters.countries,
    sort,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  });
  const facets = useJobFacets(source, { enabled: jobs.isSuccess });
  const refresh = useRefreshSource(source);

  const company = sourceInfo.data?.company ?? source;
  useDocumentTitle(`${company} jobs`);

  const setView = (next: Partial<View>) => setSearchParams(viewSearch({ ...view, ...next }));

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

  const toolbar = (
    <div className={styles.toolbar}>
      <div className={styles.filters}>
        <JobFilters
          // Remount when the applied filters change (e.g. Back), so the form matches the URL.
          key={`${filters.keywords}\n${filters.countries.join(",")}`}
          applied={filters}
          countryOptions={facets.data?.countries ?? []}
          countriesLoading={facets.isPending}
          onApply={applyFilters}
        />
      </div>
      <JobSortSelect value={sort} onChange={changeSort} />
    </div>
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
          {(filtered || jobs.data.total > 0) && toolbar}

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
                <Link to={{ search: viewSearch({ ...view, page: 1 }).toString() }}>
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