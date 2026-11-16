# Job Sentry Backend

Collects job listings from companies' public job board APIs (Greenhouse,
Ashby, Lever and SmartRecruiters) into one common JSON format, and serves
them to the frontend through a local API. It also runs the monitor, which
fetches on a schedule and alerts about new jobs. Run every command from
this folder.

```bash
python -m jobsentry sources                     # list available sources
python -m jobsentry list <source>               # fetch one source's jobs -> data/<source>/jobs.json
python -m jobsentry show <source> <job_id>      # one job -> data/<source>/jobs/<job_id>.json
python -m jobsentry -v list <source>            # same, with progress logs
python -m jobsentry.api                         # start the API on http://127.0.0.1:8000
python scripts/missing_countries.py <source>    # saved locations that match no country
```

`<source>` is a source's `name` from its catalog, e.g. `stripe`, `supabase`, `spotify`, `wise`.

## Structure

```
backend/
├── jobsentry/
│   ├── __main__.py              entry point for `python -m jobsentry`
│   ├── config.py                Settings, loaded from backend/.env
│   ├── core/                    shared building blocks, no business logic
│   │   ├── models.py            Job, JobDetails, JobSnapshot
│   │   ├── countries.py         CountryFinder: country codes from location text
│   │   ├── http.py              HttpClient: headers, timeouts, retries
│   │   └── exceptions.py        JobsentryError and subclasses
│   ├── sources/                 where jobs come from
│   │   ├── base.py              JobSource interface
│   │   ├── registry.py          register(), create_source(), loads (and reloads) the catalogs
│   │   ├── catalogs/            JSON data, read by the loaders
│   │   │   ├── ashby-sources.json             companies on Ashby
│   │   │   ├── greenhouse-sources.json        companies on Greenhouse
│   │   │   ├── lever-sources.json             companies on Lever
│   │   │   ├── smartrecruiters-sources.json   companies on SmartRecruiters
│   │   │   └── country-hints.json             location text -> country, shared by all
│   │   ├── loaders/             read a catalog, register a source per entry
│   │   │   ├── _catalog.py      shared reading and validation helpers
│   │   │   ├── ashby_loader.py
│   │   │   ├── greenhouse_loader.py
│   │   │   ├── lever_loader.py
│   │   │   └── smartrecruiters_loader.py
│   │   └── strategies/          one base class per platform's API
│   │       ├── _helpers.py      small helpers the strategies share
│   │       ├── ashby.py
│   │       ├── greenhouse.py
│   │       ├── lever.py
│   │       └── smartrecruiters.py
│   ├── storage/                 where data is saved
│   │   ├── base.py              JobStore interface
│   │   └── json_store.py        JSON files under data/
│   ├── services/
│   │   ├── job_service.py       JobService: the operations CLI and API both use
│   │   ├── queries.py           JobQuery, JobPage, AllJobsPage, JobFacets, SourceStatus
│   │   ├── refresh_runner.py    "Fetch all jobs": a background queue and thread pool
│   │   ├── today_jobs.py        data/todays-jobs.json, the fast path for /today
│   │   ├── catalog_editor.py    add, edit, delete and check sources (and logos) from the website
│   │   ├── monitor.py           the monitor: scheduled fetching and alerts
│   │   ├── email_sender.py      alert emails through your SMTP server
│   │   ├── sound.py             the alert chime, played by this computer
│   │   └── keep_awake.py        stops the computer sleeping while the monitor is on
│   ├── api/                     FastAPI app for the frontend
│   │   ├── __main__.py          `python -m jobsentry.api` (runs uvicorn)
│   │   ├── app.py               create_app(): CORS, error handlers, routers, shutdown
│   │   ├── dependencies.py      settings / HTTP client / JobService per request
│   │   ├── errors.py            exceptions -> HTTP status + one JSON error shape
│   │   ├── schemas.py           Pydantic request and response models (the public contract)
│   │   └── routes/              health, sources, jobs, all_jobs, catalog, monitor
│   └── cli/
│       ├── main.py              builds the parser from COMMANDS
│       ├── output.py            shared output formatting
│       └── commands/            one class per command: sources, list, show
├── scripts/
│   └── missing_countries.py     find locations that need a country hint
├── .env                         local settings (git-ignored)
├── .env.example                 settings template (committed)
└── data/                        generated output (git-ignored)
```

