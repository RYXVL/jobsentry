import { useId, useState, type FormEvent } from "react";

import type { FacetValue } from "../api/types";
import {
  EMPTY_FILTERS,
  hasFilters,
  normalizeFilters,
  sameFilters,
  type JobFilterValues,
} from "../utils/jobFilters";
import { Button } from "./Button";
import { CountryPicker } from "./CountryPicker";
import fieldStyles from "./Field.module.css";
import styles from "./JobFilters.module.css";

interface JobFiltersProps {
  /** The filters currently applied. The form starts from these; give the
   *  component a new `key` when they change so the form resets to match. */
  applied: JobFilterValues;
  /** Countries in the saved jobs, with counts (from /facets). */
  countryOptions: FacetValue[];
  /** True while the country options are still loading. */
  countriesLoading?: boolean;
  /** Called with normalised filters on "Apply filters" or "Clear filters". */
  onApply: (filters: JobFilterValues) => void;
}

/**
 * Keywords and countries for a job list. Edits stay in a draft until
 * "Apply filters" (or Enter in the keywords box). "Apply filters" is
 * disabled until something has changed; "Clear filters" appears once
 * there is anything to clear.
 */
export function JobFilters({ applied, countryOptions, countriesLoading, onApply }: JobFiltersProps) {
  const [draft, setDraft] = useState<JobFilterValues>(applied);
  const keywordsId = useId();

  const changed = !sameFilters(draft, applied);
  const canClear = hasFilters(applied) || hasFilters(draft);

  const apply = (event: FormEvent) => {
    event.preventDefault();
    if (changed) onApply(normalizeFilters(draft));
  };

  const clear = () => {
    setDraft(EMPTY_FILTERS);
    if (hasFilters(applied)) onApply(EMPTY_FILTERS);
  };

  return (
    <form className={styles.form} onSubmit={apply} role="search" aria-label="Filter jobs">
      <div className={`${fieldStyles.field} ${styles.keywords}`}>
        <label htmlFor={keywordsId} className={fieldStyles.label}>
          Keywords
        </label>
        <input
          id={keywordsId}
          type="search"
          className={fieldStyles.control}
          placeholder="e.g. senior engineer"
          value={draft.keywords}
          onChange={(event) => setDraft((d) => ({ ...d, keywords: event.target.value }))}
        />
      </div>

      <CountryPicker
        options={countryOptions}
        selected={draft.countries}
        loading={countriesLoading}
        onChange={(countries) => setDraft((d) => ({ ...d, countries }))}
      />

      <div className={styles.actions}>
        <Button type="submit" disabled={!changed}>
          Apply filters
        </Button>
        {canClear && <Button onClick={clear}>Clear filters</Button>}
      </div>
    </form>
  );
}