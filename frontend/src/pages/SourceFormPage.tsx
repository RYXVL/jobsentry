import { useEffect, useId, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useCatalog, useCatalogEntry, useCheckBoards, useSaveSource } from "../api/queries";
import type { CatalogEntry, CheckResult, LeverRegion, Platform } from "../api/types";
import { BoardCheck } from "../components/BoardCheck";
import { Button } from "../components/Button";
import fieldStyles from "../components/Field.module.css";
import { PageHeader } from "../components/PageHeader";
import { SourceLogo } from "../components/SourceLogo";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import styles from "./SourceFormPage.module.css";

/** The backend's limit for logos (2 MB). */
const LOGO_MAX_BYTES = 2_000_000;

/** /manage/new and /manage/:name: add or edit a source. */
export function SourceFormPage() {
  const { name } = useParams();
  const editing = name !== undefined;
  useDocumentTitle(editing ? "Edit source" : "Add source");
  const catalog = useCatalog();
  const entry = useCatalogEntry(name ?? "", { enabled: editing });

  const header = (
    <PageHeader
      back={{ to: "/manage", label: "Manage sources" }}
      title={editing ? `Edit ${entry.data?.company ?? name}` : "Add source"}
    />
  );

  if (catalog.isPending || (editing && entry.isPending)) {
    return <>{header}<StatusMessage>Loading…</StatusMessage></>;
  }
  if (catalog.isError) return <>{header}<ErrorNotice error={catalog.error} onRetry={() => catalog.refetch()} /></>;
  if (editing && entry.isError) return <>{header}<ErrorNotice error={entry.error} /></>;

  return (
    <>
      {header}
      {/* Keyed by source, so switching sources starts a fresh form. */}
      <SourceForm key={name ?? "@new"} platforms={catalog.data.platforms} initial={entry.data} />
    </>
  );
}

interface SourceFormProps {
  platforms: Platform[];
  /** The entry being edited; absent when adding. */
  initial?: CatalogEntry;
}

/**
 * The add/edit form. Save is enabled only after "Check" has passed for
 * exactly the current platform, board names and region, so changing any of
 * them requires checking again.
 */