### How the layers depend on each other

```
cli        api
  └────┬────┘
   services (JobService, refresh_runner, today_jobs, catalog_editor, monitor)
        ├── sources  (catalog → loader → strategy → JobSource)  ── core.http
        └── storage  (JobStore → JsonJobStore)
                       all layers use core.models and core.exceptions
```

Each layer only depends on the ones below it. Sources never save files, storage never fetches, and the CLI only calls services. The FastAPI app sits next to `cli/` and calls the same services, so both interfaces behave identically.

## Choosing sources

Job Sentry only reads data it's allowed to read. Before adding a company:

1. **Prefer an official public API.** Job board platforms publish hosted boards as public APIs. Check where a company's "Apply" links go: `boards.greenhouse.io` / `job-boards.greenhouse.io`, `jobs.ashbyhq.com`, `jobs.lever.co` / `jobs.eu.lever.co` and `jobs.smartrecruiters.com` all mean a public board exists.
2. **Read the terms of use** of any site you'd read directly. If they forbid automated access (robots, spiders, scraping), don't add it.
3. **Check `robots.txt`** for any site you'd read directly. It doesn't override the terms of use.
4. **Never log in, and never work around a block.** A 401 or 403 raises `SourceBlockedError`, which is never retried.
5. **Keep refreshes light.** Most sources make one or two requests per board; large SmartRecruiters boards make one per 100 jobs. If refresh results show rate limiting, lower `JOBSENTRY_REFRESH_WORKERS`, and prefer a longer monitor interval.

## Adding a company

Companies are data, not code. Find the company's **board name**: the last part of its board URL (`jobs.ashbyhq.com/<name>`, `boards.greenhouse.io/<name>`, `jobs.lever.co/<name>`, `jobs.smartrecruiters.com/<name>`).

### From the website (easiest)

Open **Command center, then Manage sources, then Add source**:

1. **Fill in the form:** the platform, company, name, board name(s), optional careers page, region (Lever only), and an optional PNG logo.
2. **Press Check.** It requests each board once, exactly as a refresh would, and shows what came back.
3. **Save.** This only becomes available once the check has passed for the current platform, board names and region.

The entry is validated like a hand-edited one and written to the right catalog file, and it's available straight away, with no restart. The same page edits and deletes sources (see "Managing sources from the website" below).

### By editing a catalog file

Check the board in a browser, then add an entry to that platform's catalog in `sources/catalogs/`.

| Platform | Catalog | Check this URL shows jobs |
|---|---|---|
| Ashby | `ashby-sources.json` | `https://api.ashbyhq.com/posting-api/job-board/<name>` |
| Greenhouse | `greenhouse-sources.json` | `https://boards-api.greenhouse.io/v1/boards/<name>/jobs` |
| Lever | `lever-sources.json` | `https://api.lever.co/v0/postings/<name>?mode=json` (or `api.eu.lever.co` for EU-hosted companies) |
| SmartRecruiters | `smartrecruiters-sources.json` | `https://api.smartrecruiters.com/v1/companies/<name>/postings?limit=1`: `totalFound` must be above 0, because a wrong name also answers with 0 jobs rather than an error. The name is case-sensitive (`Wise`, `BoschGroup`) |

Every platform uses the same entry format:

```json
{
  "name": "acme",
  "company": "Acme",
  "board_name": "acme",
  "homepage": "https://acme.example/careers",
  "country_hints": { "SF": "US" },
  "state_codes": true
}
```

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | lowercase letters, digits, `-` or `_`; used in URLs, as the `data/<name>/` folder and as the logo's file name. Must be unique across all catalogs |
| `company` | yes | display name |
| `board_name` | yes | the board's name on the platform, or a list of names for a company with several boards (e.g. one per region), merged into one source |
| `homepage` | no | careers page; defaults to the first board's page |
| `country_hints` | no | location text → ISO country code for this company only, added to (and overriding) the shared hints |
| `state_codes` | no | `true` to read "City, ST" and "Remote - ST" as a US state or Canadian province when nothing else matched; for North American boards only |
| `region` | Lever only | `"eu"` for companies on Lever's EU instance; defaults to `"global"` |
| `max_pages` | SmartRecruiters only | most list pages (100 jobs each) fetched per board; overrides the catalog's top-level `max_pages` (default 100) |

