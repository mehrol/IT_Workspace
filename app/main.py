import os
import re
import shutil
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeSerializer
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .database import get_db, initialize_database
from .models import Category, Channel, Comment, FreelancerProfile, Like, Playlist, Video


BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / "media"
UPLOAD_DIR = MEDIA_DIR / "uploads"
POSTER_DIR = MEDIA_DIR / "posters"
CHANNEL_DIR = MEDIA_DIR / "channels"
PROFILE_DIR = MEDIA_DIR / "profiles"
RESUME_DIR = MEDIA_DIR / "resumes"
CAPTION_DIR = MEDIA_DIR / "captions"
HLS_DIR = MEDIA_DIR / "hls"

for directory in (UPLOAD_DIR, POSTER_DIR, CHANNEL_DIR, PROFILE_DIR, RESUME_DIR, CAPTION_DIR, HLS_DIR):
    directory.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Tech Video Hub")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

serializer = URLSafeSerializer(os.getenv("SECRET_KEY", "replace-this-secret-key"), salt="owner-session")
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD", "change-me-now")


@app.on_event("startup")
def startup() -> None:
    initialize_database()


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
    raise HTTPException(status_code=303, headers={"Location": "/workspace-login"})


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


def delete_media_file(path: str | None):
    if not path:
        return
    try:
        target = Path(path).resolve()
        media_root = MEDIA_DIR.resolve()
        if target.is_file() and target.is_relative_to(media_root):
            target.unlink()
    except (OSError, ValueError):
        pass


def is_direct_media_url(value: str) -> bool:
    path = urlparse(value.strip()).path.lower()
    return path.endswith((".mp4", ".webm", ".ogg", ".mov", ".m3u8"))


def youtube_embed_url(video_id: str) -> str:
    return f"https://www.youtube-nocookie.com/embed/{video_id}?enablejsapi=1&rel=0&modestbranding=1&playsinline=1&controls=0"


def build_embed_details(video_url: str) -> dict[str, str | None]:
    clean_url = video_url.strip()
    parsed = urlparse(clean_url)
    host = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.strip("/")

    if is_direct_media_url(clean_url):
        return {
            "platform": "direct",
            "embed_url": None,
            "direct_play_url": clean_url,
            "thumbnail_url": None,
        }

    if host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        video_id = parse_qs(parsed.query).get("v", [""])[0]
        if not video_id and path.startswith(("shorts/", "embed/")):
            video_id = path.split("/")[1]
        if video_id:
            return {
                "platform": "youtube",
                "embed_url": youtube_embed_url(video_id),
                "direct_play_url": None,
                "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            }

    if host == "youtu.be":
        video_id = path.split("/")[0]
        if video_id:
            return {
                "platform": "youtube",
                "embed_url": youtube_embed_url(video_id),
                "direct_play_url": None,
                "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            }

    if "instagram.com" in host or host == "instagr.am":
        pieces = [piece for piece in path.split("/") if piece]
        if len(pieces) >= 2 and pieces[0] in {"p", "reel", "reels", "tv"}:
            content_type = "reel" if pieces[0] == "reels" else pieces[0]
            return {
                "platform": "instagram",
                "embed_url": f"https://www.instagram.com/{content_type}/{pieces[1]}/embed",
                "direct_play_url": None,
                "thumbnail_url": None,
            }

    return {"platform": "external", "embed_url": clean_url, "direct_play_url": None, "thumbnail_url": None}


def refresh_external_video_details(video: Video) -> bool:
    source_url = (video.source_url or video.source_path or "").strip()
    if not source_url:
        return False

    details = build_embed_details(source_url)
    changed = False
    if details["platform"] in {"youtube", "instagram", "direct"}:
        for field, value in {
            "embed_url": details["embed_url"],
            "external_platform": details["platform"],
            "thumbnail_url": details["thumbnail_url"],
        }.items():
            if getattr(video, field) != value:
                setattr(video, field, value)
                changed = True
        if details["direct_play_url"] and video.direct_play_url != details["direct_play_url"]:
            video.direct_play_url = details["direct_play_url"]
            changed = True

    return changed


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


def freelancer_list_query(db: Session, search: str | None = None, domain: str | None = None):
    query = select(FreelancerProfile).where(
        FreelancerProfile.is_active == True,
        func.lower(FreelancerProfile.domain).in_(["tech", "design"]),
    )
    if domain:
        query = query.where(func.lower(FreelancerProfile.domain) == domain.lower())
    if search:
        needle = f"%{search.strip()}%"
        query = query.where(
            or_(
                FreelancerProfile.name.ilike(needle),
                FreelancerProfile.role.ilike(needle),
                FreelancerProfile.domain.ilike(needle),
                FreelancerProfile.skills.ilike(needle),
                FreelancerProfile.bio.ilike(needle),
            )
        )
    return db.scalars(query.order_by(FreelancerProfile.created_at.desc())).all()


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
            "search_action": "/",
            "q": q or "",
        },
    )


