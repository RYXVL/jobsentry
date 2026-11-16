import { useMonitor } from "../api/queries";
import { ButtonLink } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { TodayCallout } from "../components/TodayCallout";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatRelativeTime } from "../utils/format";
import styles from "./CommandCenterPage.module.css";

/** /command-center: today's jobs at the top, then the way to everything else. */
export function CommandCenterPage() {
  useDocumentTitle("Command center");
  const monitor = useMonitor();
  const status = monitor.data;

  const monitorNote = !status
    ? "Scheduled fetching and alerts"
    : !status.active
      ? "Off"
      : status.fetching
        ? "On: fetching now"
        : status.next_fetch_at
          ? `On: next fetch ${formatRelativeTime(status.next_fetch_at)}`
          : "On";

  return (
    <>
      <PageHeader title="Command center" intro="Today's new jobs, and everything that keeps them coming." />

      <TodayCallout />

      <nav aria-label="Command center" className={styles.tiles}>
        <div className={styles.tile}>
          <ButtonLink to="/sources" size="large" className={styles.button}>Sources</ButtonLink>
          <p className={styles.note}>Every company, and fetching all their jobs</p>
        </div>
        <div className={styles.tile}>
          <ButtonLink to="/manage" size="large" className={styles.button}>Manage sources</ButtonLink>
          <p className={styles.note}>Add, edit or delete companies</p>
        </div>
        <div className={styles.tile}>
          <ButtonLink to="/monitor" size="large" className={styles.button}>Monitor</ButtonLink>
          <p className={styles.note}>{monitorNote}</p>
        </div>
      </nav>
    </>
  );
}