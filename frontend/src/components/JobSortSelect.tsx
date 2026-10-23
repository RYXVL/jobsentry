import { useId } from "react";

import type { JobSort } from "../api/types";
import styles from "./JobSortSelect.module.css";

/** Choices in display order. To add an order, add it here and to JobSort. */
const OPTIONS: { value: JobSort; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
];

interface JobSortSelectProps {
  value: JobSort;
  onChange: (sort: JobSort) => void;
}

/** "Sort by date posted: Newest first / Oldest first", right-aligned above a job list. */
export function JobSortSelect({ value, onChange }: JobSortSelectProps) {
  const id = useId();
  return (
    <div className={styles.sort}>
      <label htmlFor={id} className={styles.label}>
        Sort by date posted
      </label>
      <select
        id={id}
        className={styles.select}
        value={value}
        onChange={(event) => onChange(event.target.value as JobSort)}
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}