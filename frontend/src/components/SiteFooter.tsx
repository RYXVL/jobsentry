import { Link } from "react-router-dom";

import { REPO_URL } from "../config/site";
import styles from "./SiteFooter.module.css";

/** Footer on every page: legal links, the repository, and a one-line note
 *  on where listings come from. */
export function SiteFooter() {
  return (
    <footer className={styles.footer}>
      <nav aria-label="Legal and project links">
        <ul className={styles.links}>
          <li>
            <Link to="/privacy">Privacy</Link>
          </li>
          <li>
            <Link to="/terms">Terms</Link>
          </li>
          <li>
            <a href={REPO_URL} target="_blank" rel="noreferrer">
              GitHub<span className="visually-hidden"> (opens in a new tab)</span>
            </a>
          </li>
        </ul>
      </nav>
      <p className={styles.note}>
        Listings come from companies' public job boards. Not affiliated with any company listed.
      </p>
    </footer>
  );
}