import { ButtonLink } from "../components/Button";
import { PageHeader } from "../components/PageHeader";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import styles from "./WhyPage.module.css";

const REASONS = [
  {
    title: "Straight from the source",
    text: "Job Sentry reads company career sites directly, so you see roles as the company lists them, without waiting for job boards to copy them over.",
  },
  {
    title: "Every company in one list",
    text: "Instead of checking careers pages one by one, browse them all here, with titles, teams and locations side by side.",
  },
  {
    title: "Free, with nothing to sign up for",
    text: "No account and no ads. It runs on your own computer.",
  },
];

/** /why: what Job Sentry is for. */
export function WhyPage() {
  useDocumentTitle("Why Job Sentry?");

  return (
    <>
      <PageHeader title="Why Job Sentry?" intro="Open jobs from company career sites, in one place." />
      <ul className={styles.reasons}>
        {REASONS.map((reason) => (
          <li key={reason.title}>
            <h2 className={styles.reasonTitle}>{reason.title}</h2>
            <p className={styles.reasonText}>{reason.text}</p>
          </li>
        ))}
      </ul>
      <div className={styles.cta}>
        <ButtonLink to="/sources" size="large">
          Be the first to apply
        </ButtonLink>
      </div>
    </>
  );
}