# Job Sentry

Collects job listings from companies' public job board APIs and shows them
in a local web UI, newest first. Local and non-commercial: it only reads
data that job boards publish for public use.

Requires Python 3.10+ and Node 18+.

## Setup

```bash
pip install -r requirements.txt

# Adjust environment variables as needed after copying files.
cp backend/.env.example backend/.env
cd frontend && npm install && cp .env.example .env
```

## Usage

Run from the `backend/` folder:

```bash
python -m jobsentry sources                 # list available sources
python -m jobsentry list <source>           # fetch all jobs -> data/<source>/jobs.json
python -m jobsentry show <source> <job_id>  # one job -> data/<source>/jobs/<job_id>.json
python -m jobsentry.api                     # API on http://127.0.0.1:8000, docs at /docs
```

From `frontend/`, with the API running:

```bash
npm run dev                                 # web UI on http://localhost:5173
```

## Adding a company

Companies are entries in a JSON catalog, not code. See
[backend/README.md](backend/README.md#adding-a-company) for the steps, the
rules for choosing sources, and the architecture.

## Licence

Job Sentry is released under the [MIT License](LICENSE). It isn't affiliated
with any company it lists, or with Greenhouse, Ashby or Lever; company names
and logos belong to their owners. See the app's Terms and Privacy pages for
details.