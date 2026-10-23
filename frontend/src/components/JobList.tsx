import type { Job } from "../api/types";
import { formatDate, formatList, formatWorkModes } from "../utils/format";
import styles from "./JobList.module.css";

/**
 * One glass card per job: title, locations and work mode on the left, the
 * posting date on the right. The whole card links to the company's own
 * posting (in a new tab) until there is a details page.
 */
export function JobList({ jobs }: { jobs: Job[] }) {
  return (
    <ul className={styles.list}>
      {jobs.map((job) => (
        <li key={job.id}>
          <a href={job.url} target="_blank" rel="noreferrer" className={styles.card}>
            <span className={styles.summary}>
              <span className={styles.title}>{job.title}</span>
              {job.locations.length > 0 && (
                <span className={styles.meta}>{formatList(job.locations)}</span>
              )}
              {job.work_modes.length > 0 && (
                <span className={styles.meta}>Mode: {formatWorkModes(job.work_modes)}</span>
              )}
            </span>
            {job.posted_at && (
              <span className={styles.posted}>
                <span className={styles.label}>Posted</span>{" "}
                <time dateTime={job.posted_at}>{formatDate(job.posted_at)}</time>
              </span>
            )}
            <span className="visually-hidden"> (opens the posting in a new tab)</span>
          </a>
        </li>
      ))}
    </ul>
  );
}