Then:

1. Restart the API (or just run the CLI), and refresh the new source.
2. Run `python scripts/missing_countries.py <name>` and fix what it lists (see "Country matching" below), then refresh again.
3. Optionally add a logo at `frontend/public/logos/<name>.png` (or `.jpg`), ideally with a transparent background. Without one, the card shows the company's initials.

The order of entries in a catalog is the order "Fetch all jobs" takes them. The catalogs are checked when they load: a missing or unknown key, a duplicate `name`, or a bad URL, number or country code stops with a `ConfigError` naming the file and entry, so a typo never silently drops a company.

### Platform notes

- **Greenhouse:** two small requests per board (jobs, then departments for team names). Descriptions are fetched only when a job's details are opened. The only platform with an updated date.
- **Ashby:** one request per board, which includes descriptions; details re-read the board.
- **Lever:** one request per board; details come from the single-posting endpoint.
- **SmartRecruiters:**
  - **Fetching:** only the list endpoint is used, one request per 100 jobs, up to `max_pages` per board. No filters are sent.
  - **English only:** only English postings (and those without a language) are kept.
  - **Countries** come from each posting's country code.
  - **Work mode** is remote, hybrid, or otherwise on-site.
  - **No details request:** opening details makes no request, since each job links to its posting page.
  - **A sudden drop to zero is refused:** if a refresh finds 0 jobs for a company that previously had some, the refresh fails and the saved jobs are kept.

## Managing sources from the website

`services/catalog_editor.py` adds, edits and deletes catalog entries and logos for the website's **Manage sources** pages, through the `/catalog` endpoints (see "API" below).

- **Validated like startup.** Every change is checked by the same loader code that runs at startup, before anything is written, so the same rules and messages apply. A name must also be unique across all catalogs.
- **Atomic, and live at once.** Catalog files are written atomically and the registry reloads, so changes apply with no restart. If the reload fails, the previous files are restored.
- **Hand-edited keys are kept.** Editing changes only the form's fields (`company`, `board_name`, `homepage`, `region`); other keys such as `country_hints`, `state_codes` and `max_pages` are kept as they are. Moving a source to another platform moves it to that catalog and drops keys the new platform doesn't allow. A name can't change; to rename, delete and add again.
- **Delete removes everything:** the catalog entry, `data/<name>/`, the source's part of `todays-jobs.json`, and its logo. It can't be undone.
- **Logos** are PNGs of up to 2 MB, saved as `<JOBSENTRY_LOGOS_DIR>/<name>.png` (by default `frontend/public/logos/`), which is where the frontend looks for them. Uploading replaces any `.jpg` logo for the same name.
- **Refused while fetching.** Changes are refused while "Fetch all jobs" is running or while that source is refreshing (409).
- **Can be switched off.** Turning off `JOBSENTRY_ALLOW_CATALOG_EDITS` makes every change a 403 and hides "Manage sources" in the website.

**Safety:** this lets the website write files on the computer running the API. That's fine with the default `JOBSENTRY_API_HOST=127.0.0.1`, where only that computer can reach the API. If you ever listen on another address (e.g. `0.0.0.0`), set `JOBSENTRY_ALLOW_CATALOG_EDITS=false`.

## Monitor and alerts

`services/monitor.py` fetches every source on a schedule and alerts about new jobs. It's controlled from the website's **Monitor** page (the `/monitor` endpoints below).

**Schedule**
- **Every 15, 30 or 45 minutes, or every 1 to 24 hours,** measured from the start of each fetch. **Start** fetches straight away.
- **Each scheduled fetch is a normal fetch-all** (the same queue as "Fetch all jobs"), so every page updates as companies finish.
- **It runs only while the API runs.** Stopping the API (Ctrl+C) stops it, and a fresh API always starts with the monitor off.
- **While it's on, the computer is kept from idle sleep:** `caffeinate` on macOS, `SetThreadExecutionState` on Windows, `systemd-inhibit` on Linux. Closing a laptop's lid still sleeps it.

**What counts as new.** After **every** fetch-all finishes, scheduled or started with the button:

