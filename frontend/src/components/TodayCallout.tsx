import { useId, useState } from "react";

import { useAllJobs } from "../api/queries";
import { localDateString, localTimeZone } from "../utils/dates";
import { formatJobCount } from "../utils/format";
import { ButtonLink } from "./Button";
import styles from "./TodayCallout.module.css";

/**
 * The command center on the sources page: how many jobs were posted today
 * across every company, and the way into /today. The count comes from saved
 * data in one quick request (limit 1, only `total` is used), so it never
 * contacts a job board. "Today" is the viewer's local date.
 */
export function TodayCallout() {
  const headingId = useId();
  const [now] = useState(() => new Date());
  const [timeZone] = useState(localTimeZone);
  const today = useAllJobs({ posted_on: localDateString(now), tz: timeZone, limit: 1 });

  const count = today.data?.total;
  const summary = today.isError
    ? "Open the list to see what's new."
    : count === undefined
      ? "Counting…"
      : count === 0
        ? "Nothing posted yet today"
        : `${formatJobCount(count)} posted today`;

  return (
    <section className={styles.callout} aria-labelledby={headingId}>
      <div className={styles.text}>
        <h2 id={headingId} className={styles.heading}>
          Today's jobs
        </h2>
        <p className={styles.count} aria-live="polite">
          {summary}
        </p>
        <p className={styles.hint}>Every company in one list, newest first. Be the first to apply.</p>
      </div>
      <ButtonLink to="/today" size="large">
        See today's jobs
      </ButtonLink>
    </section>
  );
}