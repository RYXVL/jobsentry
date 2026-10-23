import { useId } from "react";

import type { JobSort } from "../api/types";
import fieldStyles from "./Field.module.css";

/** Choices in display order. To add an order, add it here and to JobSort. */
const OPTIONS: { value: JobSort; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
];

interface JobSortSelectProps {
  value: JobSort;
  onChange: (sort: JobSort) => void;
}

/** "Sort by date posted" dropdown. The parent decides where it sits
 *  (SourceJobsPage puts it at the right of the filter bar). */
export function JobSortSelect({ value, onChange }: JobSortSelectProps) {
  const id = useId();
  return (
    <div className={fieldStyles.field}>
      <label htmlFor={id} className={fieldStyles.label}>
        Sort by date posted
      </label>
      <select
        id={id}
        className={`${fieldStyles.control} ${fieldStyles.dropdown}`}
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