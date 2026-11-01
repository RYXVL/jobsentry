import { Link, Outlet, useLocation } from "react-router-dom";

import styles from "./Layout.module.css";
import { SiteFooter } from "./SiteFooter";

/** Shared frame for every page except the homepage: header, the page, footer. */
export function Layout() {
  const { pathname } = useLocation();

  return (
    <div className={`${styles.page} page-enter`}>
      <header className={styles.header}>
        <Link to="/" className={styles.home}>
          Job Sentry
        </Link>
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