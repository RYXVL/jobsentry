import { Link } from "react-router-dom";

import type { Source } from "../api/types";
import { formatNumber, formatRelativeTime } from "../utils/format";
import { SourceLogo } from "./SourceLogo";
import styles from "./SourceList.module.css";

/**
 * Every source as a frosted-glass card, three per row at most (fewer on
 * narrow screens). Each card links to that source's jobs.
 */
export function SourceList({ sources }: { sources: Source[] }) {
  return (
    <ul className={styles.grid}>
      {sources.map((source) => (
        <li key={source.name} className={styles.item}>
          <SourceCard source={source} />
        </li>
      ))}
    </ul>
  );
}

/** One company: logo, name, job count and when it was last fetched. */
function SourceCard({ source }: { source: Source }) {
  return (
    <Link to={`/sources/${encodeURIComponent(source.name)}`} className={styles.card}>
      <span className={styles.head}>
        <SourceLogo name={source.name} company={source.company} />
        <span className={styles.name}>{source.company}</span>
      </span>

      <dl className={styles.details}>
        <dt>Jobs</dt>
        {source.job_count === null ? (
          <dd className={styles.muted}>Not fetched</dd>
        ) : (
          <dd>{formatNumber(source.job_count)}</dd>
        )}

        <dt>Updated</dt>
        {source.fetched_at === null ? (
          <dd className={styles.muted}>Never</dd>
        ) : (
          <dd>
            <time dateTime={source.fetched_at} title={new Date(source.fetched_at).toLocaleString()}>
              {formatRelativeTime(source.fetched_at)}
            </time>
          </dd>
        )}
      </dl>
    </Link>
  );
}