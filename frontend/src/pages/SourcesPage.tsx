import { useClearAll, useRefreshAll, useSources } from "../api/queries";
import { Button } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { SourceList } from "../components/SourceList";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { TodayCallout } from "../components/TodayCallout";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatJobCount } from "../utils/format";
import styles from "./SourcesPage.module.css";

const CONFIRM_CLEAR = "Delete all saved jobs for every company? This can't be undone.";

/** /sources: every company Job Sentry can read, with today's jobs on top. */
export function SourcesPage() {
  useDocumentTitle("Sources");
  const sources = useSources();
  const refreshAll = useRefreshAll();
  const clearAll = useClearAll();
  const busy = refreshAll.isPending || clearAll.isPending;

  const fetchAll = () => {
    clearAll.reset();
    refreshAll.mutate();
  };

  const clear = () => {
    if (!window.confirm(CONFIRM_CLEAR)) return;
    refreshAll.reset();
    clearAll.mutate();
  };

  const actions = (
    <div className={styles.actions}>
      <Button busy={refreshAll.isPending} disabled={busy} onClick={fetchAll}>
        {refreshAll.isPending ? "Fetching…" : "Fetch all jobs"}
      </Button>
      <Button busy={clearAll.isPending} disabled={busy} onClick={clear}>
        {clearAll.isPending ? "Clearing…" : "Clear saved jobs"}
      </Button>
    </div>
  );

  return (
    <>
      <PageHeader
        title="Sources"
        intro="Choose a company to see its open jobs."
        actions={sources.isSuccess && sources.data.length > 0 ? actions : undefined}
      />

      <div className={styles.notice} role="status">
        {refreshAll.isPending && "Fetching jobs from every company, one at a time. This can take a few minutes."}
        {refreshAll.isSuccess && (
          <>
            <p>
              Fetched {refreshAll.data.succeeded} of {refreshAll.data.results.length} sources,{" "}
              {formatJobCount(refreshAll.data.results.reduce((sum, r) => sum + (r.job_count ?? 0), 0))} in total.
            </p>
            {refreshAll.data.failed > 0 && (
              <ul className={styles.failures}>
                {refreshAll.data.results
                  .filter((result) => !result.ok)
                  .map((result) => (
                    <li key={result.source}>
                      {result.company}: {result.error?.message}
                    </li>
                  ))}
              </ul>
            )}
          </>
        )}
        {clearAll.isSuccess && "Saved jobs cleared. Open a company, or fetch all, to get them again."}
      </div>

      {refreshAll.isError && <div className={styles.notice}><ErrorNotice error={refreshAll.error} /></div>}
      {clearAll.isError && <div className={styles.notice}><ErrorNotice error={clearAll.error} /></div>}

      {sources.isPending ? (
        <StatusMessage>Loading sources…</StatusMessage>
      ) : sources.isError ? (
        <ErrorNotice error={sources.error} onRetry={() => sources.refetch()} />
      ) : sources.data.length === 0 ? (
        <StatusMessage>
          No sources yet. Add one to{" "}
          <code>backend/jobsentry/sources/catalogs/greenhouse-sources.json</code>.
        </StatusMessage>
      ) : (
        <>
          <TodayCallout />
          <SourceList sources={sources.data} />
        </>
      )}
    </>
  );
}