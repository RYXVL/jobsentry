# Job Sentry Backend

Collects job listings from companies' public job board APIs (Greenhouse,
Ashby and Lever) into one common JSON format, and serves them to the
frontend through a local API. Run every command from this folder.

```bash
python -m jobsentry sources                     # list available sources
python -m jobsentry list <source>               # fetch one source's jobs -> data/<source>/jobs.json
python -m jobsentry show <source> <job_id>      # one job -> data/<source>/jobs/<job_id>.json
python -m jobsentry -v list <source>            # same, with progress logs
python -m jobsentry.api                         # start the API on http://127.0.0.1:8000
python scripts/missing_countries.py <source>    # saved locations that match no country
```

`<source>` is a source's `name` from its catalog, e.g. `stripe`, `supabase`, `spotify`.

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
│   │   ├── registry.py          register(), create_source(), loads the catalogs
│   │   ├── catalogs/            JSON data, read by the loaders
│   │   │   ├── ashby-sources.json        companies on Ashby
│   │   │   ├── greenhouse-sources.json   companies on Greenhouse
│   │   │   ├── lever-sources.json        companies on Lever
│   │   │   └── country-hints.json        location text -> country, shared by all
│   │   ├── loaders/             read a catalog, register a source per entry
│   │   │   ├── _catalog.py      shared reading and validation helpers
│   │   │   ├── ashby_loader.py
│   │   │   ├── greenhouse_loader.py
│   │   │   └── lever_loader.py
│   │   └── strategies/          one base class per platform's API
│   │       ├── _helpers.py      small helpers the strategies share
│   │       ├── ashby.py
│   │       ├── greenhouse.py
│   │       └── lever.py
│   ├── storage/                 where data is saved
│   │   ├── base.py              JobStore interface
│   │   └── json_store.py        JSON files under data/
│   ├── services/
│   │   ├── job_service.py       JobService: the operations CLI and API both use
│   │   ├── queries.py           JobQuery, JobPage, AllJobsPage, JobFacets, SourceStatus
│   │   ├── refresh_runner.py    "Fetch all jobs": a background queue and thread pool
│   │   └── today_jobs.py        data/todays-jobs.json, the fast path for /today
│   ├── api/                     FastAPI app for the frontend
│   │   ├── __main__.py          `python -m jobsentry.api` (runs uvicorn)
│   │   ├── app.py               create_app(): CORS, error handlers, routers, shutdown
│   │   ├── dependencies.py      settings / HTTP client / JobService per request
│   │   ├── errors.py            exceptions -> HTTP status + one JSON error shape
│   │   ├── schemas.py           Pydantic response models (the public contract)
│   │   └── routes/              health.py, sources.py, jobs.py, all_jobs.py
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
   services (JobService, refresh_runner, today_jobs)
        ├── sources  (catalog → loader → strategy → JobSource)  ── core.http
        └── storage  (JobStore → JsonJobStore)
                       all layers use core.models and core.exceptions
```

Each layer only depends on the ones below it. Sources never save files, storage never fetches, and the CLI only calls services. The FastAPI app sits next to `cli/` and calls the same services, so both interfaces behave identically.

## Choosing sources

Job Sentry only reads data it's allowed to read. Before adding a company:

1. **Prefer an official public API.** Job board platforms publish hosted boards as public APIs. Check where a company's "Apply" links go: `boards.greenhouse.io` / `job-boards.greenhouse.io`, `jobs.ashbyhq.com` and `jobs.lever.co` / `jobs.eu.lever.co` all mean a public board exists.
2. **Read the terms of use** of any site you'd read directly. If they forbid automated access (robots, spiders, scraping), don't add it.
3. **Check `robots.txt`** for any site you'd read directly. It doesn't override the terms of use.
4. **Never log in, and never work around a block.** A 401 or 403 raises `SourceBlockedError`, which is never retried.
5. **Keep refreshes light.** Each source makes one or two requests per board. If refresh results show rate limiting, lower `JOBSENTRY_REFRESH_WORKERS`.

## Adding a company

Companies are data, not code. Find the company's **board name**: the last part of its board URL (`jobs.ashbyhq.com/<name>`, `boards.greenhouse.io/<name>`, `jobs.lever.co/<name>`). Check that it works in a browser, then add an entry to that platform's catalog in `sources/catalogs/`.

| Platform | Catalog | Check this URL shows jobs |
|---|---|---|
| Ashby | `ashby-sources.json` | `https://api.ashbyhq.com/posting-api/job-board/<name>` |
| Greenhouse | `greenhouse-sources.json` | `https://boards-api.greenhouse.io/v1/boards/<name>/jobs` |
| Lever | `lever-sources.json` | `https://api.lever.co/v0/postings/<name>?mode=json` (or `api.eu.lever.co` for EU-hosted companies) |

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
| `name` | yes | lowercase letters, digits, `-` or `_`; used in URLs and as the `data/<name>/` folder. Must be unique across all catalogs |
| `company` | yes | display name |
| `board_name` | yes | the board's name on the platform, or a list of names for a company with several boards (e.g. one per region), merged into one source |
| `homepage` | no | careers page; defaults to the first board's page |
| `country_hints` | no | location text → ISO country code for this company only, added to (and overriding) the shared hints |
| `state_codes` | no | `true` to read "City, ST" and "Remote - ST" as a US state or Canadian province when nothing else matched; for North American boards only |
| `region` | Lever only | `"eu"` for companies on Lever's EU instance; defaults to `"global"` |

