# Tech Video Hub

A FastAPI web app for a tech-only video portfolio/channel hub. It supports owner-only uploads, shorts, long videos, playlists, public comments, likes, share links, searchable videos, and social/channel links with large icons or custom images.

## Recommended Production Stack

- **Database:** PostgreSQL for production, SQLite for local development.
- **Video storage:** S3-compatible object storage such as AWS S3, Cloudflare R2, or MinIO. Keep only metadata in the database.
- **Video processing:** FFmpeg worker queue in production, ideally Celery/RQ + Redis, generating adaptive HLS renditions.
- **Delivery:** CDN in front of video files.

This starter stores files under `media/` locally and uses SQLite by default.

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

Visit `/admin/login`. The default owner password is read from `OWNER_PASSWORD`; if missing it falls back to `change-me-now`.

## Adaptive Video Quality

If `ffmpeg` is installed, uploads are compressed into HLS renditions up to 480p, 720p, and 1080p. The player uses automatic network-based quality by default and exposes quality options. If FFmpeg is not available, the original upload is still playable.