@app.get("/shorts", response_class=HTMLResponse)
def shorts_page(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    shorts = video_list_query(db, search=q, video_type="short")
    return templates.TemplateResponse(
        "shorts.html",
        {"request": request, "shorts": shorts, "q": q or "", "search_action": "/shorts"},
    )


@app.get("/channels", response_class=HTMLResponse)
def channels_page(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    query = select(Channel).where(Channel.is_active == True)
    if q:
        needle = f"%{q.strip()}%"
        query = query.where(Channel.name.ilike(needle))
    channels = db.scalars(query.order_by(Channel.created_at.desc())).all()
    return templates.TemplateResponse(
        "channels.html",
        {"request": request, "channels": channels, "q": q or "", "search_action": "/channels"},
    )


@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "q": "", "search_action": "/"},
    )


@app.get("/freelancing", response_class=HTMLResponse)
def freelancing_page(request: Request, q: str | None = None, domain: str | None = None, db: Session = Depends(get_db)):
    clean_domain = domain if domain and domain.lower() in {"tech", "design"} else None
    freelancers = freelancer_list_query(db, search=q, domain=clean_domain)
    return templates.TemplateResponse(
        "freelancing.html",
        {
            "request": request,
            "freelancers": freelancers,
            "q": q or "",
            "active_domain": clean_domain or "",
            "search_action": "/freelancing",
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
        {
            "request": request,
            "videos": videos_,
            "playlists": playlists,
            "q": q or "",
            "active_playlist": playlist or "",
            "search_action": "/videos",
        },
    )


@app.get("/watch/{video_id}", response_class=HTMLResponse)
def watch(video_id: int, request: Request, db: Session = Depends(get_db)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404)
    if refresh_external_video_details(video):
        db.commit()
        db.refresh(video)
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


@app.get("/workspace-login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": "", "show_search": False})


@app.post("/workspace-login")
def login(response: Response, request: Request, password: str = Form(...)):
    if password != OWNER_PASSWORD:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Wrong owner password.", "show_search": False},
            status_code=401,
        )
    redirect = RedirectResponse("/admin", status_code=303)
    redirect.set_cookie("owner_session", serializer.dumps("owner"), httponly=True, samesite="lax")
    return redirect


@app.post("/admin/logout")
def logout():
    redirect = RedirectResponse("/", status_code=303)
    redirect.delete_cookie("owner_session")
    return redirect


@app.post("/admin/videos/{video_id}/delete")
def delete_video(video_id: int, db: Session = Depends(get_db), owner: bool = Depends(require_owner)):
    video = db.get(Video, video_id)
    if not video:
        raise HTTPException(status_code=404)
    for path in (video.poster_path, video.source_path, video.hls_path, video.caption_path):
        delete_media_file(path)
    db.delete(video)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, db: Session = Depends(get_db), owner: bool = Depends(require_owner)):
    videos_ = db.scalars(select(Video).order_by(Video.created_at.desc())).all()
    channels = db.scalars(select(Channel).order_by(Channel.created_at.desc())).all()
    freelancers = db.scalars(select(FreelancerProfile).order_by(FreelancerProfile.created_at.desc())).all()
    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "videos": videos_, "channels": channels, "freelancers": freelancers, "show_search": False},
    )


