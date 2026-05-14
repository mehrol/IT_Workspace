# Tech Video Hub

A FastAPI web app for a tech-only video portfolio/channel hub. It supports owner-only video link publishing, shorts, long videos, playlists, public comments, likes, share links, searchable videos, and social/channel links with large icons or custom images.

## Recommended Production Stack

- **Database:** PostgreSQL for production, SQLite for local development.
- **Video storage:** not required for YouTube/Instagram links. Store only metadata and optional poster images.
- **Poster/profile storage:** S3-compatible object storage such as AWS S3, Cloudflare R2, or MinIO for uploaded images and resumes.
- **Delivery:** use the original platform players for YouTube/Instagram playback.

This starter stores optional images under `media/` locally and uses SQLite by default.

## Run Locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OWNER_PASSWORD="change-this-password"
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Owner Login

Use the private workspace login path shared with the owner. The default owner password is read from `OWNER_PASSWORD`; if missing it falls back to `change-me-now`.

## Video Links

Add a YouTube, YouTube Shorts, Instagram Reel, Instagram post, or other embeddable video URL from Owner Studio. YouTube links get automatic thumbnails and can auto-advance to the next video when playback ends.

For direct in-site playback without a platform overlay, add a direct playable URL ending in `.mp4`, `.webm`, `.ogg`, `.mov`, or `.m3u8`. Instagram public post/reel URLs can be embedded, but Instagram may still show its own “Watch on Instagram” overlay inside the official iframe.
