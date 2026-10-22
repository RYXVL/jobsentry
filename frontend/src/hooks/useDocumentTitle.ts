import { useEffect } from "react";

const SITE = "Job Sentry";

/** Sets the browser tab title, e.g. "Stripe jobs | Job Sentry". */
export function useDocumentTitle(title?: string): void {
  useEffect(() => {
    document.title = title ? `${title} | ${SITE}` : SITE;
  }, [title]);
}