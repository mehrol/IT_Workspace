import shutil
import subprocess
from pathlib import Path


RENDITIONS = [
    ("480p", 854, 480, "1200k"),
    ("720p", 1280, 720, "2800k"),
    ("1080p", 1920, 1080, "5000k"),
]


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def transcode_to_hls(source: Path, output_dir: Path) -> Path | None:
    """Create multi-quality HLS playlists. Returns master playlist path."""
    if not ffmpeg_available():
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    variant_lines: list[str] = []

    for label, width, height, bitrate in RENDITIONS:
        rendition_dir = output_dir / label
        rendition_dir.mkdir(parents=True, exist_ok=True)
        playlist = rendition_dir / "index.m3u8"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(source),
            "-vf",
            f"scale=w='min({width},iw)':h='min({height},ih)':force_original_aspect_ratio=decrease",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-hls_time",
            "4",
            "-hls_playlist_type",
            "vod",
            "-hls_segment_filename",
            str(rendition_dir / "seg_%03d.ts"),
            str(playlist),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        variant_lines.extend(
            [
                f"#EXT-X-STREAM-INF:BANDWIDTH={bitrate.replace('k', '000')},RESOLUTION={width}x{height}",
                f"{label}/index.m3u8",
            ]
        )

    master = output_dir / "master.m3u8"
    master.write_text("#EXTM3U\n#EXT-X-VERSION:3\n" + "\n".join(variant_lines) + "\n", encoding="utf-8")
    return master
