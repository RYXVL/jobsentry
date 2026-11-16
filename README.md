# Job Sentry

<a href="https://buymeacoffee.com/ryansojan">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy me a coffee" height="45">
</a>

Find new jobs the moment companies post them. Job Sentry reads companies'
public job boards (Ashby, Greenhouse, Lever and SmartRecruiters), keeps
the listings on your computer, and shows them in a local web app: today's
new jobs across every company, newest first, with keyword and country
filters, and an optional monitor that fetches on a schedule and alerts you
with a sound or an email.

It runs entirely on your own machine. There's no account, no server of
ours, and no tracking; it only reads job listings that job boards publish
for public use.

## Features

- **Today's jobs:** every job posted today across all companies, in one list, newest first.
- **Filters:** keywords (title or team), countries, and newest or oldest first, on every job list.
- **Fast fetching:** "Fetch all jobs" fetches every company in the background, 5 at a time, with live progress; data appears as each company finishes.
- **Monitor:** fetch every 15, 30 or 45 minutes, or every 1 to 24 hours, and be alerted about new matching jobs with a chime on your computer and/or an email. The computer is kept awake while it runs.
- **Manage sources from the website:** add, edit or delete companies (with a check that their job board exists) and upload their logos.
- **Command center:** today's count and the way into everything else, in one place.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer

## Setup

```bash
git clone <this repository's URL>
cd jobsentry

# Backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp backend/.env.example backend/.env

# Frontend
cd frontend
npm install
cp .env.example .env
```

The defaults in both `.env` files work as they are. See
[backend/README.md](backend/README.md#configuration) for every setting.

## Running it

In one terminal, start the API (from `backend/`):

```bash
python -m jobsentry.api            # http://127.0.0.1:8000, docs at /docs
```

In another, start the web app (from `frontend/`):

```bash
npm run dev                        # http://localhost:5173
```

Open http://localhost:5173, press **Be the first to apply**, then **Sources**, then
**Fetch all jobs**. To stop everything, press Ctrl+C in both terminals; this also
stops the monitor.

The backend also has a command line (from `backend/`):

```bash
python -m jobsentry sources                 # list available sources
python -m jobsentry list <source>           # fetch one company's jobs
python -m jobsentry show <source> <job_id>  # one job's details
```

## Email alerts (optional)

The monitor can email you through any SMTP server, such as your own Gmail
account. Add the server's details to `backend/.env` (see
[backend/README.md](backend/README.md#monitor-and-alerts)), restart the API,
then send and confirm a test email from the Monitor page. For Gmail, use an
[app password](https://myaccount.google.com/apppasswords), not your normal
password. The password stays in `backend/.env`, which is git-ignored.

## Adding a company

Use **Manage sources, then Add source** in the web app, or add an entry to a JSON
catalog in `backend/jobsentry/sources/catalogs/`. Companies are data, not
code. See [backend/README.md](backend/README.md#adding-a-company) for the
steps, the rules for choosing sources, and the architecture.

Only add companies whose jobs are published through a public job board
API, and respect any site that refuses automated access.

## Where things live

| Folder | What's in it |
|---|---|
| `backend/` | Python: fetching, storage, the monitor, and the FastAPI API ([README](backend/README.md)) |
| `frontend/` | React + TypeScript web app ([README](frontend/README.md)) |
| `backend/data/` | Saved jobs and monitor state, created on first run (git-ignored) |

## Licence

Job Sentry is released under the [MIT License](LICENSE). It isn't
affiliated with, endorsed by or sponsored by any company it lists, or by
Ashby, Greenhouse, Lever or SmartRecruiters; company names and logos belong
to their owners. See the app's Terms and Privacy pages for details.