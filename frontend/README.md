# Job Sentry frontend

The React + TypeScript web app for Job Sentry, built with Vite. Everything
it shows comes from the local FastAPI backend.

## Run it

The backend must be running first (from `backend/`: `python -m jobsentry.api`). Then:

```bash
cd frontend
npm install        # first time only
npm run dev        # http://localhost:5173
```

| Command | What it does |
|---|---|
| `npm run dev` | development server with hot reload |
| `npm run build` | type-check, then build to `dist/` |
| `npm run preview` | serve the built `dist/` locally |

Requires Node.js 18 or newer. `package-lock.json` is committed, so everyone gets the same versions.

## How it talks to the backend

Browser code calls relative URLs like `/api/v1/sources`. The Vite dev server forwards anything under `/api` to the backend (see `vite.config.ts`), so there's one origin and no CORS setup during development. The backend address defaults to `http://127.0.0.1:8000`; to change it, copy `.env.example` to `.env` and set `JOBSENTRY_API_URL` to match `backend/.env`.

Company logos are static files in `public/logos/<source name>.png` (or `.jpg`). Logos uploaded from "Manage sources" are saved there by the backend.

## Pages

| URL | Page |
|---|---|
| `/` | the name, "Why Job Sentry?", and "Be the first to apply" (to the command center) |
| `/why` | what Job Sentry is for |
| `/command-center` | today's jobs count, then Sources, Manage sources and Monitor |
| `/today` | every company's jobs posted today (in your time zone), with filters |
| `/sources` | every company as a card, "Fetch all jobs" with live progress, "Clear saved jobs" |
| `/sources/:source` | one company's jobs, 10 per page, with filters and "Refresh jobs" |
| `/manage` | every source, with Edit and Delete |
| `/manage/new`, `/manage/:name` | add or edit a source: check its board, upload a logo |
| `/monitor` | scheduled fetching, the keyword filter, sound and email alerts, fetch progress |
| `/privacy`, `/terms` | the privacy policy and terms of use |

Job lists keep their filters, order and page in the URL (`?q=engineer&country=US&sort=oldest&page=2`), so a view survives a reload and can be shared. Each job card links to the company's own posting.

## Structure

```
src/
├── main.tsx                 entry: fonts, global CSS, React Query + router providers
├── App.tsx                  routes, the background gradient, and the alert listener
├── config/site.ts           repository URL and the legal pages' "last updated" date
├── api/
│   ├── types.ts             response types, mirroring backend/jobsentry/api/schemas.py
│   ├── client.ts            fetch wrapper; every failure becomes an ApiError with a code
│   ├── endpoints.ts         one function per backend endpoint
│   └── queries.ts           React Query hooks (useSources, useAllJobs, useMonitor, ...)
├── components/              reusable pieces, each with its own .module.css
│   ├── Button.tsx           Button and ButtonLink
│   ├── Layout.tsx           header (with the monitor's live countdown), page column, footer
│   ├── AlertListener.tsx    polls the monitor every 15 s; shows the "new jobs" banner
│   ├── Countdown.tsx        live hh:mm:ss countdown
│   ├── TodayCallout.tsx     the Today's jobs tile on the command center
│   ├── SourceList.tsx       source cards; SourceLogo.tsx for logos or initials
│   ├── JobList.tsx          job cards (with company chips on /today)
│   ├── JobListToolbar.tsx   filters (JobFilters, CountryPicker) and sort (JobSortSelect)
│   ├── RefreshProgress.tsx  the "Fetch all jobs" progress panel
│   ├── BoardCheck.tsx       results of checking a board before saving a source
│   ├── PageHeader.tsx, Pagination.tsx, StatusMessage.tsx, SiteFooter.tsx
│   └── FeralGradient.js     the animated background (generated, kept as is)
├── pages/                   one component per route
├── hooks/useDocumentTitle.ts
├── utils/
│   ├── format.ts            numbers, dates, relative times, lists, countries, work modes
│   ├── dates.ts             the browser's time zone and local date
│   ├── jobFilters.ts        filter values and how they compare
│   ├── jobListView.ts       a job list's URL state (filters, sort, page)
│   └── logoVersion.ts       makes logos reload after one is uploaded or removed
└── styles/
    ├── tokens.css           every colour, size and space
    └── global.css           base element styles, focus ring, reduced motion, page fade
```

Data flows one way: **page → hook in `api/queries.ts` → function in `api/endpoints.ts` → `request()` in `api/client.ts`**. Components never call `fetch` directly.

Query keys for saved data live under `["sources", ...]`, so invalidating `["sources"]` after a fetch refreshes every list and count at once. The fetch progress (`["refresh-run"]`), catalog (`["catalog"]`) and monitor (`["monitor"]`) have their own keys.

## Design

Black ink on frosted glass over an animated rose-gold gradient, set in Cambria (with the free Caladea as its fallback, then Georgia), in a single regular weight: size and spacing carry the hierarchy. Buttons have a solid ink border and an offset shadow that they slide onto when pressed. Red is used only for errors. Reduced-motion settings switch off the animations.

Change the look in `src/styles/tokens.css`. Components use CSS Modules, so class names never clash.

## Adding things

- **A page:** create it in `pages/`, then add a `<Route>` inside the `<Layout>` route in `App.tsx` to get the header and footer.
- **A backend call:** add the response type to `api/types.ts`, a function to `api/endpoints.ts`, and a hook to `api/queries.ts`. Keep queries about saved data under `["sources", ...]` so fetches update them.
- **An error message:** the backend's error `code` reaches the UI unchanged; add a hint for it in `hintFor()` in `components/StatusMessage.tsx`.