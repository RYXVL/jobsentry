import { Button } from "./Button";
import styles from "./Pagination.module.css";

interface PaginationProps {
  page: number;
  totalPages: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, totalPages, onChange }: PaginationProps) {
  if (totalPages <= 1) return null;
  const isFirst = page <= 1;
  const isLast = page >= totalPages;

  return (
    <nav aria-label="Pages" className={styles.pagination}>
      <Button
        onClick={() => onChange(page - 1)}
        className={isFirst ? styles.placeholder : undefined}
        aria-hidden={isFirst || undefined}
        tabIndex={isFirst ? -1 : undefined}
      >
        Previous page
      </Button>
      <p className={styles.position} aria-current="page">
        Page {page} of {totalPages}
      </p>
      <Button
        onClick={() => onChange(page + 1)}
        className={isLast ? styles.placeholder : undefined}
        aria-hidden={isLast || undefined}
        tabIndex={isLast ? -1 : undefined}
      >
        Next page
      </Button>
    </nav>
  );
}
