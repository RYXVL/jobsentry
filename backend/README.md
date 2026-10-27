# Job Sentry Backend

Collects job listings from companies' public job board APIs (Greenhouse
today, Ashby next) into one common JSON format, and serves them to the
frontend through a local API. Run every command from this folder.

```bash
python -m jobsentry sources                  # list available sources
python -m jobsentry list <source>            # fetch all jobs -> data/<source>/jobs.json
python -m jobsentry show <source> <job_id>   # one job -> data/<source>/jobs/<job_id>.json
python -m jobsentry -v list <source>         # same, with progress logs
python -m jobsentry.api                      # start the API on http://127.0.0.1:8000
```

`<source>` is a source's `name` from its catalog, e.g. `stripe`, `figma`, `anthropic`.

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
│   │   │   ├── country-hints.json        city -> country, shared by every source
│   │   │   └── greenhouse-sources.json   companies on Greenhouse
│   │   ├── loaders/             read a catalog, register a source per entry
│   │   │   ├── _catalog.py      shared reading and validation helpers
│   │   │   └── greenhouse_loader.py
│   │   └── strategies/          one base class per platform's API
│   │       └── greenhouse.py
│   ├── storage/                 where data is saved
│   │   ├── base.py              JobStore interface
│   │   └── json_store.py        JSON files under data/
│   ├── services/
│   │   ├── job_service.py       JobService: the operations CLI and API both use
│   │   └── queries.py           JobQuery, JobPage, JobFacets, SourceStatus
│   ├── api/                     FastAPI app for the frontend
│   │   ├── __main__.py          `python -m jobsentry.api` (runs uvicorn)
│   │   ├── app.py               create_app(): CORS, error handlers, routers
│   │   ├── dependencies.py      settings / HTTP client / JobService per request
│   │   ├── errors.py            exceptions -> HTTP status + one JSON error shape
│   │   ├── schemas.py           Pydantic response models (the public contract)
│   │   └── routes/              health.py, sources.py, jobs.py
│   └── cli/
│       ├── main.py              builds the parser from COMMANDS
│       ├── output.py            shared output formatting
│       └── commands/            one class per command: sources, list, show
├── .env                         local settings (git-ignored)
├── .env.example                 settings template (committed)
└── data/                        generated output (git-ignored)
```

### How the layers depend on each other

```
cli        api
  └────┬────┘
   services.JobService
        ├── sources  (catalog → loader → strategy → JobSource)  ── core.http
        └── storage  (JobStore → JsonJobStore)
                       all layers use core.models and core.exceptions
```

Each layer only depends on the ones below it. Sources never save files, storage never fetches, and the CLI only calls `JobService`. The FastAPI app sits next to `cli/` and calls the same `JobService` methods, so both interfaces behave identically.

## Choosing sources

Job Sentry only reads data it's allowed to read. Before adding a company:

1. **Prefer an official public API.** Job board platforms such as Greenhouse publish hosted boards as public APIs. Check where a company's "Apply" links go: `boards.greenhouse.io`, `jobs.ashbyhq.com` and `jobs.lever.co` all mean a public board exists.
2. **Read the terms of use** of any site you'd read directly. If they forbid automated access (robots, spiders, scraping), don't add it.
3. **Check `robots.txt`** for any site you'd read directly. It doesn't override the terms of use.
4. **Never log in, and never work around a block.** A 401 or 403 raises `SourceBlockedError`, which is never retried.
5. **Keep refreshes light.** Prefer one request per refresh. Refresh-all fetches sources one at a time.

## Adding a company

Companies are data, not code. For a company on Greenhouse:

1. Find its board token: the `<token>` in `boards.greenhouse.io/<token>`.
2. Open `https://boards-api.greenhouse.io/v1/boards/<token>/jobs` in a browser. If you get JSON with jobs, the token is right.
3. Add an entry to `sources/catalogs/greenhouse-sources.json`:

```json
{
  "name": "acme",
  "company": "Acme",
  "board_token": "acme",
  "homepage": "https://acme.example/careers",
  "country_hints": { "SF": "US" }
}
```

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | lowercase letters, digits, `-` or `_`; used in URLs and as the `data/<name>/` folder |
| `company` | yes | display name |
| `board_token` | yes | the board's token on Greenhouse |
| `homepage` | no | careers page; defaults to the Greenhouse board |
| `country_hints` | no | hints for this company only, added to (and overriding) the shared list |

4. Restart the API (or just run the CLI), then refresh the new source.
5. With the API running, open `http://127.0.0.1:8000/api/v1/sources/<name>/jobs/facets` and compare `locations` with `countries`. For each location whose country wasn't found:
   - **A city** (e.g. "Lisbon") goes in `sources/catalogs/country-hints.json`, in alphabetical order, so every company benefits.
   - **A company's own shorthand** (e.g. Stripe's "CHI" or "SEA") goes in that entry's `country_hints`, because it could mean something else on another board.
6. Optionally add a logo at `frontend/public/logos/<name>.png` (or `.jpg`). Without one, the card shows the company's initials.

Country names themselves ("Canada", "United Kingdom") are recognised without any hints; see `COUNTRY_NAMES` in `core/countries.py`.

