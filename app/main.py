import os
import re
import shutil
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Category, Channel, Comment, Like, Playlist, Video
from .video_processing import transcode_to_hls


BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / "media"
UPLOAD_DIR = MEDIA_DIR / "uploads"
POSTER_DIR = MEDIA_DIR / "posters"
CHANNEL_DIR = MEDIA_DIR / "channels"
HLS_DIR = MEDIA_DIR / "hls"

for directory in (UPLOAD_DIR, POSTER_DIR, CHANNEL_DIR, HLS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tech Video Hub")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

serializer = URLSafeSerializer(os.getenv("SECRET_KEY", "replace-this-secret-key"), salt="owner-session")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "change-me-now")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def media_url(path: str | None) -> str | None:
    if not path:
        return None
    return "/media/" + str(Path(path).relative_to(MEDIA_DIR)).replace("\\", "/")


templates.env.filters["media_url"] = media_url


def require_owner(request: Request):
    token = request.cookies.get("owner_session")
    try:
        if token and serializer.loads(token) == "owner":
            return True
    except BadSignature:
        pass
    raise HTTPException(status_code=303, headers={"Location": "/admin/login"})


def get_or_create_named(db: Session, model, name: str | None):
    if not name:
        return None
    clean = name.strip()
    if not clean:
        return None
    existing = db.scalar(select(model).where(func.lower(model.name) == clean.lower()))
    if existing:
        return existing
    item = model(name=clean, slug=slugify(clean))
    db.add(item)
    db.flush()
    return item


def save_upload(upload: UploadFile, folder: Path) -> Path | None:
    if not upload or not upload.filename:
        return None
    extension = Path(upload.filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{extension}"
    target = folder / safe_name
    with target.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)
    return target


def video_list_query(db: Session, search: str | None = None, video_type: str | None = None):
    query = select(Video)
    if video_type:
        query = query.where(Video.video_type == video_type)
    if search:
        needle = f"%{search.strip()}%"
        query = query.where(
            or_(
                Video.title.ilike(needle),
                Video.description.ilike(needle),
                Video.keywords.ilike(needle),
            )
        )
    return db.scalars(query.order_by(Video.created_at.desc())).all()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    shorts = video_list_query(db, search=q, video_type="short")
    long_videos = video_list_query(db, search=q, video_type="long")
    channels = db.scalars(select(Channel).where(Channel.is_active == True).order_by(Channel.created_at.desc())).all()
    categories = db.scalars(select(Category).order_by(Category.name)).all()
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "shorts": shorts,
            "long_videos": long_videos,
            "channels": channels,
            "categories": categories,
            "q": q or "",
        },
    )


@app.get("/videos", response_class=HTMLResponse)
def videos(request: Request, q: str | None = None, playlist: str | None = None, db: Session = Depends(get_db)):
    query = select(Video).where(Video.video_type == "long")
    if q:
        needle = f"%{q.strip()}%"
        query = query.where(or_(Video.title.ilike(needle), Video.description.ilike(needle), Video.keywords.ilike(needle)))
    if playlist:
        query = query.join(Playlist).where(Playlist.slug == playlist)
    videos_ = db.scalars(query.order_by(Video.created_at.desc())).all()
    playlists = db.scalars(select(Playlist).order_by(Playlist.name)).all()
    return templates.TemplateResponse(
        "videos.html",
        {"request": request, "videos": videos_, "playlists": playlists, "q": q or "", "active_playlist": playlist or ""},
    )


@app.get("/watch/{video_id}", response_class=HTMLResponse)
def watch(video_id: int, request: Request, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404)
    related = db.scalars(
        select(Video).where(Video.id != video.id, Video.video_type == video.video_type).order_by(Video.created_at.desc()).limit(8)
    ).all()
    sequence = db.scalars(select(Video).where(Video.video_type == video.video_type).order_by(Video.created_at.desc())).all()
    next_video = None
    for index, item in enumerate(sequence):
        if item.id == video.id and index + 1 < len(sequence):
            next_video = sequence[index + 1]
            break
    comments = db.scalars(select(Comment).where(Comment.video_id == video.id).order_by(Comment.created_at.desc())).all()
    like_count = db.scalar(select(func.count(Like.id)).where(Like.video_id == video.id)) or 0
    return templates.TemplateResponse(
        "watch.html",
        {
            "request": request,
            "video": video,
            "related": related,
            "comments": comments,
            "like_count": like_count,
            "next_video": next_video,
        },
    )