1. **The jobs considered** are those posted **today** (in `JOBSENTRY_TIMEZONE`) that match the monitor's keywords. The matching is the same as Today's jobs: every word in the title or a team name. With no keywords, every job counts.
2. **Only those posted after the previous fetch-all started** (the "watermark") are new. The first fetch after Start takes all of today's matching jobs.
3. **A job is announced at most once a day,** however many fetches see it.
4. **The watermark then moves** to this fetch's start.

**Alerts,** when a fetch finds any new jobs:
- **Sound:** a 4-second chime, played **immediately** by the computer running the API (`afplay` on macOS, `winsound` on Windows, `paplay` or `aplay` on Linux). It plays whether or not a browser tab is open.
- **Email:** one email listing the new jobs, through the SMTP server in `.env` (see "Configuration"). It's only sent to an address that has been **verified**: the Monitor page sends a test email, then asks whether it arrived, and only "yes" verifies it. Changing the SMTP settings or the address requires verifying again.
- **Banner:** open Job Sentry tabs check `/monitor/poll` every 15 seconds and show a "N new jobs" banner linking to Today's jobs.

The monitor's settings, the watermark, email verification and the last 50 alerts are kept in `data/monitor.json`. "Clear saved jobs" doesn't touch it; deleting it resets the monitor.

## Country matching

Job board APIs mostly give locations as free text ("Dublin", "SF, NYC", "Remote - TX"), so each job's `countries` are worked out at refresh time by `CountryFinder` in `core/countries.py`. Lever and SmartRecruiters also give a country code, which is used directly. For each location it collects matches from, in order:

1. **Built-in names:** country names, US state names and Canadian province names, in any case.
2. **Abbreviations:** US, U.S., USA, UK, U.K. and UAE, in capitals only.
3. **Hints:** the shared `country-hints.json` plus the company's own `country_hints` (the company's win).
4. **State codes:** only if nothing above matched and the company has `"state_codes": true`.

Matches are whole words (so "Helsinki" matches inside "FI-Helsinki-MSO"), and the longest text wins (so "Dublin, CA" beats "Dublin").

Where a fix goes:

| `missing_countries.py` lists | Fix |
|---|---|
| a country name ("Cyprus") | `COUNTRY_NAMES` in `core/countries.py` |
| an unambiguous city ("Lisbon"), or a spelling of one ("Iași") | shared `country-hints.json`, alphabetically |
| a company's shorthand ("CHI"), or text that means something else elsewhere ("Alexandria") | that company's `country_hints` |
| "Georgia" (the US state or the country) | that company's `country_hints`, after checking its jobs |
| a shared hint that's wrong for one company | that company's `country_hints` with the fuller text, e.g. `"Dublin, CA": "US"` |
| many "City, ST" locations | `"state_codes": true` on that company |
| regions and non-places ("Remote", "EMEA", "Europe") | leave them; no single country fits |

Codes are always two-letter ISO codes (`AE`, not `UAE`; `GB`, not `UK`). `country_hints` and `state_codes` aren't on the website's form; edit them in the catalog file (the website keeps them when it saves).

## Adding a platform

A platform needs three pieces, plus one line for the website:

1. **A strategy** in `sources/strategies/<platform>.py`: a `JobSource` subclass that sets `strategy = "<platform>"`, declares its settings as class attributes, and implements `fetch_jobs()` and `fetch_job_details(job)` against the platform's public API. It can also override `check_refresh(jobs, previous)`, which is called before saving and may refuse the save (see SmartRecruiters). Export it from `sources/strategies/__init__.py`.
2. **A catalog** in `sources/catalogs/<platform>-sources.json`: the API base URLs once at the top, plus a `sources` list using the entry format above.
3. **A loader** in `sources/loaders/<platform>_loader.py`: a `load()` function that validates the catalog with the helpers in `_catalog.py` (including `read_country_hints()`, `get_token_list()` and `get_int()`), builds one subclass per entry with `make_source_class()`, and registers them all. Add it to `LOADERS` in `sources/loaders/__init__.py`, and the platform's strategy name to `JOBSENTRY_REFRESH_ORDER` (and `DEFAULT_REFRESH_ORDER` in `config.py`).
4. **For the website:** add a `Platform` to `PLATFORMS` in `services/catalog_editor.py`. It names the loader, the request a check makes (the same one a refresh makes), and how to count jobs in the response.

