import { Link, Outlet, useLocation } from "react-router-dom";

import styles from "./Layout.module.css";

/** Shared frame for every page except the homepage. */
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
          and the header stays still. */}
      <main key={pathname} className="page-enter">
        <Outlet />
      </main>
    </div>
  );
}