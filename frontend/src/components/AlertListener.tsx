import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api/endpoints";
import { queryKeys } from "../api/queries";
import { playChime, unlockAudio } from "../utils/chime";
import { formatJobCount } from "../utils/format";
import styles from "./AlertListener.module.css";

/** How often an open tab checks in with the backend. */
const POLL_MS = 15_000;
/** Shared by every tab, so each alert chimes once, not once per tab. */
const CHIMED_KEY = "jobsentry:last-chimed-alert";

/**
 * Mounted once for the whole site. Every 15 seconds it asks the backend for
 * new monitor alerts; that also tells the backend a tab is open, so the tab
 * (not the computer) plays the chime. New alerts show a banner linking to
 * Today's jobs, chime once across all tabs, and refresh saved-data views.
 */
export function AlertListener() {
  const queryClient = useQueryClient();
  const [banner, setBanner] = useState<number | null>(null); // new jobs to announce

  // Browsers only allow sound after an interaction: unlock on the first one.
  useEffect(() => {
    const unlock = () => unlockAudio();
    window.addEventListener("pointerdown", unlock, { once: true });
    window.addEventListener("keydown", unlock, { once: true });
    return () => {
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    };
  }, []);

  useEffect(() => {
    let after: number | null = null; // null: first poll, only learn the latest ID
    let cancelled = false;

    const tick = async () => {
      try {
        const poll = await api.pollMonitor(after);
        if (cancelled) return;
        queryClient.setQueryData(queryKeys.monitor, poll.monitor);
        if (after !== null && poll.events.length > 0) {
          const newest = poll.events[poll.events.length - 1];
          setBanner(poll.events.reduce((total, event) => total + event.count, 0));
          if (poll.events.some((event) => event.play_in_browser) && claimChime(newest.id)) {
            playChime();
          }
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

/** True if this tab should chime for alert `id` (no other tab has yet). */
function claimChime(id: number): boolean {
  try {
    if (Number(window.localStorage.getItem(CHIMED_KEY) ?? 0) >= id) return false;
    window.localStorage.setItem(CHIMED_KEY, String(id));
    return true;
  } catch {
    return true; // storage unavailable: chime anyway
  }
}