Rules for strategies:
- **IDs** are always strings.
- **Fill only what the platform states.** Leave `work_modes` or `countries` empty rather than guessing.
- **Use `CountryFinder`** for free-text locations.
- **Record each job's board** in `Job.extra["board_name"]`.
- **Raise `SourceError`** when a response doesn't look as expected.
- **Use `get_json()` from `_helpers.py`** rather than `requests` directly.

## Adding a CLI command

Create `cli/commands/<command>.py` with a `Command` subclass (`name`, `help`, `add_arguments`, `run`), then add an instance to `COMMANDS` in `cli/commands/__init__.py`. Only commands in that list can be run. Put the actual logic in a service so the API can reuse it.

## API

Start it from `backend/`:

```bash
python -m jobsentry.api            # http://127.0.0.1:8000
python -m jobsentry.api --reload   # restart automatically when code or catalogs change
```

`--reload` restarts the API on every code change, which also stops the monitor. Use it while developing, not while monitoring.

Open **http://127.0.0.1:8000/docs** for interactive documentation where you can try every endpoint. All paths start with `/api/v1`.

**Sources and jobs**

| Method | Path | What it does | CLI equivalent |
|---|---|---|---|
| GET | `/health` | check the API is up | |
| GET | `/sources` | every source, with `fetched_at` and `job_count` | `sources` |
| POST | `/sources/refresh` | start fetching every source in the background; returns the run's progress | |
| GET | `/sources/refresh` | progress of the current run (including what started it), or the last run's result | |
| POST | `/sources/clear` | delete all saved jobs, details and `todays-jobs.json` | |
| GET | `/sources/{source}` | one source and its status | |
| POST | `/sources/{source}/refresh` | fetch one source's jobs again and save them | `list <source>` |
| GET | `/sources/{source}/jobs` | one source's saved jobs, filtered, sorted and paginated | |
| GET | `/sources/{source}/jobs/facets` | teams, locations and countries with counts | |
| GET | `/sources/{source}/jobs/{job_id}` | full details (saved copy, or fetched once) | `show <source> <id>` |
| GET | `/jobs` | saved jobs across every source, e.g. today's jobs | |