@app.post("/videos/{video_id}/comment")
def add_comment(video_id: int, author: str = Form(...), body: str = Form(...), db: Session = Depends(get_db)):
    if not db.get(Video, video_id):
        raise HTTPException(status_code=404)
    db.add(Comment(video_id=video_id, author=author[:120], body=body[:1200]))
    db.commit()
    return RedirectResponse(f"/watch/{video_id}", status_code=303)


@app.post("/videos/{video_id}/like")
def like_video(video_id: int, request: Request, db: Session = Depends(get_db)):
    if not db.get(Video, video_id):
        raise HTTPException(status_code=404)
    fingerprint = request.client.host if request.client else "unknown"
    exists = db.scalar(select(Like).where(Like.video_id == video_id, Like.fingerprint == fingerprint))
    if not exists:
        db.add(Like(video_id=video_id, fingerprint=fingerprint))
        db.commit()
    return RedirectResponse(f"/watch/{video_id}", status_code=303)


@app.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})


@app.post("/admin/login")
def login(response: Response, request: Request, password: str = Form(...)):
    if password != OWNER_PASSWORD:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Wrong owner password."}, status_code=401)
    redirect = RedirectResponse("/admin", status_code=303)
    redirect.set_cookie("owner_session", serializer.dumps("owner"), httponly=True, samesite="lax")
    return redirect


@app.post("/admin/logout")
def logout():
    redirect = RedirectResponse("/", status_code=303)
    redirect.delete_cookie("owner_session")
    return redirect


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, db: Session = Depends(get_db), owner: bool = Depends(require_owner)):
    videos_ = db.scalars(select(Video).order_by(Video.created_at.desc())).all()
    channels = db.scalars(select(Channel).order_by(Channel.created_at.desc())).all()
    return templates.TemplateResponse("admin.html", {"request": request, "videos": videos_, "channels": channels})


@app.post("/admin/upload")
def upload_video(
    title: str = Form(...),
    description: str = Form(""),
    keywords: str = Form(""),
    video_type: str = Form(...),
    category: str = Form(""),
    playlist: str = Form(""),
    file: UploadFile = File(...),
    poster: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    owner: bool = Depends(require_owner),
):
    if video_type not in {"short", "long"}:
        raise HTTPException(status_code=400, detail="Video type must be short or long.")
    source = save_upload(file, UPLOAD_DIR)
    poster_path = save_upload(poster, POSTER_DIR) if poster else None
    category_item = get_or_create_named(db, Category, category)
    playlist_item = get_or_create_named(db, Playlist, playlist) if video_type == "long" else None

    video = Video(
        title=title.strip(),
        description=description.strip(),
        keywords=keywords.strip(),
        video_type=video_type,
        source_path=str(source),
        poster_path=str(poster_path) if poster_path else None,
        category=category_item,
        playlist=playlist_item,
        processing_status="processing",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    try:
        master = transcode_to_hls(source, HLS_DIR / str(video.id))
        video.hls_path = str(master) if master else None
        video.processing_status = "ready" if master else "ready-original"
    except Exception:
        video.processing_status = "ready-original"
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/channels")
def add_channel(
    name: str = Form(...),
    url: str = Form(...),
    icon: str = Form("user"),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    owner: bool = Depends(require_owner),
):
    image_path = save_upload(image, CHANNEL_DIR) if image and image.filename else None
    db.add(Channel(name=name.strip(), url=url.strip(), icon=icon.strip() or "user", image_path=str(image_path) if image_path else None))
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/channels/{channel_id}/toggle")
def toggle_channel(channel_id: int, db: Session = Depends(get_db), owner: bool = Depends(require_owner)):
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404)
    channel.is_active = not channel.is_active
    db.commit()
    return RedirectResponse("/admin", status_code=303)
