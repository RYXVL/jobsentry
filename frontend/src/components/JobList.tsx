import type { Job } from "../api/types";
import { formatList } from "../utils/format";
import styles from "./JobList.module.css";

/** Jobs link to the company's own posting until we add a details page. */
export function JobList({ jobs }: { jobs: Job[] }) {
  return (
    <ul className={styles.list}>
      {jobs.map((job) => (
        <li key={job.id} className={styles.item}>
          <a href={job.url} target="_blank" rel="noreferrer" className={styles.title}>
            {job.title}
            <span className="visually-hidden"> (opens the posting in a new tab)</span>
          </a>
          {job.teams.length > 0 && <p className={styles.meta}>{job.teams.join(", ")}</p>}
          {job.locations.length > 0 && <p className={styles.meta}>{formatList(job.locations)}</p>}
        </li>
      ))}
    </ul>
  );
}
