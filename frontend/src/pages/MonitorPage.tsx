import { useId, useState, type FormEvent } from "react";

import {
  useConfirmEmail,
  useMonitor,
  useRefreshRun,
  useSaveMonitorSettings,
  useSendTestEmail,
  useStartMonitor,
  useStopMonitor,
  useTestSound,
} from "../api/queries";
import type { MonitorSettings, MonitorStatus, MonitorUnit } from "../api/types";
import { Button } from "../components/Button";
import fieldStyles from "../components/Field.module.css";
import { PageHeader } from "../components/PageHeader";
import { RefreshProgress } from "../components/RefreshProgress";
import { ErrorNotice, StatusMessage } from "../components/StatusMessage";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { formatRelativeTime } from "../utils/format";
import styles from "./MonitorPage.module.css";

const MINUTE_CHOICES = [15, 30, 45];
const HOUR_CHOICES = Array.from({ length: 24 }, (_, index) => index + 1);

/** /monitor: fetch every company on a schedule and alert about new jobs,
 *  with the current fetch's progress at the top, as on the sources page. */
export function MonitorPage() {
  useDocumentTitle("Monitor");
  const monitor = useMonitor();
  const run = useRefreshRun();

  return (
    <>
      <PageHeader
        back={{ to: "/command-center", label: "Command center" }}
        title="Monitor"
        intro="Fetch every company on a schedule, and get a sound or an email when new jobs are posted."
      />
      {run.data && <RefreshProgress run={run.data} />}
      {monitor.isPending ? (
        <StatusMessage>Loading…</StatusMessage>
      ) : monitor.isError ? (
        <ErrorNotice error={monitor.error} onRetry={() => monitor.refetch()} />
      ) : (
        <MonitorForm status={monitor.data} />
      )}
    </>
  );
}

