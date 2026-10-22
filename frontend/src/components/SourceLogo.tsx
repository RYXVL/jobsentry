import { useState } from "react";

import styles from "./SourceLogo.module.css";

/**
 * Image types tried in order. Logos live in frontend/public/logos/ and are
 * named after the source's `name` (not its company name), e.g. stripe.png.
 * To support another format, add its extension here.
 */
const LOGO_EXTENSIONS = ["png", "jpg", "jpeg"] as const;

interface SourceLogoProps {
  /** The source's registry name; used for the file name. */
  name: string;
  /** The company's display name; used for the initials fallback. */
  company: string;
}

/**
 * A company's logo from frontend/public/logos/, or its initials when no
 * image is found. Each extension is tried in turn; when the last one fails
 * to load, the initials are shown instead.
 *
 * Decorative only: the company name is always shown next to it, so the
 * image has empty alt text and the initials are hidden from screen readers.
 */
export function SourceLogo({ name, company }: SourceLogoProps) {
  const [attempt, setAttempt] = useState(0);
  const extension = LOGO_EXTENSIONS[attempt];

  if (extension === undefined) {
    return (
      <span className={`${styles.logo} ${styles.initials}`} aria-hidden="true">
        {initials(company)}
      </span>
    );
  }

  return (
    <img
      key={extension}
      className={styles.logo}
      src={`${import.meta.env.BASE_URL}logos/${encodeURIComponent(name)}.${extension}`}
      alt=""
      decoding="async"
      onError={() => setAttempt((current) => current + 1)}
    />
  );
}

/** "Stripe" becomes "S", "Jane Street" becomes "JS". */
function initials(company: string): string {
  const letters = company
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => Array.from(word)[0] ?? "");
  return letters.join("").toUpperCase() || "?";
}