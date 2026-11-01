import { ButtonLink } from "../components/Button";
import { SiteFooter } from "../components/SiteFooter";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import styles from "./HomePage.module.css";

/** The site logo, served from frontend/public/. */
const LOGO_SRC = `${import.meta.env.BASE_URL}favicon-nobg.png`;

/** The logo and name, a link explaining the platform, the way in, and the
 *  footer at the bottom of the screen. */
export function HomePage() {
  useDocumentTitle();

  return (
    <div className={`${styles.home} page-enter`}>
      <main className={styles.inner}>
        <h1 className={styles.title}>
          {/* Decorative: the heading text already says "Job Sentry". */}
          <img className={styles.logo} src={LOGO_SRC} alt="" decoding="async" />
          <span>Job Sentry</span>
        </h1>
        <ButtonLink to="/why">Why Job Sentry?</ButtonLink>
        <ButtonLink to="/sources" size="large">
          Be the first to apply
        </ButtonLink>
      </main>
      <div className={styles.footer}>
        <SiteFooter />
      </div>
    </div>
  );
}