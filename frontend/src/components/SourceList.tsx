import { Link } from "react-router-dom";

import type { Source } from "../api/types";
import { formatJobCount, formatRelativeTime } from "../utils/format";
import styles from "./SourceList.module.css";

export function SourceList({ sources }: { sources: Source[] }) {
  return (
    <ul className={styles.list}>
      {sources.map((source) => (
        <li key={source.name}>
          <Link to={`/sources/${encodeURIComponent(source.name)}`} className={styles.row}>
            <span className={styles.line}>
              <span className={styles.name}>{source.company}</span>
              <span className={styles.leader} aria-hidden="true" />
              {source.job_count === null ? (
                <span className={`${styles.count} ${styles.notFetched}`}>Not fetched</span>
              ) : (
                <span className={styles.count}>{formatJobCount(source.job_count)}</span>
              )}
            </span>
            <span className={styles.updated}>
              {source.fetched_at
                ? `Updated ${formatRelativeTime(source.fetched_at)}`
                : "Jobs are fetched the first time you open it"}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
