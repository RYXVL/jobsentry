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
            Everything Job Sentry keeps is stored as files on your computer, in the folder you
            run it from:
          </p>
          <ul>
            <li>
              The job listings it fetches, in <code>backend/data/</code> (by default).
            </li>
            <li>
              The monitor's settings, including the email address you choose for alerts, and
              its recent alerts, in <code>backend/data/monitor.json</code>.
            </li>
            <li>
              Logos you upload, in <code>frontend/public/logos/</code>, and the companies you
              add, in the catalog files.
            </li>
            <li>
              Your mail server login, if you set up email alerts, in <code>backend/.env</code>.
              It's only ever sent to your own mail server.
            </li>
          </ul>
          <p>
            Filters and page numbers live in the page address. There are no accounts, cookies,
            analytics or tracking, and fonts are bundled with the app.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>Who it contacts</h2>
          <p>
            When you fetch jobs (with "Fetch all jobs", a company's "Refresh jobs", or the
            monitor's schedule) or check a job board while adding a company, your computer
            requests listings directly from the public job board services companies use:
            Ashby, Greenhouse, Lever and SmartRecruiters. Like any website you visit, those
            services receive your IP address and the browser identification (User-Agent) set in
            Job Sentry's settings, and their own privacy policies apply.
          </p>
          <ul>
            <li>Browsing jobs you've already fetched contacts no one.</li>
            <li>
              Opening a job takes you to the company's own posting, where that company's
              privacy policy applies.
            </li>
            <li>
              If you turn on email alerts, alert and test emails are sent through the mail
              server you set up (for example, your own Gmail account) to the address you
              choose. Your mail provider's privacy policy applies to those emails. Nothing is
              sent to Job Sentry's authors.
            </li>
          </ul>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>Deleting your data</h2>
          <ul>
            <li>
              "Clear saved jobs" on the <Link to="/sources">sources page</Link> deletes every
              saved listing.
            </li>
            <li>
              Deleting a company in <Link to="/manage">Manage sources</Link> removes its entry,
              its saved jobs and its logo.
            </li>
            <li>
              Deleting <code>backend/data/monitor.json</code> resets the monitor, including your
              alert address. Removing the <code>JOBSENTRY_SMTP_</code> lines from{" "}
              <code>backend/.env</code> removes your mail server login.
            </li>
          </ul>
          <p>Deleting the Job Sentry folder removes everything it stored.</p>
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