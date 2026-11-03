import type { RefreshRun } from "../api/types";
import { formatJobCount, formatList, formatRelativeTime } from "../utils/format";
import styles from "./RefreshProgress.module.css";

/**
 * Progress of fetching every source: a bar, how many companies and jobs are
 * done, who's being fetched now, and any failures. Shows the last run's
 * result once it finishes; nothing before the first run.
 */
export function RefreshProgress({ run }: { run: RefreshRun }) {
  if (run.state === "idle") return null;

  const running = run.state === "running";
  const percent = run.total > 0 ? Math.round((run.completed / run.total) * 100) : 100;
  const failures = run.results.filter((result) => !result.ok);

  const summary = running
    ? `${run.completed} of ${run.total} companies done, ${formatJobCount(run.jobs_fetched)} fetched so far`
    : `Fetched ${run.succeeded} of ${run.total} companies, ${formatJobCount(run.jobs_fetched)} in total` +
      (run.finished_at ? `, finished ${formatRelativeTime(run.finished_at)}` : "");

  return (
    <section className={styles.progress} aria-label="Fetching all jobs">
      <div
        className={styles.bar}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={run.total}
        aria-valuenow={run.completed}
        aria-valuetext={`${run.completed} of ${run.total} companies`}
      >
        <div className={styles.fill} style={{ width: `${percent}%` }} />
      </div>

      <p className={styles.summary} role="status">
        {summary}
      </p>

      {running && run.in_progress.length > 0 && (
        <p className={styles.detail}>
          Now fetching: {formatList(run.in_progress, run.in_progress.length)}
        </p>
      )}

      {failures.length > 0 && (
        <ul className={styles.failures}>
          {failures.map((result) => (
            <li key={result.source}>
              {result.company}: {result.error?.message ?? "failed"}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}