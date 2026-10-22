import type { ReactNode } from "react";

import { API_UNREACHABLE, ApiError } from "../api/client";
import { Button } from "./Button";
import styles from "./StatusMessage.module.css";

/** Loading and empty states. Announced politely to screen readers. */
export function StatusMessage({ children }: { children: ReactNode }) {
  return (
    <p className={styles.status} role="status">
      {children}
    </p>
  );
}

/** What to tell the user for each error code, beyond the API's own message. */
function hintFor(error: unknown): ReactNode {
  if (!(error instanceof ApiError)) return null;
  switch (error.code) {
    case API_UNREACHABLE:
      return (
        <>
          Start it from the backend folder with <code>python -m jobsentry.api</code>, then try
          again.
        </>
      );
    case "source_blocked":
      return "This site refuses automated access, so jobsentry won't fetch from it.";
    case "source_error":
      return "The career site failed or changed its layout. Try again later.";
    case "refresh_in_progress":
      return "Wait for the current refresh to finish.";
    default:
      return null;
  }
}

interface ErrorNoticeProps {
  error: unknown;
  /** Shows a "Try again" button when given. */
  onRetry?: () => void;
}

export function ErrorNotice({ error, onRetry }: ErrorNoticeProps) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  const hint = hintFor(error);
  return (
    <div className={styles.error} role="alert">
      <p className={styles.errorTitle}>{message}</p>
      {hint && <p className={styles.hint}>{hint}</p>}
      {onRetry && (
        <Button className={styles.retry} onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
