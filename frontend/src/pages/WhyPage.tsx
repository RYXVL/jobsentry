import { ButtonLink } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import styles from "./WhyPage.module.css";

const REASONS = [
  {
    title: "Straight from the source",
    text: "Job Sentry reads companies' own public job boards, so you see roles as the company lists them, without waiting for job sites to copy them over.",
  },
  {
    title: "Every company in one list",
    text: "Instead of checking careers pages one by one, see every job posted today across all of them, newest first, with keyword and country filters.",
  },
  {
    title: "Alerted the moment it matters",
    text: "Turn on the monitor and Job Sentry checks every company on a schedule, then plays a sound or emails you when a new matching job appears.",
  },
  {
    title: "Free, with nothing to sign up for",
    text: "No account and no ads. It runs on your own computer, and your data stays there.",
  },
];

/** /why: what Job Sentry is for. */
export function WhyPage() {
  useDocumentTitle("Why Job Sentry?");

  return (
    <>
      <PageHeader title="Why Job Sentry?" intro="New jobs from companies' own job boards, the moment they're posted." />
      <ul className={styles.reasons}>
        {REASONS.map((reason) => (
          <li key={reason.title}>
            <h2 className={styles.reasonTitle}>{reason.title}</h2>
            <p className={styles.reasonText}>{reason.text}</p>
          </li>
        ))}
      </ul>
      <div className={styles.cta}>
        <ButtonLink to="/command-center" size="large">
          Be the first to apply
        </ButtonLink>
      </div>
    </>
  );
}