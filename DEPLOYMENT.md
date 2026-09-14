# Deployment

Adeniran Street Clinic is two pieces of software in one repository:

| Piece | Location | Runtime |
| --- | --- | --- |
| Next.js 15 frontend | `frontend/` | Node (Vercel `@vercel/next`) |
| FastAPI backend | `app/`, entered through `api/index.py` | Python 3.12 (Vercel `@vercel/python`) |

There are two supported ways to ship it. Option A is recommended because it
gives you one domain, one deploy and no CORS to configure.

---

## Option A (recommended): one Vercel project

The root `vercel.json` builds both halves and routes between them.

| Path | Served by |
| --- | --- |
| `/` and every other page | Next.js build from `frontend/` |
| `/api/*` | FastAPI function `api/index.py` |
| `/docs`, `/docs/oauth2-redirect` | FastAPI Swagger UI |
| `/openapi.json` | FastAPI OpenAPI schema |

### Steps

1. Push this repository to GitHub (or GitLab / Bitbucket).
2. In Vercel choose **Add New -> Project** and import the repository.
3. Leave **Root Directory** at the repository root. Do **not** set it to
   `frontend` - the root `vercel.json` needs to see both `frontend/` and
   `app/`. When Root Directory is the repository root, `frontend/vercel.json`
   is ignored; only the root `vercel.json` applies.
4. Leave the Framework Preset as **Other**. The `builds` entry for
   `frontend/package.json` is what tells Vercel to build Next.js.
5. Add the environment variables in the table below (Settings ->
   Environment Variables), for Production *and* Preview.
6. Deploy, then check `/`, `/api/health` and `/docs`.

### Environment variables

| Variable | Required | Value to use | Why |
| --- | --- | --- | --- |
| `CLINIC_SECRET_KEY` | Yes | A long random string, e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"` | Signs the JWTs. The code ships with the placeholder `adeniran-street-clinic-secret-key`; leaving it in place means anyone can forge a receptionist token. Change it. |
| `CLINIC_DATABASE_URL` | Yes in production | A managed Postgres URL, e.g. `postgresql://user:password@host/dbname` | See "Why SQLite will not do" below. |
| `NEXT_PUBLIC_API_URL` | Yes | `/api` | Makes the browser call the API on the same origin. Point it anywhere else and the deployed site talks to the wrong backend. Trailing slashes are stripped by `src/lib/api/client.ts`, so `/api/` is tolerated. Read at build time - change it and redeploy. |
| `CLINIC_CORS_ORIGINS` | Optional | `https://your-app.vercel.app` | Not needed for same-origin calls in this layout. Set it if another site calls the API. Comma separated. Preview URLs are already allowed by the built-in `https://.*\.vercel\.app` regex. |
| `CLINIC_SEED_ON_STARTUP` | Optional | `false` once you have real data | Defaults to `true`, which inserts the demo doctors and users on every cold start. Useful for a first demo, wrong for a live clinic. |
| `CLINIC_TOKEN_MINUTES` | Optional | `60` | Access token lifetime in minutes. |
| `CLINIC_JWT_ALGORITHM` | Optional | `HS256` | Leave alone unless you know you need to change it. |

### Why SQLite will not do

The Vercel filesystem is read-only apart from `/tmp`. The `clinic.db` file
committed next to the code therefore cannot be written to at all, and `/tmp`
is discarded whenever the serverless instance is recycled.

| `CLINIC_DATABASE_URL` | Result |
| --- | --- |
| unset (bundled `clinic.db`) | Reads work, every write fails - registrations and bookings error out. |
| `sqlite:////tmp/clinic.db` | Writes work until the instance is recycled, then the data is gone. Demo only. |
| `postgresql://...` (Neon, Supabase, Vercel Postgres, RDS) | Correct. Bookings and consultation notes persist. |

If you use Postgres, add the driver to `requirements.txt` (for example
`psycopg[binary]>=3.2`) so SQLAlchemy can connect.

### Notes on the routing