function MonitorForm({ status }: { status: MonitorStatus }) {
  const ids = { every: useId(), unit: useId(), keywords: useId(), email: useId() };
  const [form, setForm] = useState<MonitorSettings>(status.settings);
  const [testSentTo, setTestSentTo] = useState<string | null>(null);
  const [notReceived, setNotReceived] = useState(false);

  const save = useSaveMonitorSettings();
  const start = useStartMonitor();
  const stop = useStopMonitor();
  const testSound = useTestSound();
  const sendTest = useSendTestEmail();
  const confirm = useConfirmEmail();

  const update = (changes: Partial<MonitorSettings>) => setForm((current) => ({ ...current, ...changes }));
  const changed = JSON.stringify(form) !== JSON.stringify(status.settings);
  const emailTo = form.email_to.trim();
  const emailVerified = status.email_verified && status.settings.email_to === emailTo;

  const changeUnit = (unit: MonitorUnit) => update({ unit, every: unit === "minutes" ? 15 : 1 });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    save.mutate(form);
  };

  const testEmail = () => {
    setNotReceived(false);
    confirm.reset();
    sendTest.mutate(emailTo, { onSuccess: () => setTestSentTo(emailTo) });
  };

  const answer = (received: boolean) =>
    confirm.mutate(
      { emailTo: testSentTo ?? emailTo, received },
      {
        onSuccess: (next) => {
          setTestSentTo(null);
          setNotReceived(!received);
          if (received) update({ email_to: next.settings.email_to });
        },
      },
    );

  return (
    <div className={styles.page}>
      <section className={styles.status} aria-label="Monitor status">
        <p className={styles.state}>
          {status.active ? "Monitoring is on" : "Monitoring is off"}
          {status.active && status.fetching && ": fetching now"}
        </p>
        {status.active && status.next_fetch_at && !status.fetching && (
          <p className={styles.hint}>Next fetch {formatRelativeTime(status.next_fetch_at)}.</p>
        )}
        {status.last_fetch_started_at && (
          <p className={styles.hint}>
            Last fetch of every company started {formatRelativeTime(status.last_fetch_started_at)}.
          </p>
        )}
        {status.last_email && (
          <p className={status.last_email.ok ? styles.hint : styles.error}>
            Last alert email {formatRelativeTime(status.last_email.at)}:{" "}
            {status.last_email.ok ? "sent" : status.last_email.error}
          </p>
        )}
        <div className={styles.row}>
          {status.active ? (
            <Button size="large" busy={stop.isPending} onClick={() => stop.mutate()}>
              {stop.isPending ? "Stopping…" : "Stop monitoring"}
            </Button>
          ) : (
            <Button size="large" busy={start.isPending} onClick={() => start.mutate(form)}>
              {start.isPending ? "Starting…" : "Start monitoring"}
            </Button>
          )}
        </div>
        {start.isError && <ErrorNotice error={start.error} />}
        {stop.isError && <ErrorNotice error={stop.error} />}
      </section>

      <p className={styles.rule}>
        You're alerted only about jobs <strong>posted today</strong>, after the{" "}
        <strong>previous fetch</strong> started, that match the filter below. The first fetch after
        you start includes everything matching posted so far today. Any fetch of every company
        counts, including "Fetch all jobs" on the sources page.
      </p>

      <form className={styles.form} onSubmit={submit}>
        <fieldset className={styles.group}>
          <legend className={styles.legend}>Fetch every</legend>
          <div className={styles.row}>
            <label htmlFor={ids.every} className="visually-hidden">Interval</label>
            <select
              id={ids.every}
              className={`${fieldStyles.control} ${fieldStyles.dropdown}`}
              value={form.every}
              onChange={(event) => update({ every: Number(event.target.value) })}
            >
              {(form.unit === "minutes" ? MINUTE_CHOICES : HOUR_CHOICES).map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </select>
            <label htmlFor={ids.unit} className="visually-hidden">Unit</label>
            <select
              id={ids.unit}
              className={`${fieldStyles.control} ${fieldStyles.dropdown}`}
              value={form.unit}
              onChange={(event) => changeUnit(event.target.value as MonitorUnit)}
            >
              <option value="minutes">minutes</option>
              <option value="hours">hours</option>
            </select>
          </div>
        </fieldset>

        <div className={fieldStyles.field}>
          <label htmlFor={ids.keywords} className={fieldStyles.label}>Keywords</label>
          <input
            id={ids.keywords}
            type="search"
            className={fieldStyles.control}
            value={form.keywords}
            onChange={(event) => update({ keywords: event.target.value })}
            placeholder="e.g. software engineer"
          />
          <p className={styles.hint}>
            The same filter as Today's jobs: every word must appear in the job's title or team
            name. Leave it empty to be alerted about every new job.
          </p>
        </div>

        <fieldset className={styles.group}>
          <legend className={styles.legend}>Alert me with</legend>

          <label className={styles.check}>
            <input type="checkbox" checked={form.sound} onChange={(event) => update({ sound: event.target.checked })} />
            A sound
          </label>
          <div className={styles.row}>
            <Button busy={testSound.isPending} onClick={() => testSound.mutate()}>
              Test sound
            </Button>
          </div>
          {testSound.data && <p className={styles.hint}>{testSound.data.message}</p>}
          {testSound.isError && <ErrorNotice error={testSound.error} />}
          <p className={styles.hint}>
            This computer plays the chime the moment a fetch finds new jobs, whether or not
            Job Sentry is open in a browser.
          </p>

          <label className={styles.check}>
            <input
              type="checkbox"
              checked={form.email && emailVerified}
              disabled={!emailVerified}
              onChange={(event) => update({ email: event.target.checked })}
            />
            An email
          </label>
          {!status.email_configured ? (
            <p className={styles.hint}>
              Email isn't set up. Add <code>JOBSENTRY_SMTP_HOST</code>, <code>JOBSENTRY_SMTP_FROM</code>{" "}
              (and usually <code>JOBSENTRY_SMTP_USERNAME</code> and <code>JOBSENTRY_SMTP_PASSWORD</code>)
              to <code>backend/.env</code>, then restart the API.
            </p>
          ) : (
            <>
              <div className={fieldStyles.field}>
                <label htmlFor={ids.email} className={fieldStyles.label}>Send alerts to</label>
                <input
                  id={ids.email}
                  type="email"
                  className={fieldStyles.control}
                  value={form.email_to}
                  onChange={(event) => { update({ email_to: event.target.value, email: false }); setTestSentTo(null); }}
                  placeholder="you@example.com"
                />
              </div>
              <p className={styles.hint}>
                {emailVerified
                  ? "Verified: test emails to this address arrive."
                  : "Verify this address before turning email on: send a test email and confirm you received it."}
              </p>
              <div className={styles.row}>
                <Button busy={sendTest.isPending} disabled={!emailTo.includes("@")} onClick={testEmail}>
                  {sendTest.isPending ? "Sending…" : "Send test email"}
                </Button>
              </div>
              {sendTest.isError && <ErrorNotice error={sendTest.error} />}
              {testSentTo && sendTest.data && (
                <div className={styles.confirm}>
                  <p>{sendTest.data.message} Did you receive it?</p>
                  <div className={styles.row}>
                    <Button busy={confirm.isPending} onClick={() => answer(true)}>Yes, I got it</Button>
                    <Button disabled={confirm.isPending} onClick={() => answer(false)}>No</Button>
                  </div>
                </div>
              )}
              {confirm.isError && <ErrorNotice error={confirm.error} />}
              {notReceived && (
                <p className={styles.hint}>
                  Check your spam folder, that <code>JOBSENTRY_SMTP_FROM</code> is an address your mail
                  server lets you send from, and (for Gmail or Outlook) that the password is an app
                  password. Then send another test.
                </p>
              )}
            </>
          )}
        </fieldset>

        {save.isError && <ErrorNotice error={save.error} />}
        <div className={styles.row}>
          <Button type="submit" busy={save.isPending} disabled={!changed}>
            {save.isPending ? "Saving…" : "Save settings"}
          </Button>
          {changed && <p className={styles.hint}>Unsaved changes. Start also saves them.</p>}
        </div>
      </form>
    </div>
  );
}