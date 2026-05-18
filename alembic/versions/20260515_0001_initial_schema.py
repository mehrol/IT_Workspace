"""initial schema

Revision ID: 20260515_0001
Revises: a692bd0d976b
Create Date: 2026-05-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260515_0001"
down_revision: Union[str, None] = "a692bd0d976b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categories_id"), "categories", ["id"], unique=False)
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=True)
    op.create_index(op.f("ix_categories_slug"), "categories", ["slug"], unique=True)

    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=700), nullable=False),
        sa.Column("icon", sa.String(length=60), nullable=True),
        sa.Column("image_path", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_channels_id"), "channels", ["id"], unique=False)

    op.create_table(
        "freelancer_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("role", sa.String(length=180), nullable=False),
        sa.Column("domain", sa.String(length=80), nullable=False),
        sa.Column("location", sa.String(length=160), nullable=True),
        sa.Column("experience", sa.String(length=120), nullable=True),
        sa.Column("skills", sa.String(length=500), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("email", sa.String(length=180), nullable=True),
        sa.Column("phone", sa.String(length=80), nullable=True),
        sa.Column("portfolio_url", sa.String(length=700), nullable=True),
        sa.Column("photo_path", sa.String(length=500), nullable=True),
        sa.Column("resume_path", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_freelancer_profiles_domain"), "freelancer_profiles", ["domain"], unique=False)
    op.create_index(op.f("ix_freelancer_profiles_id"), "freelancer_profiles", ["id"], unique=False)
    op.create_index(op.f("ix_freelancer_profiles_name"), "freelancer_profiles", ["name"], unique=False)
    op.create_index(op.f("ix_freelancer_profiles_role"), "freelancer_profiles", ["role"], unique=False)
    op.create_index(op.f("ix_freelancer_profiles_skills"), "freelancer_profiles", ["skills"], unique=False)

    op.create_table(
        "playlists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_playlists_id"), "playlists", ["id"], unique=False)
    op.create_index(op.f("ix_playlists_name"), "playlists", ["name"], unique=True)
    op.create_index(op.f("ix_playlists_slug"), "playlists", ["slug"], unique=True)

    op.create_table(
        "videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("keywords", sa.String(length=500), nullable=True),
        sa.Column("video_type", sa.String(length=20), nullable=False),
        sa.Column("source_path", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=900), nullable=True),
        sa.Column("direct_play_url", sa.String(length=900), nullable=True),
        sa.Column("embed_url", sa.String(length=900), nullable=True),
        sa.Column("external_platform", sa.String(length=60), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=900), nullable=True),
        sa.Column("poster_path", sa.String(length=500), nullable=True),
        sa.Column("hls_path", sa.String(length=500), nullable=True),
        sa.Column("caption_path", sa.String(length=500), nullable=True),
        sa.Column("processing_status", sa.String(length=40), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("playlist_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlists.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_videos_external_platform"), "videos", ["external_platform"], unique=False)
    op.create_index(op.f("ix_videos_id"), "videos", ["id"], unique=False)
    op.create_index(op.f("ix_videos_keywords"), "videos", ["keywords"], unique=False)
    op.create_index(op.f("ix_videos_title"), "videos", ["title"], unique=False)
    op.create_index(op.f("ix_videos_video_type"), "videos", ["video_type"], unique=False)

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("author", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_comments_id"), "comments", ["id"], unique=False)
    op.create_index(op.f("ix_comments_video_id"), "comments", ["video_id"], unique=False)

    op.create_table(
        "likes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_likes_fingerprint"), "likes", ["fingerprint"], unique=False)
    op.create_index(op.f("ix_likes_id"), "likes", ["id"], unique=False)
    op.create_index(op.f("ix_likes_video_id"), "likes", ["video_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_likes_video_id"), table_name="likes")
    op.drop_index(op.f("ix_likes_id"), table_name="likes")
    op.drop_index(op.f("ix_likes_fingerprint"), table_name="likes")
    op.drop_table("likes")
    op.drop_index(op.f("ix_comments_video_id"), table_name="comments")
    op.drop_index(op.f("ix_comments_id"), table_name="comments")
    op.drop_table("comments")
    op.drop_index(op.f("ix_videos_video_type"), table_name="videos")
    op.drop_index(op.f("ix_videos_title"), table_name="videos")
    op.drop_index(op.f("ix_videos_keywords"), table_name="videos")
    op.drop_index(op.f("ix_videos_id"), table_name="videos")
    op.drop_index(op.f("ix_videos_external_platform"), table_name="videos")
    op.drop_table("videos")
    op.drop_index(op.f("ix_playlists_slug"), table_name="playlists")
    op.drop_index(op.f("ix_playlists_name"), table_name="playlists")
    op.drop_index(op.f("ix_playlists_id"), table_name="playlists")
    op.drop_table("playlists")
    op.drop_index(op.f("ix_freelancer_profiles_skills"), table_name="freelancer_profiles")
    op.drop_index(op.f("ix_freelancer_profiles_role"), table_name="freelancer_profiles")
    op.drop_index(op.f("ix_freelancer_profiles_name"), table_name="freelancer_profiles")
    op.drop_index(op.f("ix_freelancer_profiles_id"), table_name="freelancer_profiles")
    op.drop_index(op.f("ix_freelancer_profiles_domain"), table_name="freelancer_profiles")
    op.drop_table("freelancer_profiles")
    op.drop_index(op.f("ix_channels_id"), table_name="channels")
    op.drop_table("channels")
    op.drop_index(op.f("ix_categories_slug"), table_name="categories")
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_id"), table_name="categories")
    op.drop_table("categories")