**Managing sources** (used by the website's Manage sources pages)

| Method | Path | What it does |
|---|---|---|
| GET | `/catalog` | the platforms, and whether editing is allowed (`edits_allowed`) |
| GET | `/catalog/sources/{name}` | one source's entry, as the form edits it, plus the names of keys kept as they are |
| POST | `/catalog/check` | `{platform, board_names, region?}`: request each board once, as a refresh would; returns `ok` and one result per board (status, job count, message) |
| POST | `/catalog/sources` | add a source: `{platform, name, company, board_names, homepage?, region?}` |
| PUT | `/catalog/sources/{name}` | edit a source (same body; `name` can't change, and other keys are kept) |
| DELETE | `/catalog/sources/{name}` | delete a source, its saved jobs and its logo |
| PUT | `/catalog/sources/{name}/logo` | upload a logo: the PNG file itself as the body, `Content-Type: image/png` |
| DELETE | `/catalog/sources/{name}/logo` | remove a source's logo |

**Monitor** (used by the website's Monitor page and every open tab)

| Method | Path | What it does |
|---|---|---|
| GET | `/monitor` | settings and status: on or off, next and last fetch, email set up and verified, last email result |
| PUT | `/monitor/settings` | `{every, unit, keywords, sound, email, email_to}` |
| POST | `/monitor/start` | start monitoring: fetch now, then every interval |
| POST | `/monitor/stop` | stop monitoring |
| GET | `/monitor/poll?after=<id>` | status plus alerts newer than `<id>` (open tabs call this every 15 seconds) |
| POST | `/monitor/test-sound` | play the alert chime on this computer |
| POST | `/monitor/test-email` | `{email_to}`: send a test email (step 1 of verifying) |
| POST | `/monitor/confirm-email` | `{email_to, received}`: confirm whether it arrived (step 2) |

Options for `/sources/{source}/jobs` and `/jobs`, all optional:

- `q`: keywords; every word must appear in the title or a team name (case-insensitive)
- `country`: ISO country code; repeat it for several (`country=CA&country=US`), and a job in any of them matches
- `sort`: `newest` (default) or `oldest`, by date posted; jobs without a date go last
- `limit` (1–200, default 50) and `offset`
- `/jobs` only: `posted_on` (`YYYY-MM-DD`) and `tz` (an IANA time zone, default `UTC`), for jobs first published on that date in that time zone

Example:
```
GET /api/v1/jobs?posted_on=2026-11-01&tz=Asia/Kolkata&country=US&q=engineer
```

**Fetching every source.** `POST /sources/refresh` (and the monitor) queues every source, grouped by platform in `JOBSENTRY_REFRESH_ORDER` and in catalog order within each, and a pool of `JOBSENTRY_REFRESH_WORKERS` threads takes them from the front of the queue. Each source is saved as soon as it finishes, and a failing source is recorded while the rest carry on. Only one run happens at a time; starting another while one runs returns the running one. A run lives in the API's memory, so restarting the API stops it (sources already finished stay saved).

**Today's jobs.** Every save also updates that source's section of `data/todays-jobs.json`, which holds the jobs posted today in `JOBSENTRY_TIMEZONE`. When `/jobs` is asked for that date and time zone, it reads this one file instead of every `jobs.json`; otherwise it reads the saved jobs, so results are never stale.

**Caching rules.** GET endpoints never fetch on their own, except the first time a source has no saved data. Only the refresh endpoints, the monitor, `?refresh=true` on a job's details, and `/catalog/check` contact job boards, so browsing in the UI sends no traffic to companies. Two refreshes of the same source can't run at once, and clearing or changing sources is refused while anything is being fetched; both get a 409.

**Errors** always have one shape, so the frontend can handle them in one place:

```json
{"error": {"code": "job_not_found", "message": "No Stripe job with ID '999'"}}
```

| Status | `code` | Meaning |
|---|---|---|
| 403 | `catalog_edits_disabled` | editing sources is turned off (`JOBSENTRY_ALLOW_CATALOG_EDITS=false`) |
| 404 | `source_not_found`, `job_not_found`, `not_found` | unknown source, job, or URL |
| 409 | `refresh_in_progress` | that source (or every source) is already being fetched |
| 422 | `invalid_request` | bad parameter, e.g. an unknown time zone (with a `details` list) |
| 422 | `invalid_entry` | a source from the website isn't valid (e.g. a duplicate name or a bad board name), or a logo isn't a PNG of up to 2 MB |
| 422 | `invalid_monitor_settings` | the monitor's settings aren't valid, e.g. email chosen without a verified address |
| 502 | `email_error` | the mail server failed or refused (the message says why, e.g. a wrong app password) |
| 502 | `source_blocked` | the job board refused automated access; not retried or worked around |
| 502 | `source_error` | the job board failed, its response changed, or a refresh was refused (e.g. a sudden drop to zero jobs) |
| 500 | `config_error`, `internal_error` | problem on our side, e.g. an invalid catalog |

**Adding endpoints.** Put the logic in a service first (so the CLI can use it too), add request and response models to `schemas.py`, then add a route in `api/routes/`. A new group of endpoints is a new module with a `router`, added to `ROUTERS` in `api/routes/__init__.py`. New exception types get a status in `ERROR_MAP` in `api/errors.py`.

## Configuration

Settings come from `backend/.env`, loaded automatically on every run. A template is in `backend/.env.example`:

```bash
cp .env.example .env      # run from backend/
```

`.env` is git-ignored, so each machine keeps its own, and passwords in it never reach the repository. Variables set in your shell override the file for a single run, e.g. `JOBSENTRY_HTTP_TIMEOUT=60 python -m jobsentry list stripe`. Invalid values (like `JOBSENTRY_HTTP_RETRIES=lots`) stop with a clear error. Restart the API after changing `.env`.

| Variable | Default | Purpose |
|---|---|---|
| `JOBSENTRY_DATA_DIR` | `data` | where JSON is written; relative paths are relative to `backend/` |
| `JOBSENTRY_HTTP_TIMEOUT` | `30` | seconds per request |
| `JOBSENTRY_HTTP_RETRIES` | `3` | retries on 429/5xx and connection errors |
| `JOBSENTRY_USER_AGENT` | browser string | User-Agent sent with requests |
| `JOBSENTRY_REFRESH_WORKERS` | `5` | how many sources a fetch-all fetches at the same time (1–32) |
| `JOBSENTRY_REFRESH_ORDER` | `ashby,greenhouse,lever,smartrecruiters` | platforms in the order a fetch-all works through them |
| `JOBSENTRY_TIMEZONE` | this computer's | IANA time zone for "today" (Today's jobs and the monitor), e.g. `Asia/Kolkata` (set it on Windows) |
| `JOBSENTRY_ALLOW_CATALOG_EDITS` | `true` | allow adding, editing and deleting sources (and logos) from the website; turn off if the API listens beyond `127.0.0.1` |
| `JOBSENTRY_LOGOS_DIR` | `../frontend/public/logos` | where uploaded logos are saved as `<name>.png`; relative paths are relative to `backend/` |
| `JOBSENTRY_SMTP_HOST` | empty | mail server for monitor emails; empty turns email off |
| `JOBSENTRY_SMTP_PORT` | `587` | mail server port |
| `JOBSENTRY_SMTP_SECURITY` | `starttls` | `starttls` (usual for 587), `ssl` (usual for 465) or `none` |
| `JOBSENTRY_SMTP_USERNAME` | empty | login, if the server needs one |
| `JOBSENTRY_SMTP_PASSWORD` | empty | password; for Gmail and Outlook, an app password |
| `JOBSENTRY_SMTP_FROM` | empty | sender address, usually the same as the username |
| `JOBSENTRY_API_HOST` | `127.0.0.1` | API address; the default is reachable from this computer only |
| `JOBSENTRY_API_PORT` | `8000` | API port |
| `JOBSENTRY_CORS_ORIGINS` | local dev ports 5173, 3000 | comma-separated frontend URLs allowed to call the API |

**Gmail example:**

```dotenv
JOBSENTRY_SMTP_HOST=smtp.gmail.com
JOBSENTRY_SMTP_PORT=587
JOBSENTRY_SMTP_SECURITY=starttls
JOBSENTRY_SMTP_USERNAME=you@gmail.com
JOBSENTRY_SMTP_PASSWORD=your16letterapppassword
JOBSENTRY_SMTP_FROM=you@gmail.com
```

Gmail needs 2-Step Verification on the account, then an app password from https://myaccount.google.com/apppasswords.

New settings go in `config.py` (a field on `Settings` plus a line in `from_env`) and in `.env.example`.

## Output format

```
data/
├── <source>/jobs.json         every job from the source's last refresh
├── <source>/jobs/<id>.json    one job's full details, saved when opened
├── todays-jobs.json           jobs posted today, by source (services/today_jobs.py)
└── monitor.json               the monitor's settings, watermark and recent alerts (services/monitor.py)
```

`data/<source>/jobs.json`:

```json
{
  "source": "stripe",
  "fetched_at": "2026-11-01T09:30:00+00:00",
  "count": 673,
  "jobs": [
    {
      "source": "stripe",
      "id": "8172508",
      "title": "Abuse Investigator",
      "url": "https://stripe.com/jobs/search?gh_jid=8172508",
      "company": "Stripe",
      "teams": ["Risk & Financial Crimes"],
      "locations": ["Dublin"],
      "countries": ["IE"],
      "work_modes": [],
      "employment_type": null,
      "posted_at": "2026-09-03T13:32:53-04:00",
      "updated_at": "2026-10-22T09:16:15-04:00",
      "extra": {"board_name": "stripe"}
    }
  ]
}
```

- **`work_modes`** holds any of `on_site`, `hybrid` and `remote`, only when the source states them.
- **`countries`** holds ISO 3166-1 alpha-2 codes.
- **`updated_at`** is only given by Greenhouse, and it includes bulk edits across a whole board.
- **`extra.board_name`** records which board a job came from.
- **Files saved by older versions still load:** unknown fields are ignored and missing ones get defaults.

`data/<source>/jobs/<id>.json` holds every `Job` field plus `description`, `description_format` and `apply_url`. Descriptions are HTML for Greenhouse, Ashby and Lever. For SmartRecruiters, details make no request, so the description is empty and `apply_url` is the posting page.