# jobsentry frontend

React + TypeScript web UI for jobsentry, built with Vite. It reads everything from the local FastAPI backend.

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
| `npm run typecheck` | type-check only |

Requires Node.js 18 or newer. Commit `package-lock.json` after the first `npm install` so everyone gets the same versions.

## How it talks to the backend

Browser code calls relative URLs like `/api/v1/sources`. The Vite dev server forwards anything under `/api` to the backend (see `vite.config.ts`), so there's one origin and no CORS setup during development. The backend address defaults to `http://127.0.0.1:8000`; to change it, copy `.env.example` to `.env` and set `JOBSENTRY_API_URL` to match `backend/.env`.

## Pages

| URL | Page |
|---|---|
| `/` | name and "Get started" |
| `/sources` | every company, with job counts and last update |
| `/sources/:source` | one company's jobs, 50 per page (`?page=2`), with "Refresh jobs" |

Job titles link to the company's own posting for now.

## Structure

```
src/
├── main.tsx              entry: fonts, global CSS, React Query + router providers
├── App.tsx               routes
├── api/
│   ├── types.ts          response types, mirroring backend/jobsentry/api/schemas.py
│   ├── client.ts         fetch wrapper; every failure becomes an ApiError with a code
│   ├── endpoints.ts      one function per backend endpoint
│   └── queries.ts        React Query hooks (useSources, useJobs, useRefreshSource, ...)
├── components/           reusable pieces, each with its own .module.css
│   ├── Button.tsx        Button and ButtonLink (the typewriter-key style)
│   ├── TypedText.tsx     typing animation with cursor
│   ├── Layout.tsx        header + page column for every page except home
│   ├── PageHeader.tsx    title, intro line, back link, actions
│   ├── StatusMessage.tsx loading/empty messages and ErrorNotice
│   ├── SourceList.tsx    the sources index
│   ├── JobList.tsx       a list of jobs
│   └── Pagination.tsx
├── pages/                one component per route
├── hooks/                useDocumentTitle, usePrefersReducedMotion
├── utils/format.ts       numbers, relative times, lists
└── styles/
    ├── tokens.css        every colour, size and space (light + dark)
    └── global.css        base element styles, focus ring, reduced motion
```

Data flows one way: **page → hook in `api/queries.ts` → function in `api/endpoints.ts` → `request()` in `api/client.ts`**. Components never call `fetch` directly.

## Design

A carbon copy from a typewriter: text in carbon-paper blue on cool paper, set entirely in Courier Prime (self-hosted, so it works offline). Ribbon red is used only for the cursor and errors. The one animated moment is the name typing itself out on the homepage. Dark mode follows the system setting; reduced-motion settings show the name instantly and switch off transitions.

Change the look in `src/styles/tokens.css`. Components use CSS Modules, so class names never clash.

## Adding things

- **A page:** create it in `pages/`, then add a `<Route>` in `App.tsx`. Wrap it in the existing `<Layout>` route to get the header.
- **A backend call:** add the response type to `api/types.ts`, a function to `api/endpoints.ts`, and a hook to `api/queries.ts`. Keep query keys under `["sources", ...]` so refreshing a source updates them.
- **An error message:** the backend's error `code` reaches the UI unchanged; add a hint for it in `hintFor()` in `components/StatusMessage.tsx`.
