import { useCatalog, useDeleteSource, useSources } from "../api/queries";
import type { Source } from "../api/types";
import { Button, ButtonLink } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { SourceLogo } from "../components/SourceLogo";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import styles from "./ManageSourcesPage.module.css";

/** /manage: every source, with Edit and Delete, and the way to add one. */
export function ManageSourcesPage() {
  useDocumentTitle("Manage sources");
  const catalog = useCatalog();
  const sources = useSources();
  const deleteSource = useDeleteSource();

  const platformLabel = (key: string) =>
    catalog.data?.platforms.find((platform) => platform.key === key)?.label ?? key;

  const remove = (source: Source) => {
    const message =
      `Delete ${source.company}? This can't be undone.\n\n` +
      "These will be removed:\n" +
      `• its entry in the ${platformLabel(source.strategy)} catalog\n` +
      "• all its saved jobs\n" +
      "• its logo";
    if (!window.confirm(message)) return;
    deleteSource.mutate(source.name);
  };

  if (catalog.data && !catalog.data.edits_allowed) {
    return (
      <>
        <PageHeader back={{ to: "/sources", label: "All sources" }} title="Manage sources" />
        <StatusMessage>
          Editing sources is turned off. Set <code>JOBSENTRY_ALLOW_CATALOG_EDITS=true</code> in{" "}
          <code>backend/.env</code> and restart the API.
        </StatusMessage>
      </>
    );
  }

  return (
    <>
      <PageHeader
        back={{ to: "/sources", label: "All sources" }}
        title="Manage sources"
        intro="Add, edit or delete the companies Job Sentry reads."
        actions={<ButtonLink to="/manage/new">Add source</ButtonLink>}
      />

      {deleteSource.isError && (
        <div className={styles.notice}>
          <ErrorNotice error={deleteSource.error} />
        </div>
      )}

      {sources.isPending ? (
        <StatusMessage>Loading sources…</StatusMessage>
      ) : sources.isError ? (
        <ErrorNotice error={sources.error} onRetry={() => sources.refetch()} />
      ) : sources.data.length === 0 ? (
        <StatusMessage>No sources yet. Add the first one.</StatusMessage>
      ) : (
        <ul className={styles.list}>
          {sources.data.map((source) => {
            const deleting = deleteSource.isPending && deleteSource.variables === source.name;
            return (
              <li key={source.name} className={styles.row}>
                <SourceLogo name={source.name} company={source.company} />
                <span className={styles.info}>
                  <span className={styles.company}>{source.company}</span>
                  <span className={styles.detail}>
                    {platformLabel(source.strategy)} · {source.name}
                  </span>
                </span>
                <span className={styles.actions}>
                  <ButtonLink to={`/manage/${encodeURIComponent(source.name)}`}>Edit</ButtonLink>
                  <Button busy={deleting} disabled={deleteSource.isPending} onClick={() => remove(source)}>
                    {deleting ? "Deleting…" : "Delete"}
                  </Button>
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}