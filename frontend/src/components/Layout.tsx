import { Link, Outlet, useLocation } from "react-router-dom";

import { useMonitor } from "../api/queries";
import { formatRelativeTime } from "../utils/format";
import styles from "./Layout.module.css";
import { SiteFooter } from "./SiteFooter";

/** Shared frame for every page except the homepage: header, the page, footer.
 *  While the monitor is on, the header says so and links to it. */
export function Layout() {
  const { pathname } = useLocation();
  const monitor = useMonitor().data;

  const monitoring = monitor?.active
    ? monitor.fetching
      ? "Monitoring · fetching now"
      : monitor.next_fetch_at
        ? `Monitoring · next fetch ${formatRelativeTime(monitor.next_fetch_at)}`
        : "Monitoring"
    : null;

  return (
    <div className={`${styles.page} page-enter`}>
      <header className={styles.header}>
        <Link to="/" className={styles.home}>
          Job Sentry
        </Link>
        {monitoring && (
          <Link to="/monitor" className={styles.monitoring}>
            {monitoring}
          </Link>
        )}
      </header>
      {/* A new key per URL replays the fade, so only the content transitions
          and the header and footer stay still. */}
      <main key={pathname} className="page-enter">
        <Outlet />
      </main>
      <SiteFooter />
    </div>
  );
}