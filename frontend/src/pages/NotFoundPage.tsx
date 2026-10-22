import { Link } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export function NotFoundPage() {
  useDocumentTitle("Page not found");
  return (
    <>
      <PageHeader title="Page not found" intro="There's nothing at this address." />
      <Link to="/sources">Go to sources</Link>
    </>
  );
}
