# Job Sentry Backend

Scrapes company career sites into a common JSON format. Run every command from this folder.

```bash
python -m jobsentry sources                      # list available sources
python -m jobsentry list <company_name>          # fetch all jobs -> data/<company_name>/jobs.json
python -m jobsentry show <company_name> <job_id> # one job by ID -> data/<company_name>/jobs/<job_id>.json
python -m jobsentry -v list <company_name>       # same, with progress logs
python -m pytest                                 # run the tests (offline, uses saved HTML)
```

## Structure

```
backend/
├── jobsentry/
│   ├── __main__.py           entry point for `python -m jobsentry`
│   ├── config.py             Settings, loaded from backend/.env
│   ├── core/                 shared building blocks, no business logic
│   │   ├── models.py         Job, JobDetails, Salary, JobSnapshot
│   │   ├── http.py           HttpClient: headers, timeouts, retries
│   │   └── exceptions.py     JobsentryError and subclasses
│   ├── sources/              how to read each site
│   │   ├── base.py           JobSource interface
│   │   ├── registry.py       @register, create_source(), auto-discovery
│   │   ├── strategies/       one base class per way sites deliver data
│   │   │   └── next_data.py  Next.js __NEXT_DATA__ pages
│   │   └── companies/        one file per company, loaded automatically
│   │       └── stripe.py
│   ├── storage/              where data is saved
│   │   ├── base.py           JobStore interface
│   │   └── json_store.py     JSON files under data/
│   ├── services/
│   │   └── job_service.py    JobService: the operations CLI and API both use
│   └── cli/
│       ├── main.py           builds the parser from COMMANDS
│       ├── output.py         shared output formatting
│       └── commands/         one class per command: sources, list, show
├── tests/                    pytest suite + saved HTML fixtures
├── .env                      local settings (git-ignored)
├── .env.example              settings template (committed)
└── data/                     generated output (git-ignored)
```

### How the layers depend on each other

Each layer only depends on the ones below it. Sources never save files, storage never fetches, and the CLI only calls `JobService`.

## Adding a company
 
1. Work out how the site delivers its data (DevTools → Network, or View Source).
2. If a matching strategy exists in `sources/strategies/`, subclass it. If not, add a new strategy there first (see below), or subclass `JobSource` directly for a one-off site.
3. Create `sources/companies/<name>.py`:
```python
from ...core.models import Job, JobDetails
from ..registry import register
from ..strategies import NextDataSource
 
 
@register
class AcmeSource(NextDataSource):
    name = "acme"                    # used on the command line
    company = "Acme"
    homepage = "https://acme.example/careers"
 
    def fetch_jobs(self) -> list[Job]:
        props = self.get_page_props("https://acme.example/careers")
        return [
            Job(source=self.name, id=str(j["id"]), title=j["title"],
                url=j["url"], company=self.company, locations=j["locations"])
            for j in props["jobs"]
        ]
 
    def fetch_job_details(self, job: Job) -> JobDetails:
        props = self.get_page_props(job.url)
        return JobDetails.from_job(job, description=props["job"]["body"],
                                   description_format="html")
```
 
4. Save one listing page and one detail page into `tests/fixtures/` and add tests like the Stripe ones in `tests/test_sources.py`.
Nothing else changes. The registry finds the file, and `sources`, `list acme` and `show acme <id>` work immediately.
 
Rules for sources: always output IDs as strings; put anything you need later (slugs, internal IDs) in `Job.extra`; raise `SourceError` when the page doesn't look as expected; use `self.http` rather than `requests` directly.
 
## Adding a strategy
 
A strategy is a reusable base class for one data-delivery method, so several companies can share the parsing code. Create `sources/strategies/<method>.py` with a `JobSource` subclass that sets `strategy = "<method>"` and provides helper methods (like `NextDataSource.get_page_props`), then export it from `sources/strategies/__init__.py`. Likely next ones: `json_api`, `greenhouse`, `workday`, `json_ld`.
 
## Adding a CLI command
 
Create `cli/commands/<command>.py` with a `Command` subclass (`name`, `help`, `add_arguments`, `run`), then add an instance to `COMMANDS` in `cli/commands/__init__.py`. Only commands in that list can be run. Put the actual logic in `JobService` so the API can reuse it.
 
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
 
New settings go in `config.py` (a field on `Settings` plus a line in `from_env`) and in `.env.example`.
 
## Output format
 
`data/<source>/jobs.json`:
 
```json
{
  "source": "stripe",
  "fetched_at": "2026-10-13T09:30:00+00:00",
  "count": 1240,
  "jobs": [{ "source": "stripe", "id": "8144196", "title": "AI Engineer", "...": "..." }]
}
```
 
`data/<source>/jobs/<id>.json` holds every `Job` field plus `description`, `description_format`, `posted_at`, `salary` and `apply_url`.
 