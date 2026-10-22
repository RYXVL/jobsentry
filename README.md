# Job Sentry

Collects job listings from company career sites and serves them to a local web UI.

## Setup

```bash
pip install -r requirements.txt
cp backend/.env.example backend/.env
```

Set environment variables inside backend/.env as required.

## Usage

Run from the `backend/` folder:

```bash
cd backend
python -m jobsentry sources                      # list available sources
python -m jobsentry list <company_name>          # fetch all jobs -> data/<company_name>/jobs.json
python -m jobsentry show <company_name> <job_id> # one job by ID -> data/<company_name>/jobs/<job_id>.json
```

Start the API for the frontend (also from `backend/`):

```bash
python -m jobsentry.api            # http://127.0.0.1:8000, docs at /docs
python -m jobsentry.api --reload   # auto-restart on code changes
```

Tests: `cd backend && python -m pytest`

Requires Python 3.10+.

See [backend/README.md](backend/README.md) for the architecture and how to add a company.