The catalogs are checked when they load. A missing or unknown key, a duplicate `name`, or a bad URL or country code stops with a `ConfigError` naming the file and entry, so a typo never silently drops a company.

## Adding a platform

A platform (e.g. Ashby) needs three pieces:

1. **A strategy** in `sources/strategies/<platform>.py`: a `JobSource` subclass that sets `strategy = "<platform>"`, declares its settings as class attributes, and implements `fetch_jobs()` and `fetch_job_details(job)` against the platform's public API. Export it from `sources/strategies/__init__.py`.
2. **A catalog** in `sources/catalogs/<platform>-sources.json`: the API base URLs once at the top, plus a `sources` list.
3. **A loader** in `sources/loaders/<platform>_loader.py`: a `load()` function that validates the catalog with the helpers in `_catalog.py` (including `read_country_hints()` for the shared hints), builds one subclass per entry and registers them all. Add it to `LOADERS` in `sources/loaders/__init__.py`.

Rules for strategies: always output IDs as strings; fill only what the platform states (leave `work_modes` or `countries` empty rather than guessing); use `CountryFinder` for free-text locations; put anything needed later in `Job.extra`; raise `SourceError` when a response doesn't look as expected; use `self.http.get_json()` rather than `requests` directly.

## Adding a CLI command

Create `cli/commands/<command>.py` with a `Command` subclass (`name`, `help`, `add_arguments`, `run`), then add an instance to `COMMANDS` in `cli/commands/__init__.py`. Only commands in that list can be run. Put the actual logic in `JobService` so the API can reuse it.

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
| POST | `/sources/refresh` | refresh every source, one at a time | |
| POST | `/sources/clear` | delete all saved jobs and details | |
| GET | `/sources/{source}` | one source and its status | |
| POST | `/sources/{source}/refresh` | fetch the source's jobs again and save them | `list <source>` |
| GET | `/sources/{source}/jobs` | saved jobs, filtered, sorted and paginated | |
| GET | `/sources/{source}/jobs/facets` | teams, locations and countries with counts | |
| GET | `/sources/{source}/jobs/{job_id}` | full details (saved copy, or fetched once) | `show <source> <id>` |

Options for `/jobs`, all optional:

- `q`: keywords; every word must appear in the title or a team name (case-insensitive)
- `country`: ISO country code; repeat it for several (`country=CA&country=US`), and a job in any of them matches
- `sort`: `newest` (default) or `oldest`, by date posted; jobs without a date go last
- `limit` (1–200, default 50)
- `offset`

Example:
```
GET /api/v1/sources/stripe/jobs?q=engineer&country=CA&country=US&sort=oldest&limit=20
```

`/facets` reads saved data only: `countries` feeds the country filter, and `locations` shows which places still need a country hint. Add `?refresh=true` to the details endpoint to fetch a job again.

**Caching rules.** GET endpoints never fetch on their own, except the first time a source has no saved data. Only `POST .../refresh` (or `?refresh=true` on a job) contacts the job board again, so browsing in the UI sends no traffic to companies. Two refreshes of the same source can't run at once; the second gets a 409.

**Errors** always have one shape, so the frontend can handle them in one place:

```json
{"error": {"code": "job_not_found", "message": "No Stripe job with ID '999'"}}
```

| Status | `code` | Meaning |
|---|---|---|
| 404 | `source_not_found`, `job_not_found`, `not_found` | unknown source, job, or URL |
| 409 | `refresh_in_progress` | that source is already being refreshed |
| 422 | `invalid_request` | bad parameter (with a `details` list) |
| 502 | `source_blocked` | the job board refused automated access; not retried or worked around |
| 502 | `source_error` | the job board failed or its response changed |
| 500 | `config_error`, `internal_error` | problem on our side, e.g. an invalid catalog |

**Adding endpoints.** Put the logic in `JobService` first (so the CLI can use it too), add response models to `schemas.py`, then add a route in `api/routes/`. A new group of endpoints is a new module with a `router`, added to `ROUTERS` in `api/routes/__init__.py`. New exception types get a status in `ERROR_MAP` in `api/errors.py`.

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
| `JOBSENTRY_API_HOST` | `127.0.0.1` | API address; the default is reachable from this computer only |
| `JOBSENTRY_API_PORT` | `8000` | API port |
| `JOBSENTRY_CORS_ORIGINS` | local dev ports 5173, 3000 | comma-separated frontend URLs allowed to call the API |

New settings go in `config.py` (a field on `Settings` plus a line in `from_env`) and in `.env.example`.

## Output format

`data/<source>/jobs.json`:

```json
{
  "source": "stripe",
  "fetched_at": "2026-10-27T09:30:00+00:00",
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
      "extra": {}
    }
  ]
}
```

`work_modes` holds any of `on_site`, `hybrid` and `remote`, only when the source states them; `countries` holds ISO 3166-1 alpha-2 codes. `updated_at` is when the platform last changed the job's record, which includes bulk edits across a whole board, so many jobs can share one value. Files saved by older versions still load: unknown fields are ignored and missing ones get defaults.

`data/<source>/jobs/<id>.json` holds every `Job` field plus `description`, `description_format` (`html` for Greenhouse) and `apply_url`.