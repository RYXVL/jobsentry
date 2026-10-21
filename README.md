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

Tests:
```bash
cd backend
python -m pytest
```

See [backend/README.md](backend/README.md) for the architecture and how to add a company.
