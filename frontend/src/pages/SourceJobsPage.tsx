import { Link, useParams, useSearchParams } from "react-router-dom";

import { useJobs, useRefreshSource, useSource } from "../api/queries";
import { Button } from "../components/Button";
import { JobList } from "../components/JobList";
import { PageHeader } from "../components/PageHeader";
import { Pagination } from "../components/Pagination";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatJobCount, formatNumber, formatRelativeTime } from "../utils/format";
import styles from "./SourceJobsPage.module.css";

const PAGE_SIZE = 50;

/** /sources/:source — one company's jobs, a page at a time (?page=2). */
export function SourceJobsPage() {
  const { source = "" } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, Number.parseInt(searchParams.get("page") ?? "1", 10) || 1);

  const sourceInfo = useSource(source);
  const jobs = useJobs(source, { limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE });
  const refresh = useRefreshSource(source);

  const company = sourceInfo.data?.company ?? source;
  useDocumentTitle(`${company} jobs`);

  const goToPage = (next: number) => {
    setSearchParams(next > 1 ? { page: String(next) } : {});
    window.scrollTo({ top: 0 });
  };

  const intro = jobs.data
    ? `${formatJobCount(jobs.data.total)}, updated ${formatRelativeTime(jobs.data.fetched_at)}`
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
            ? `Fetching jobs from ${company}'s career site for the first time. This can take a minute.`
            : "Loading jobs…"}
        </StatusMessage>
      ) : jobs.isError ? (
        <ErrorNotice error={jobs.error} onRetry={() => jobs.refetch()} />
      ) : jobs.data.total === 0 ? (
        <StatusMessage>{company} has no open jobs right now. Refresh to check again.</StatusMessage>
      ) : jobs.data.jobs.length === 0 ? (
        <StatusMessage>
          This page is past the last job. <Link to={{ search: "" }}>Go to the first page</Link>
        </StatusMessage>
      ) : (
        <div className={jobs.isPlaceholderData ? styles.loading : undefined} aria-busy={jobs.isFetching}>
          <JobList jobs={jobs.data.jobs} />
          <Pagination
            page={page}
            totalPages={Math.ceil(jobs.data.total / PAGE_SIZE)}
            onChange={goToPage}
          />
        </div>
      )}
    </>
  );
}
