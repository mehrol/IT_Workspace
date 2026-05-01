from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    videos: Mapped[list["Video"]] = relationship(back_populates="category")


class Playlist(Base):
    __tablename__ = "playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    videos: Mapped[list["Video"]] = relationship(back_populates="playlist")


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(220), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    keywords: Mapped[str] = mapped_column(String(500), nullable=True, index=True)
    video_type: Mapped[str] = mapped_column(String(20), index=True)
    source_path: Mapped[str] = mapped_column(String(500))
    poster_path: Mapped[str] = mapped_column(String(500), nullable=True)
    hls_path: Mapped[str] = mapped_column(String(500), nullable=True)
    processing_status: Mapped[str] = mapped_column(String(40), default="uploaded")
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped[Category] = relationship(back_populates="videos")
    playlist: Mapped[Playlist] = relationship(back_populates="videos")
    comments: Mapped[list["Comment"]] = relationship(back_populates="video", cascade="all, delete-orphan")
    likes: Mapped[list["Like"]] = relationship(back_populates="video", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)
    author: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    video: Mapped[Video] = relationship(back_populates="comments")


class Like(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(160), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    video: Mapped[Video] = relationship(back_populates="likes")


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    url: Mapped[str] = mapped_column(String(700))
    icon: Mapped[str] = mapped_column(String(60), nullable=True)
    image_path: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
