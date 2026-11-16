# Changelog

Notable changes to Job Sentry. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/): from 1.0.0 on, a change that
breaks existing catalogs, `.env` settings, saved data or the API raises the
major version.

## [Unreleased]

Nothing yet.

## [1.0.0] - 2026-11-16

The first public release.

### Added

- **Job sources** from companies' public job board APIs: Ashby, Greenhouse,
  Lever (global and EU instances) and SmartRecruiters. Companies are entries
  in JSON catalogs, one per platform, and can list several boards each.
- **Country matching** from free-text locations: country, US state and
  Canadian province names, shared and per-company hints, and optional
  "City, ST" codes. `scripts/missing_countries.py` finds locations that need
  a hint.
- **Fetch all jobs:** every company fetched in the background, several at a
  time (`JOBSENTRY_REFRESH_WORKERS`) in platform order
  (`JOBSENTRY_REFRESH_ORDER`), each saved as soon as it finishes, with live
  progress in the web app.
- **Today's jobs:** every company's jobs posted today in your time zone, in
  one list, read from `data/todays-jobs.json`, which is kept up to date on
  every save.
- **Filters** on every job list: keywords (title or team), countries, and
  newest or oldest first, kept in the page address.
- **Manage sources from the website:** add, edit and delete companies, check
  that their job boards exist before saving, and upload logos. Can be turned
  off with `JOBSENTRY_ALLOW_CATALOG_EDITS`.
- **Monitor:** fetches every company every 15, 30 or 45 minutes, or every 1
  to 24 hours, and alerts about new jobs matching a keyword filter with a
  chime on your computer and/or an email through your own SMTP server
  (verified with a two-step test email). Keeps the computer awake while on,
  and shows a live countdown to the next fetch.
- **Command center** page: today's job count, then Sources, Manage sources
  and Monitor.
- **Local API** (FastAPI) under `/api/v1`, with interactive documentation at
  `/docs`, and a command line (`python -m jobsentry`) for listing sources and
  fetching jobs.
- **Privacy and Terms pages,** and the MIT License.
