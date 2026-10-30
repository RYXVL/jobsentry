import type { FacetValue, JobSort } from "../api/types";
import type { JobFilterValues } from "../utils/jobFilters";
import { filtersKey } from "../utils/jobListView";
import { JobFilters } from "./JobFilters";
import styles from "./JobListToolbar.module.css";
import { JobSortSelect } from "./JobSortSelect";

interface JobListToolbarProps {
  /** The filters currently applied (from the URL). */
  filters: JobFilterValues;
  /** Countries to offer in the picker, with job counts. */
  countryOptions: FacetValue[];
  /** True while the country options are still loading. */
  countriesLoading?: boolean;
  sort: JobSort;
  onApplyFilters: (filters: JobFilters) => void;
  onChangeSort: (sort: JobSort) => void;
}

type JobFilters = JobFilterValues;

/** Filters on the left and sort on the right, above a job list. */
export function JobListToolbar({
  filters,
  countryOptions,
  countriesLoading,
  sort,
  onApplyFilters,
  onChangeSort,
}: JobListToolbarProps) {
  return (
    <div className={styles.toolbar}>
      <div className={styles.filters}>
        <JobFilters
          // Remount when the applied filters change (e.g. Back), so the form matches the URL.
          key={filtersKey(filters)}
          applied={filters}
          countryOptions={countryOptions}
          countriesLoading={countriesLoading}
          onApply={onApplyFilters}
        />
      </div>
      <JobSortSelect value={sort} onChange={onChangeSort} />
    </div>
  );
}