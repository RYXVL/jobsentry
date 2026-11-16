import { Link, Outlet, useLocation } from "react-router-dom";

import { useMonitor } from "../api/queries";
import { Countdown } from "./Countdown";
import styles from "./Layout.module.css";
import { SiteFooter } from "./SiteFooter";

/** Shared frame for every page except the homepage: header, the page, footer.
 *  While the monitor is on, the header shows a live countdown to the next
 *  fetch and links to the Monitor page. */
export function Layout() {
  const { pathname } = useLocation();
  const monitor = useMonitor().data;

  return (
    <div className={`${styles.page} page-enter`}>
      <header className={styles.header}>
        <Link to="/" className={styles.home}>
          Job Sentry
        </Link>
        {monitor?.active && (
          <Link to="/monitor" className={styles.monitoring}>
            Monitoring ·{" "}
            {monitor.fetching ? (
              "fetching now"
            ) : monitor.next_fetch_at ? (
              <>
                next fetch in{" "}
                <span className={styles.countdown}>
                  <Countdown to={monitor.next_fetch_at} />
                </span>
              </>
            ) : (
              "on"
            )}
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