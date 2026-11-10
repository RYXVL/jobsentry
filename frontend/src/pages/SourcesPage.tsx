import { useCatalog, useClearAll, useRefreshRun, useSources, useStartRefreshAll } from "../api/queries";
import { Button, ButtonLink } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { RefreshProgress } from "../components/RefreshProgress";
import { SourceList } from "../components/SourceList";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { TodayCallout } from "../components/TodayCallout";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import styles from "./SourcesPage.module.css";

const CONFIRM_CLEAR = "Delete all saved jobs for every company? This can't be undone.";

/** /sources: every company Job Sentry can read, with today's jobs on top
 *  and the progress of "Fetch all jobs" under the buttons. */
export function SourcesPage() {
  useDocumentTitle("Sources");
  const sources = useSources();
  const catalog = useCatalog();
  const run = useRefreshRun();
  const startRefresh = useStartRefreshAll();
  const clearAll = useClearAll();

  const fetching = startRefresh.isPending || run.data?.state === "running";
  const busy = fetching || clearAll.isPending;

  const fetchAll = () => {
    clearAll.reset();
    startRefresh.mutate();
  };

  const clear = () => {
    if (!window.confirm(CONFIRM_CLEAR)) return;
    startRefresh.reset();
    clearAll.mutate();
  };

  const actions = (
    <div className={styles.actions}>
      <Button busy={fetching} disabled={busy} onClick={fetchAll}>
        {fetching ? "Fetching…" : "Fetch all jobs"}
      </Button>
      <Button busy={clearAll.isPending} disabled={busy} onClick={clear}>
        {clearAll.isPending ? "Clearing…" : "Clear saved jobs"}
      </Button>
      {catalog.data?.edits_allowed && <ButtonLink to="/manage">Manage sources</ButtonLink>}
    </div>
  );

  return (
    <>
      <PageHeader
        title="Sources"
        intro="Choose a company to see its open jobs."
        actions={sources.isSuccess ? actions : undefined}
      />

      {run.data && <RefreshProgress run={run.data} />}

      {startRefresh.isError && <div className={styles.notice}><ErrorNotice error={startRefresh.error} /></div>}
      {clearAll.isError && <div className={styles.notice}><ErrorNotice error={clearAll.error} /></div>}
      <div className={styles.notice} role="status">
        {clearAll.isSuccess && "Saved jobs cleared. Open a company, or fetch all, to get them again."}
      </div>

      {sources.isPending ? (
        <StatusMessage>Loading sources…</StatusMessage>
      ) : sources.isError ? (
        <ErrorNotice error={sources.error} onRetry={() => sources.refetch()} />
      ) : sources.data.length === 0 ? (
        <StatusMessage>No sources yet. Use “Manage sources” to add one.</StatusMessage>
      ) : (
        <>
          <TodayCallout />
          <SourceList sources={sources.data} />
        </>
      )}
    </>
  );
}