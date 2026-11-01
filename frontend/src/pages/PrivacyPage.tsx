import { Link } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { ISSUES_URL, LEGAL_UPDATED } from "../config/site";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatDate } from "../utils/format";
import styles from "./Legal.module.css";

/** /privacy: what Job Sentry stores and who it contacts. */
export function PrivacyPage() {
  useDocumentTitle("Privacy");

  return (
    <>
      <PageHeader title="Privacy" intro="Short version: everything stays on your own computer." />

      <div className={styles.sections}>
        <section className={styles.section}>
          <h2 className={styles.heading}>Who runs Job Sentry</h2>
          <p>
            Job Sentry is open-source software that you download and run on your own computer.
            Its authors don't operate a server for it, and never receive any information about
            you or how you use it.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>What it stores</h2>
          <p>
            The job listings it fetches are saved as files on your computer (in{" "}
            <code>backend/data/</code> by default). Filters and page numbers live in the page
            address. That's all. There are no accounts, cookies, analytics or tracking, and
            fonts and logos are bundled with the app.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>Who it contacts</h2>
          <p>
            Only when you fetch or refresh jobs, your computer requests listings directly from
            the public job board services companies use: Greenhouse, Ashby and Lever. Like any
            website you visit, those services receive your IP address and the browser
            identification (User-Agent) set in Job Sentry's settings, and their own privacy
            policies apply.
          </p>
          <ul>
            <li>Browsing jobs you've already fetched contacts no one.</li>
            <li>
              Opening a job takes you to the company's own posting, where that company's
              privacy policy applies.
            </li>
          </ul>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>Deleting your data</h2>
          <p>
            Use "Clear saved jobs" on the <Link to="/sources">sources page</Link>, or delete the
            data folder. Uninstalling Job Sentry removes everything it stored.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>Changes and questions</h2>
          <p>
            This policy ships with the software, so any change appears in the repository.
            Questions are welcome as{" "}
            <a href={ISSUES_URL} target="_blank" rel="noreferrer">
              an issue on GitHub
            </a>
            .
          </p>
        </section>
      </div>

      <p className={styles.updated}>Last updated {formatDate(`${LEGAL_UPDATED}T12:00:00`)}.</p>
    </>
  );
}