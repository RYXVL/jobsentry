import { useSources } from "../api/queries";
import { PageHeader } from "../components/PageHeader";
import { SourceList } from "../components/SourceList";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

/** /sources: every company jobsentry can read. */
export function SourcesPage() {
  useDocumentTitle("Sources");
  const sources = useSources();

  return (
    <>
      <PageHeader title="Sources" intro="Choose a company to see its open jobs." />
      {sources.isPending ? (
        <StatusMessage>Loading sources…</StatusMessage>
      ) : sources.isError ? (
        <ErrorNotice error={sources.error} onRetry={() => sources.refetch()} />
      ) : sources.data.length === 0 ? (
        <StatusMessage>
          No sources yet. Add one in <code>backend/jobsentry/sources/companies/</code>.
        </StatusMessage>
      ) : (
        <SourceList sources={sources.data} />
      )}
    </>
  );
}
