import { useClearAll, useRefreshRun, useSources, useStartRefreshAll } from "../api/queries";
import { Button } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { RefreshProgress } from "../components/RefreshProgress";
import { SourceList } from "../components/SourceList";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import styles from "./SourcesPage.module.css";

const CONFIRM_CLEAR = "Delete all saved jobs for every company? This can't be undone.";
const MONITOR_FETCHING =
  "The monitor is fetching every company right now. This is available again when it finishes.";

/** /sources: every company Job Sentry reads, with "Fetch all jobs" and its progress. */
export function SourcesPage() {
  useDocumentTitle("Sources");
  const sources = useSources();
  const run = useRefreshRun();
  const startRefresh = useStartRefreshAll();
  const clearAll = useClearAll();

  const fetching = startRefresh.isPending || run.data?.state === "running";
  const monitorFetching = run.data?.state === "running" && run.data.trigger === "monitor";
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
      {/* The wrapper carries the hover text, since some browsers don't show
          it on a disabled button itself. */}
      <span title={monitorFetching ? MONITOR_FETCHING : undefined}>
        <Button busy={fetching} disabled={busy} onClick={fetchAll}>
          {monitorFetching ? "Monitor fetching…" : fetching ? "Fetching…" : "Fetch all jobs"}
        </Button>
      </span>
      <Button busy={clearAll.isPending} disabled={busy} onClick={clear}>
        {clearAll.isPending ? "Clearing…" : "Clear saved jobs"}
      </Button>
    </div>
  );

  return (
    <>
      <PageHeader
        back={{ to: "/command-center", label: "Command center" }}
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
        <StatusMessage>No sources yet. Use Manage sources in the command center to add one.</StatusMessage>
      ) : (
        <SourceList sources={sources.data} />
      )}
    </>
  );
}