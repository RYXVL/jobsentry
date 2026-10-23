import type { Job } from "../api/types";
import { formatDate, formatList, formatWorkModes } from "../utils/format";
import styles from "./JobList.module.css";

/**
 * One glass card per job: title, locations and work mode on the left, the
 * posting date on the right. Titles link to the company's own posting until
 * there is a details page.
 */
export function JobList({ jobs }: { jobs: Job[] }) {
  return (
    <ul className={styles.list}>
      {jobs.map((job) => (
        <li key={job.id} className={styles.item}>
          <div className={styles.summary}>
            <a href={job.url} target="_blank" rel="noreferrer" className={styles.title}>
              {job.title}
              <span className="visually-hidden"> (opens the posting in a new tab)</span>
            </a>
            {job.locations.length > 0 && <p className={styles.meta}>{formatList(job.locations)}</p>}
            {job.work_modes.length > 0 && (
              <p className={styles.meta}>Mode: {formatWorkModes(job.work_modes)}</p>
            )}
          </div>
          {job.posted_at && (
            <p className={styles.posted}>
              <span className={styles.label}>Posted</span>{" "}
              <time dateTime={job.posted_at}>{formatDate(job.posted_at)}</time>
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}