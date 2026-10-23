import { ButtonLink } from "../components/Button";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import styles from "./HomePage.module.css";

/** The site logo, served from frontend/public/. */
const LOGO_SRC = `${import.meta.env.BASE_URL}favicon-nobg.png`;

/** The logo and name, a link explaining the platform, and the way in. */
export function HomePage() {
  useDocumentTitle();

  return (
    <main className={`${styles.home} page-enter`}>
      <div className={styles.inner}>
        <h1 className={styles.title}>
          {/* Decorative: the heading text already says "Job Sentry". */}
          <img className={styles.logo} src={LOGO_SRC} alt="" decoding="async" />
          <span>Job Sentry</span>
        </h1>
        <ButtonLink to="/why">Why Job Sentry?</ButtonLink>
        <ButtonLink to="/sources" size="large">
          Be the first to apply
        </ButtonLink>
      </div>
    </main>
  );
}