Then:

1. Restart the API (or just run the CLI), and refresh the new source.
2. Run `python scripts/missing_countries.py <name>` and fix what it lists (see "Country matching" below), then refresh again.
3. Optionally add a logo at `frontend/public/logos/<name>.png` (or `.jpg`), ideally with a transparent background. Without one, the card shows the company's initials.

The order of entries in a catalog is the order "Fetch all jobs" takes them. The catalogs are checked when they load: a missing or unknown key, a duplicate `name`, or a bad URL or country code stops with a `ConfigError` naming the file and entry, so a typo never silently drops a company.

## Country matching

Job board APIs mostly give locations as free text ("Dublin", "SF, NYC", "Remote - TX"), so each job's `countries` are worked out at refresh time by `CountryFinder` in `core/countries.py` (Lever also gives a country code, which is used directly). For each location it collects matches from, in order:

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

Codes are always two-letter ISO codes (`AE`, not `UAE`; `GB`, not `UK`).

## Adding a platform

A platform needs three pieces:

1. **A strategy** in `sources/strategies/<platform>.py`: a `JobSource` subclass that sets `strategy = "<platform>"`, declares its settings as class attributes, and implements `fetch_jobs()` and `fetch_job_details(job)` against the platform's public API. Export it from `sources/strategies/__init__.py`.
2. **A catalog** in `sources/catalogs/<platform>-sources.json`: the API base URLs once at the top, plus a `sources` list using the entry format above.
3. **A loader** in `sources/loaders/<platform>_loader.py`: a `load()` function that validates the catalog with the helpers in `_catalog.py` (including `read_country_hints()` and `get_token_list()`), builds one subclass per entry with `make_source_class()`, and registers them all. Add it to `LOADERS` in `sources/loaders/__init__.py`, and the platform's strategy name to `JOBSENTRY_REFRESH_ORDER`.

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

Open **http://127.0.0.1:8000/docs** for interactive documentation where you can try every endpoint. All paths start with `/api/v1`.

| Method | Path | What it does | CLI equivalent |
|---|---|---|---|
| GET | `/health` | check the API is up | |
| GET | `/sources` | every source, with `fetched_at` and `job_count` | `sources` |
| POST | `/sources/refresh` | start fetching every source in the background; returns the run's progress | |
| GET | `/sources/refresh` | progress of the current run, or the last run's result | |
| POST | `/sources/clear` | delete all saved jobs, details and `todays-jobs.json` | |
| GET | `/sources/{source}` | one source and its status | |
| POST | `/sources/{source}/refresh` | fetch one source's jobs again and save them | `list <source>` |
| GET | `/sources/{source}/jobs` | one source's saved jobs, filtered, sorted and paginated | |
| GET | `/sources/{source}/jobs/facets` | teams, locations and countries with counts | |
| GET | `/sources/{source}/jobs/{job_id}` | full details (saved copy, or fetched once) | `show <source> <id>` |
| GET | `/jobs` | saved jobs across every source, e.g. today's jobs | |

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

