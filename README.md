# Tech Video Hub

A FastAPI web app for a tech-only video portfolio/channel hub. It supports owner-only video link publishing, shorts, long videos, playlists, public comments, likes, share links, searchable videos, and social/channel links with large icons or custom images.

## Recommended Production Stack

- **Database:** PostgreSQL.
- **Video storage:** not required for YouTube/Instagram links. Store only metadata and optional poster images.
- **Poster/profile storage:** S3-compatible object storage such as AWS S3, Cloudflare R2, or MinIO for uploaded images and resumes.
- **Delivery:** use the original platform players for YouTube/Instagram playback.

This starter stores optional images under `media/` locally and uses PostgreSQL.

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/tech_video_hub"
# Optional when your maintenance database is not named postgres:
# $env:POSTGRES_MAINTENANCE_DB="postgres"
$env:OWNER_PASSWORD="change-this-password"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

At startup the app connects to the PostgreSQL server, creates the database from `DATABASE_URL` when it is missing, and runs pending Alembic migrations. On later starts, Alembic sees the existing schema revision and leaves it unchanged.

## Use Supabase PostgreSQL

Copy the database connection string from Supabase Dashboard -> Project Settings -> Database. Use the SQLAlchemy/Psycopg 3 form below, keep the database name from Supabase (usually `postgres`), and URL-encode special characters in the password such as `@` as `%40`.

```powershell
$env:DATABASE_URL="postgresql+psycopg://postgres.<project-ref>:<url-encoded-password>@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres?sslmode=require"
$env:AUTO_CREATE_DATABASE="false"
$env:OWNER_PASSWORD="change-this-password"
uvicorn app.main:app --reload
```

`AUTO_CREATE_DATABASE=false` is recommended for hosted databases such as Supabase because the app should migrate the existing database, not try to create a new database on the server. With that setting, startup still runs pending Alembic migrations automatically.

Do not commit real database credentials into `alembic.ini` or source files. Prefer environment variables for local work and your hosting provider's secret settings in production.

## Owner Login

Use the private workspace login path shared with the owner. The default owner password is read from `OWNER_PASSWORD`; if missing it falls back to `change-me-now`.

## Video Links

Add a YouTube, YouTube Shorts, Instagram Reel, Instagram post, or other embeddable video URL from Owner Studio. YouTube links get automatic thumbnails and can auto-advance to the next video when playback ends.

For direct in-site playback without a platform overlay, add a direct playable URL ending in `.mp4`, `.webm`, `.ogg`, `.mov`, or `.m3u8`. Instagram public post/reel URLs can be embedded, but Instagram may still show its own “Watch on Instagram” overlay inside the official iframe.
