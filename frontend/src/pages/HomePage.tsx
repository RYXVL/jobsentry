import { ButtonLink } from "../components/Button";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import styles from "./HomePage.module.css";

/** The name, a link explaining the platform, and the way in. */
export function HomePage() {
  useDocumentTitle();

  return (
    <main className={`${styles.home} page-enter`}>
      <div className={styles.inner}>
        <h1 className={styles.title}>Job Sentry</h1>
        <ButtonLink to="/why">Why Job Sentry?</ButtonLink>
        <ButtonLink to="/sources" size="large">
          Be the first to apply
        </ButtonLink>
      </div>
    </main>
  );
}