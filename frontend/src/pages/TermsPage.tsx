import { PageHeader } from "../components/PageHeader";
import { ISSUES_URL, LEGAL_UPDATED } from "../config/site";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatDate } from "../utils/format";
import styles from "./Legal.module.css";

/** /terms: the terms of use for running Job Sentry. */
export function TermsPage() {
  useDocumentTitle("Terms of use");

  return (
    <>
      <PageHeader
        title="Terms of use"
        intro="By running or using Job Sentry, you agree to these terms. If you don't, please don't use it."
      />

      <div className={styles.sections}>
        <section className={styles.section}>
          <h2 className={styles.heading}>The software and its licence</h2>
          <p>
            Job Sentry is free, open-source software. Using, copying, changing and sharing it is
            governed by the licence in the repository's <code>LICENSE</code> file. Where these
            terms and the licence differ, the licence decides.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>Intended use</h2>
          <p>
            Job Sentry is for personal job searching: keeping an eye on companies' open roles
            so you can apply early. It isn't intended for commercial use, such as reselling
            listings or running a job board.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>Your responsibilities</h2>
          <p>
            You run Job Sentry on your own computer, and every request it makes comes from
            there. You're responsible for using it lawfully and in line with the terms of the
            services it contacts. In particular:
          </p>
          <ul>
            <li>Keep refreshes reasonable rather than fetching constantly.</li>
            <li>
              Add only companies whose jobs are published through a public job board API, and
              respect any site that refuses automated access.
            </li>
            <li>Don't use it to collect listings for resale or redistribution.</li>
          </ul>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>Job listings</h2>
          <p>
            Listings belong to the companies that posted them. Job Sentry shows copies fetched
            at a point in time, so they may be incomplete, out of date or no longer open. Some
            details, such as countries and work mode, are worked out from the listing's text
            and may be wrong. Always check the original posting before applying. Job Sentry
            doesn't handle applications.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>No affiliation</h2>
          <p>
            Job Sentry isn't affiliated with, endorsed by or sponsored by any company it lists,
            or by Greenhouse, Ashby or Lever. Company names and logos belong to their owners and
            are shown only to identify where a listing comes from.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>No warranty</h2>
          <p>
            Job Sentry is provided "as is", without warranty of any kind. To the extent the law
            allows, its authors aren't liable for any loss arising from its use, including
            missed, outdated or inaccurate listings.
          </p>
        </section>

        <section className={styles.section}>
          <h2 className={styles.heading}>Changes and questions</h2>
          <p>
            These terms ship with the software, so any change appears in the repository.
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