@app.post("/admin/upload")
def upload_video(
    title: str = Form(...),
    description: str = Form(""),
    keywords: str = Form(""),
    video_type: str = Form(...),
    category: str = Form(""),
    playlist: str = Form(""),
    video_url: str = Form(...),
    direct_play_url: str = Form(""),
    poster: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    owner: bool = Depends(require_owner),
):
    if video_type not in {"short", "long"}:
        raise HTTPException(status_code=400, detail="Video type must be short or long.")
    embed_details = build_embed_details(video_url)
    clean_direct_play_url = direct_play_url.strip() or embed_details["direct_play_url"]
    if clean_direct_play_url and not is_direct_media_url(clean_direct_play_url):
        raise HTTPException(status_code=400, detail="Direct play URL must end with .mp4, .webm, .ogg, .mov, or .m3u8.")
    poster_path = save_upload(poster, POSTER_DIR) if poster else None
    category_item = get_or_create_named(db, Category, category)
    playlist_item = get_or_create_named(db, Playlist, playlist) if video_type == "long" else None

    video = Video(
        title=title.strip(),
        description=description.strip(),
        keywords=keywords.strip(),
        video_type=video_type,
        source_path=video_url.strip(),
        source_url=video_url.strip(),
        direct_play_url=clean_direct_play_url,
        embed_url=embed_details["embed_url"],
        external_platform="direct" if clean_direct_play_url else embed_details["platform"],
        thumbnail_url=embed_details["thumbnail_url"],
        poster_path=str(poster_path) if poster_path else None,
        category=category_item,
        playlist=playlist_item,
        processing_status="linked",
    )
    db.add(video)
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


@app.post("/admin/channels/{channel_id}/delete")
def delete_channel(channel_id: int, db: Session = Depends(get_db), owner: bool = Depends(require_owner)):
    channel = db.get(Channel, channel_id)
    if not channel:
        raise HTTPException(status_code=404)
    delete_media_file(channel.image_path)
    db.delete(channel)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/freelancers")
def add_freelancer(
    name: str = Form(...),
    role: str = Form(...),
    domain: str = Form(...),
    location: str = Form(""),
    experience: str = Form(""),
    skills: str = Form(""),
    bio: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    portfolio_url: str = Form(""),
    photo: UploadFile | None = File(None),
    resume: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    owner: bool = Depends(require_owner),
):
    if domain.lower() not in {"tech", "design"}:
        raise HTTPException(status_code=400, detail="Freelancer domain must be Tech or Design.")
    photo_path = save_upload(photo, PROFILE_DIR) if photo and photo.filename else None
    resume_path = save_upload(resume, RESUME_DIR) if resume and resume.filename else None
    db.add(
        FreelancerProfile(
            name=name.strip(),
            role=role.strip(),
            domain=domain.strip(),
            location=location.strip(),
            experience=experience.strip(),
            skills=skills.strip(),
            bio=bio.strip(),
            email=email.strip(),
            phone=phone.strip(),
            portfolio_url=portfolio_url.strip(),
            photo_path=str(photo_path) if photo_path else None,
            resume_path=str(resume_path) if resume_path else None,
        )
    )
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/freelancers/{profile_id}/toggle")
def toggle_freelancer(profile_id: int, db: Session = Depends(get_db), owner: bool = Depends(require_owner)):
    profile = db.get(FreelancerProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404)
    profile.is_active = not profile.is_active
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@app.post("/admin/freelancers/{profile_id}/delete")
def delete_freelancer(profile_id: int, db: Session = Depends(get_db), owner: bool = Depends(require_owner)):
    profile = db.get(FreelancerProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404)
    delete_media_file(profile.photo_path)
    delete_media_file(profile.resume_path)
    db.delete(profile)
    db.commit()
    return RedirectResponse("/admin", status_code=303)