function SourceForm({ platforms, initial }: SourceFormProps) {
  const navigate = useNavigate();
  const ids = { platform: useId(), company: useId(), name: useId(), boards: useId(), homepage: useId(), region: useId(), logo: useId() };
  const editing = initial !== undefined;

  const [platformKey, setPlatformKey] = useState(initial?.platform ?? platforms[0]?.key ?? "");
  const [company, setCompany] = useState(initial?.company ?? "");
  const [name, setName] = useState(initial?.name ?? "");
  const [nameTouched, setNameTouched] = useState(editing);
  const [boards, setBoards] = useState(initial?.board_names.join(", ") ?? "");
  const [homepage, setHomepage] = useState(initial?.homepage ?? "");
  const [region, setRegion] = useState<LeverRegion>(initial?.region ?? "global");
  const [logo, setLogo] = useState<File | null>(null);
  const [logoError, setLogoError] = useState<string | null>(null);
  const [removeLogo, setRemoveLogo] = useState(false);
  const [lastCheck, setLastCheck] = useState<{ key: string; result: CheckResult } | null>(null);

  const check = useCheckBoards();
  const save = useSaveSource();

  const platform = platforms.find((p) => p.key === platformKey);
  const boardNames = useMemo(
    () => boards.split(",").map((board) => board.trim()).filter(Boolean),
    [boards],
  );
  const checkRegion = platform?.has_region ? region : null;
  // What a check is for: if any of these change, the check no longer counts.
  const checkKey = JSON.stringify({ platformKey, boardNames, checkRegion });
  const currentCheck = lastCheck?.key === checkKey ? lastCheck.result : null;
  const canSave =
    currentCheck?.ok === true && company.trim() !== "" && name.trim() !== "" && !logoError;

  // A preview of the chosen logo, released when it changes.
  const preview = useMemo(() => (logo ? URL.createObjectURL(logo) : null), [logo]);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const changeCompany = (value: string) => {
    setCompany(value);
    if (!nameTouched) setName(slugify(value));
  };

  const runCheck = () => {
    const key = checkKey;
    check.mutate(
      { platform: platformKey, board_names: boardNames, region: checkRegion },
      { onSuccess: (result) => setLastCheck({ key, result }) },
    );
  };

  const chooseLogo = (file: File | null) => {
    setLogoError(null);
    if (file && file.type !== "image/png") setLogoError("The logo must be a PNG image.");
    else if (file && file.size > LOGO_MAX_BYTES) setLogoError("The logo must be at most 2 MB.");
    setLogo(file);
    if (file) setRemoveLogo(false);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!canSave) return;
    save.mutate(
      {
        editing: initial?.name,
        input: {
          platform: platformKey,
          name: name.trim(),
          company: company.trim(),
          board_names: boardNames,
          homepage: homepage.trim() || null,
          region: checkRegion,
        },
        logo,
        removeLogo,
      },
      { onSuccess: () => navigate("/manage") },
    );
  };

  const logoName = name.trim() || "<name>";

  return (
    <form className={styles.form} onSubmit={submit}>
      <div className={fieldStyles.field}>
        <label htmlFor={ids.platform} className={fieldStyles.label}>Platform</label>
        <select
          id={ids.platform}
          className={`${fieldStyles.control} ${fieldStyles.dropdown}`}
          value={platformKey}
          onChange={(event) => setPlatformKey(event.target.value)}
        >
          {platforms.map((p) => (
            <option key={p.key} value={p.key}>{p.label}</option>
          ))}
        </select>
      </div>

      <div className={fieldStyles.field}>
        <label htmlFor={ids.company} className={fieldStyles.label}>Company</label>
        <input
          id={ids.company}
          className={fieldStyles.control}
          value={company}
          onChange={(event) => changeCompany(event.target.value)}
          placeholder="e.g. Hudson River Trading"
          required
        />
      </div>

      <div className={fieldStyles.field}>
        <label htmlFor={ids.name} className={fieldStyles.label}>Name</label>
        <input
          id={ids.name}
          className={fieldStyles.control}
          value={name}
          onChange={(event) => { setName(event.target.value); setNameTouched(true); }}
          placeholder="e.g. hudson-river-trading"
          readOnly={editing}
          aria-describedby={`${ids.name}-hint`}
          required
        />
        <p id={`${ids.name}-hint`} className={styles.hint}>
          {editing
            ? "A name can't change. To rename, delete the source and add it again."
            : "Lowercase letters, digits, - or _. Used in URLs, data/<name>/ and the logo's file name. It can't be changed later."}
        </p>
      </div>

      <div className={fieldStyles.field}>
        <label htmlFor={ids.boards} className={fieldStyles.label}>Board name</label>
        <input
          id={ids.boards}
          className={fieldStyles.control}
          value={boards}
          onChange={(event) => setBoards(event.target.value)}
          placeholder="e.g. wehrtyou"
          aria-describedby={`${ids.boards}-hint`}
          required
        />
        <p id={`${ids.boards}-hint`} className={styles.hint}>
          The last part of the company's board URL. Separate several with commas.
          {platformKey === "smartrecruiters" && " SmartRecruiters names are case-sensitive."}
        </p>
      </div>

      {platform?.has_region && (
        <div className={fieldStyles.field}>
          <label htmlFor={ids.region} className={fieldStyles.label}>Region</label>
          <select
            id={ids.region}
            className={`${fieldStyles.control} ${fieldStyles.dropdown}`}
            value={region}
            onChange={(event) => setRegion(event.target.value as LeverRegion)}
          >
            <option value="global">Global (jobs.lever.co)</option>
            <option value="eu">EU (jobs.eu.lever.co)</option>
          </select>
        </div>
      )}

      <div className={fieldStyles.field}>
        <label htmlFor={ids.homepage} className={fieldStyles.label}>Careers page (optional)</label>
        <input
          id={ids.homepage}
          type="url"
          className={fieldStyles.control}
          value={homepage}
          onChange={(event) => setHomepage(event.target.value)}
          placeholder="https://…"
        />
      </div>

      <div className={fieldStyles.field}>
        <label htmlFor={ids.logo} className={fieldStyles.label}>Logo (optional)</label>
        <div className={styles.logoRow}>
          {preview ? (
            <img src={preview} alt="" className={styles.preview} />
          ) : editing && !removeLogo ? (
            <SourceLogo name={initial.name} company={company || initial.company} />
          ) : null}
          <input
            id={ids.logo}
            type="file"
            accept="image/png"
            onChange={(event) => chooseLogo(event.target.files?.[0] ?? null)}
            aria-describedby={`${ids.logo}-hint`}
          />
          {editing && !logo && (
            <Button onClick={() => setRemoveLogo((value) => !value)}>
              {removeLogo ? "Keep logo" : "Remove logo"}
            </Button>
          )}
        </div>
        <p id={`${ids.logo}-hint`} className={styles.hint}>
          PNG, up to 2 MB, ideally with a transparent background. Saved as{" "}
          <code>frontend/public/logos/{logoName}.png</code>, which is how the cards find it.
        </p>
        {logoError && <p className={styles.error}>{logoError}</p>}
      </div>

      {editing && initial.extra_keys.length > 0 && (
        <p className={styles.hint}>
          Kept as they are: {initial.extra_keys.join(", ")}. Edit these in the catalog file.
        </p>
      )}

      <div className={styles.check}>
        <Button busy={check.isPending} disabled={boardNames.length === 0} onClick={runCheck}>
          {check.isPending ? "Checking…" : "Check"}
        </Button>
        {check.isError && <ErrorNotice error={check.error} />}
        {currentCheck && <BoardCheck result={currentCheck} />}
        {lastCheck && !currentCheck && (
          <p className={styles.hint}>The platform, board names or region changed. Check again.</p>
        )}
      </div>

      {save.isError && <ErrorNotice error={save.error} />}

      <div className={styles.actions}>
        <Button type="submit" size="large" busy={save.isPending} disabled={!canSave}>
          {save.isPending ? "Saving…" : editing ? "Save changes" : "Add source"}
        </Button>
        {!currentCheck?.ok && <p className={styles.hint}>Check the board names to enable saving.</p>}
      </div>
    </form>
  );
}

/** "Hudson River Trading" becomes "hudson-river-trading". */
function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}