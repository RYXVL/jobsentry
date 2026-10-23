import { useEffect, useMemo, useRef } from "react";

import type { FacetValue } from "../api/types";
import { formatCountry, formatNumber } from "../utils/format";
import styles from "./CountryPicker.module.css";
import fieldStyles from "./Field.module.css";

interface CountryPickerProps {
  /** Countries in the saved jobs (ISO codes) with job counts, from /facets. */
  options: FacetValue[];
  /** Selected ISO codes. */
  selected: string[];
  onChange: (codes: string[]) => void;
  /** True while the options are still loading. */
  loading?: boolean;
}

/**
 * A dropdown of checkboxes for choosing any number of countries, sorted by
 * name, each with its job count. Built on <details>, so it opens and closes
 * from the keyboard; it also closes on Escape or a click outside.
 */
export function CountryPicker({ options, selected, onChange, loading = false }: CountryPickerProps) {
  const detailsRef = useRef<HTMLDetailsElement>(null);

  const countries = useMemo(() => {
    const counts = new Map(options.map((option) => [option.value.toUpperCase(), option.count]));
    // A selected country with no jobs (e.g. from an old link) stays listed so it can be unticked.
    for (const code of selected) if (!counts.has(code)) counts.set(code, 0);
    return [...counts]
      .map(([code, count]) => ({ code, count, name: formatCountry(code) }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [options, selected]);

  useEffect(() => {
    const closeOnOutsideClick = (event: PointerEvent) => {
      const details = detailsRef.current;
      if (details?.open && !details.contains(event.target as Node)) details.open = false;
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      const details = detailsRef.current;
      if (event.key === "Escape" && details?.open) {
        details.open = false;
        details.querySelector("summary")?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);

  const toggle = (code: string, checked: boolean) =>
    onChange(checked ? [...selected, code].sort() : selected.filter((c) => c !== code));

  const summary =
    selected.length === 0
      ? "Any country"
      : selected.length === 1
        ? formatCountry(selected[0])
        : `${selected.length} countries`;

  return (
    <div className={fieldStyles.field}>
      <span className={fieldStyles.label} aria-hidden="true">
        Countries
      </span>
      <details ref={detailsRef} className={styles.picker}>
        <summary
          className={`${fieldStyles.control} ${fieldStyles.dropdown} ${styles.summary}`}
          aria-label={`Countries: ${summary}`}
        >
          {summary}
        </summary>
        <fieldset className={styles.panel}>
          <legend className="visually-hidden">Countries</legend>
          {loading ? (
            <p className={styles.empty}>Loading countries…</p>
          ) : countries.length === 0 ? (
            <p className={styles.empty}>No countries listed for these jobs.</p>
          ) : (
            <ul className={styles.options}>
              {countries.map((country) => (
                <li key={country.code}>
                  <label className={styles.option}>
                    <input
                      type="checkbox"
                      checked={selected.includes(country.code)}
                      onChange={(event) => toggle(country.code, event.target.checked)}
                    />
                    <span className={styles.name}>{country.name}</span>
                    <span className={styles.count}>{formatNumber(country.count)}</span>
                  </label>
                </li>
              ))}
            </ul>
          )}
        </fieldset>
      </details>
    </div>
  );
}