- Vercel forwards the original request path to the function, so
  `/api/patients/register` arrives at FastAPI as `/api/patients/register`
  even though the router declares `/patients/register`. `api/index.py` sets
  `app.root_path = "/api"` so Starlette strips the prefix. Do not remove
  that line, and do not add a duplicate `/api` prefix to the routers.
- The root `vercel.json` uses the version 2 `builds` + `routes` form because
  the Next.js app lives in a subdirectory. Do not add a `functions` key -
  Vercel rejects `functions` and `builds` together.
- `includeFiles: "app/**"` is what puts the FastAPI package inside the
  Python function bundle. Without it the import of `app.main` fails.

---

## Option B: Vercel for the frontend, backend elsewhere

Use this when you want a writable disk (a long-lived SQLite file, uploads,
background jobs) or a server that is not serverless.

| Half | Host | Setting |
| --- | --- | --- |
| Frontend | Vercel, **Root Directory = `frontend`** | Picks up `frontend/vercel.json` (framework `nextjs` plus security headers). |
| Backend | Render / Railway / Fly.io | Start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

### Steps

1. Deploy the backend first so you know its public origin, for example
   `https://clinic-api.onrender.com`. Install from `requirements.txt`, and
   set `CLINIC_SECRET_KEY` plus `CLINIC_DATABASE_URL` there.
2. In the Vercel project set Root Directory to `frontend`.
3. Set `NEXT_PUBLIC_API_URL` to the **full backend origin** with no trailing
   slash and no `/api` suffix - the routers live at the origin root:
   `https://clinic-api.onrender.com`.
4. On the backend set `CLINIC_CORS_ORIGINS` to your Vercel domain, e.g.
   `https://adeniran-clinic.vercel.app`. Comma-separate several values. The
   default `CLINIC_CORS_ORIGIN_REGEX` already covers `*.vercel.app` preview
   deployments, so custom domains are the ones you must add by hand.
5. Redeploy the frontend so the new `NEXT_PUBLIC_API_URL` is baked into the
   build.

In this layout the API is at the backend origin root: `/health`, `/docs`,
`/auth/token`, and `api/index.py` and the root `vercel.json` are unused.

---

## Local development

Two terminals, both started from the repository root.

### Backend (uv + uvicorn)

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

The API is then on `http://localhost:8000`, Swagger on
`http://localhost:8000/docs`. On the first run `CLINIC_SEED_ON_STARTUP`
defaults to `true`, so the demo doctors and users are created in `clinic.db`.

Without uv, the committed virtual environment works too:

```bash
.venv/Scripts/uvicorn app.main:app --reload --port 8000   # Windows
.venv/bin/uvicorn app.main:app --reload --port 8000       # macOS / Linux
```

### Frontend (bun)

```bash
cd frontend
cp .env.example .env.local     # NEXT_PUBLIC_API_URL=http://localhost:8000
bun install
bun run dev
```

The site is then on `http://localhost:3000`, which is already in the default
`CLINIC_CORS_ORIGINS` list, so no backend change is needed.

### Local environment summary

| Variable | Local value | Where it goes |
| --- | --- | --- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | `frontend/.env.local` |
| `CLINIC_SECRET_KEY` | anything | shell / backend env (default is fine locally) |
| `CLINIC_DATABASE_URL` | unset (uses `clinic.db`) | shell / backend env |
| `CLINIC_SEED_ON_STARTUP` | `true` | shell / backend env |

---

## Pre-deploy checklist

- [ ] `CLINIC_SECRET_KEY` is a fresh random value, not the default.
- [ ] `CLINIC_DATABASE_URL` points at a managed database (Option A).
- [ ] `NEXT_PUBLIC_API_URL` is `/api` (Option A) or the backend origin
      (Option B), with no trailing slash.
- [ ] `CLINIC_SEED_ON_STARTUP=false` before real patients are entered.
- [ ] `frontend` builds cleanly: `cd frontend && bun run build`.
- [ ] The app imports cleanly: `uv run python -c "import api.index"`.
- [ ] `/api/health` returns 200 and `/docs` renders after the first deploy.
