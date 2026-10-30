import type { Job } from "../api/types";
import { formatDate, formatList, formatWorkModes } from "../utils/format";
import styles from "./JobList.module.css";
import { SourceLogo } from "./SourceLogo";

interface JobListProps {
  jobs: Job[];
  /** Show a company chip (logo and name) above each title, for lists mixing
   *  several companies. */
  showCompany?: boolean;
}

/**
 * One glass card per job: title, locations and work mode on the left, the
 * dates on the right. The whole card links to the company's own posting (in
 * a new tab) until there is a details page.
 */
export function JobList({ jobs, showCompany = false }: JobListProps) {
  return (
    <ul className={styles.list}>
      {jobs.map((job) => (
        // IDs are only unique within a source, so the key includes it.
        <li key={`${job.source}:${job.id}`}>
          <a href={job.url} target="_blank" rel="noreferrer" className={styles.card}>
            <span className={styles.summary}>
              {showCompany && (
                <span className={styles.company}>
                  <SourceLogo name={job.source} company={job.company} size="small" />
                  <span>{job.company}</span>
                </span>
              )}
              <span className={styles.title}>{job.title}</span>
              {job.locations.length > 0 && (
                <span className={styles.meta}>{formatList(job.locations)}</span>
              )}
              {job.work_modes.length > 0 && (
                <span className={styles.meta}>Mode: {formatWorkModes(job.work_modes)}</span>
              )}
            </span>
            <JobDates job={job} />
            <span className="visually-hidden"> (opens the posting in a new tab)</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

/** True if two ISO 8601 times are the same moment, even when written with
 *  different zone offsets. Unreadable times fall back to comparing the text. */
function sameMoment(a: string, b: string): boolean {
  const timeA = new Date(a).getTime();
  const timeB = new Date(b).getTime();
  if (Number.isNaN(timeA) || Number.isNaN(timeB)) return a === b;
  return timeA === timeB;
}

/** "Updated" above "Posted". Updated is shown whenever it differs from the
 *  posted time (a job never changed since posting has the two equal).
 *  Renders nothing if neither date is known. */
function JobDates({ job }: { job: Job }) {
  const { posted_at: posted, updated_at: updated } = job;
  const showUpdated = updated != null && (posted == null || !sameMoment(updated, posted));

  if (posted == null && !showUpdated) return null;

  return (
    <span className={styles.dates}>
      {showUpdated && <DateLine label="Updated" iso={updated} />}
      {posted != null && <DateLine label="Posted" iso={posted} />}
    </span>
  );
}

function DateLine({ label, iso }: { label: string; iso: string }) {
  return (
    <span>
      <span className={styles.label}>{label}</span>{" "}
      <time dateTime={iso}>{formatDate(iso)}</time>
    </span>
  );
}