**Fetching every source.** `POST /sources/refresh` queues every source, grouped by platform in `JOBSENTRY_REFRESH_ORDER` and in catalog order within each, and a pool of `JOBSENTRY_REFRESH_WORKERS` threads takes them from the front of the queue. Each source is saved as soon as it finishes, and a failing source is recorded while the rest carry on. Only one run happens at a time; starting another while one runs returns the running one. A run lives in the API's memory, so restarting the API stops it (sources already finished stay saved).

**Today's jobs.** Every save also updates that source's section of `data/todays-jobs.json`, which holds the jobs posted today in `JOBSENTRY_TIMEZONE`. When `/jobs` is asked for that date and time zone, it reads this one file instead of every `jobs.json`; otherwise it reads the saved jobs, so results are never stale.

**Caching rules.** GET endpoints never fetch on their own, except the first time a source has no saved data. Only the refresh endpoints (or `?refresh=true` on a job's details) contact job boards, so browsing in the UI sends no traffic to companies. Two refreshes of the same source can't run at once, and clearing is refused while anything is being fetched; both get a 409.

**Errors** always have one shape, so the frontend can handle them in one place:

```json
{"error": {"code": "job_not_found", "message": "No Stripe job with ID '999'"}}
```

| Status | `code` | Meaning |
|---|---|---|
| 404 | `source_not_found`, `job_not_found`, `not_found` | unknown source, job, or URL |
| 409 | `refresh_in_progress` | that source (or every source) is already being fetched |
| 422 | `invalid_request` | bad parameter, e.g. an unknown time zone (with a `details` list) |
| 502 | `source_blocked` | the job board refused automated access; not retried or worked around |
| 502 | `source_error` | the job board failed or its response changed |
| 500 | `config_error`, `internal_error` | problem on our side, e.g. an invalid catalog |

**Adding endpoints.** Put the logic in a service first (so the CLI can use it too), add response models to `schemas.py`, then add a route in `api/routes/`. A new group of endpoints is a new module with a `router`, added to `ROUTERS` in `api/routes/__init__.py`. New exception types get a status in `ERROR_MAP` in `api/errors.py`.

## Configuration

Settings come from `backend/.env`, loaded automatically on every run. A template is in `backend/.env.example`:

```bash
cp .env.example .env      # run from backend/
```

`.env` is git-ignored, so each machine keeps its own. Variables set in your shell override the file for a single run, e.g. `JOBSENTRY_HTTP_TIMEOUT=60 python -m jobsentry list stripe`. Invalid values (like `JOBSENTRY_HTTP_RETRIES=lots`) stop with a clear error.

| Variable | Default | Purpose |
|---|---|---|
| `JOBSENTRY_DATA_DIR` | `data` | where JSON is written; relative paths are relative to `backend/` |
| `JOBSENTRY_HTTP_TIMEOUT` | `30` | seconds per request |
| `JOBSENTRY_HTTP_RETRIES` | `3` | retries on 429/5xx and connection errors |
| `JOBSENTRY_USER_AGENT` | browser string | User-Agent sent with requests |
| `JOBSENTRY_REFRESH_WORKERS` | `5` | how many sources "Fetch all jobs" fetches at the same time (1–32) |
| `JOBSENTRY_REFRESH_ORDER` | `ashby,greenhouse,lever` | platforms in the order "Fetch all jobs" works through them |
| `JOBSENTRY_TIMEZONE` | this computer's | IANA time zone for "today" in `todays-jobs.json`, e.g. `Asia/Kolkata` (set it on Windows) |
| `JOBSENTRY_API_HOST` | `127.0.0.1` | API address; the default is reachable from this computer only |
| `JOBSENTRY_API_PORT` | `8000` | API port |
| `JOBSENTRY_CORS_ORIGINS` | local dev ports 5173, 3000 | comma-separated frontend URLs allowed to call the API |

New settings go in `config.py` (a field on `Settings` plus a line in `from_env`) and in `.env.example`.

## Output format

```
data/
├── <source>/jobs.json         every job from the source's last refresh
├── <source>/jobs/<id>.json    one job's full details, saved when opened
└── todays-jobs.json           jobs posted today, by source (see services/today_jobs.py)
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

`data/<source>/jobs/<id>.json` holds every `Job` field plus `description`, `description_format` (`html` for every current platform) and `apply_url`.