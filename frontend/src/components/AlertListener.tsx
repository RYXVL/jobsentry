import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/endpoints";
import { queryKeys } from "../api/queries";
import { formatJobCount } from "../utils/format";
import styles from "./AlertListener.module.css";

/** How often an open tab checks in with the backend. */
const POLL_MS = 15_000;

/**
 * Mounted once for the whole site. Every 15 seconds it asks the backend for
 * the monitor's status and any new alerts. New alerts show a banner linking
 * to Today's jobs and refresh the job lists. The chime isn't played here:
 * the backend plays it on this computer the moment a fetch finds new jobs.
 */
export function AlertListener() {
  const queryClient = useQueryClient();
  const [banner, setBanner] = useState<number | null>(null); // new jobs to announce

  useEffect(() => {
    let after: number | null = null; // null: first poll, only learn the latest ID
    let cancelled = false;

    const tick = async () => {
      try {
        const poll = await api.pollMonitor(after);
        if (cancelled) return;
        queryClient.setQueryData(queryKeys.monitor, poll.monitor);
        if (after !== null && poll.events.length > 0) {
          setBanner(poll.events.reduce((total, event) => total + event.count, 0));
          void queryClient.invalidateQueries({ queryKey: queryKeys.sources });
        }
        after = poll.monitor.latest_event_id;
      } catch {
        // The API isn't reachable right now; try again next time.
      }
    };

    void tick();
    const timer = window.setInterval(() => void tick(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [queryClient]);

  if (banner === null) return null;
  return (
    <div className={styles.banner} role="status">
      <span>{formatJobCount(banner)} new, matching your monitor</span>
      <Link to="/today" onClick={() => setBanner(null)} className={styles.view}>
        View
      </Link>
      <button type="button" onClick={() => setBanner(null)} className={styles.dismiss}>
        Dismiss
      </button>
    </div>
  );
}