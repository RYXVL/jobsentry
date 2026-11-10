import { useState } from "react";

import { getLogoVersion } from "../utils/logoVersion";
import styles from "./SourceLogo.module.css";

/**
 * Image types tried in order. Logos live in frontend/public/logos/ and are
 * named after the source's `name` (not its company name), e.g. stripe.png.
 * Logos uploaded from "Manage sources" are saved there as <name>.png.
 */
const LOGO_EXTENSIONS = ["png", "jpg"] as const;

interface SourceLogoProps {
  /** The source's registry name; used for the file name. */
  name: string;
  /** The company's display name; used for the initials fallback. */
  company: string;
  /** "regular": as on source cards. "small": e.g. inside the company chip on job cards. */
  size?: "regular" | "small";
}

/**
 * A company's logo from frontend/public/logos/, or its initials when no
 * image is found. Each extension is tried in turn; when the last one fails
 * to load, the initials are shown instead. After a logo changes (see
 * utils/logoVersion.ts), it starts over and asks for the new file.
 *
 * Decorative only: the company name is always shown next to it, so the
 * image has empty alt text and the initials are hidden from screen readers.
 */
export function SourceLogo({ name, company, size = "regular" }: SourceLogoProps) {
  const version = getLogoVersion();
  const [state, setState] = useState({ version, attempt: 0 });
  const attempt = state.version === version ? state.attempt : 0;
  const extension = LOGO_EXTENSIONS[attempt];
  const sizeClass = size === "small" ? styles.small : "";

  if (extension === undefined) {
    return (
      <span className={`${styles.logo} ${styles.initials} ${sizeClass}`} aria-hidden="true">
        {initials(company)}
      </span>
    );
  }

  const cacheBuster = version > 0 ? `?v=${version}` : "";
  return (
    <img
      key={`${extension}-${version}`}
      className={`${styles.logo} ${sizeClass}`}
      src={`${import.meta.env.BASE_URL}logos/${encodeURIComponent(name)}.${extension}${cacheBuster}`}
      alt=""
      decoding="async"
      onError={() => setState({ version, attempt: attempt + 1 })}
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