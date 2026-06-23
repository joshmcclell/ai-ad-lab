"""
Assemble final TikTok video from Higgsfield clips: stitch -> music ->
captions/text overlay -> export 1080x1920 @30fps. Wraps the ffmpeg binary.

Requires ffmpeg installed on the system (`ffmpeg -version` should work).

This is intentionally simple and dependency-light. For animated word-by-word
captions, consider a captioning service or a library like `captacity`; here we
burn in a static-per-segment subtitle from an .srt you provide or auto-build.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from .config import settings


def _run(args: list[str]) -> None:
    subprocess.run(args, check=True, capture_output=True)


def concat_clips(clips: list[str | Path], out_path: str | Path) -> Path:
    """Concatenate clips losslessly via the ffmpeg concat demuxer."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    listing = out_path.with_suffix(".txt")
    listing.write_text("".join(f"file '{Path(c).resolve()}'\n" for c in clips))
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
          "-c", "copy", str(out_path)])
    listing.unlink(missing_ok=True)
    return out_path


def finalize(video_in: str | Path, out_path: str | Path, *,
             music: str | Path | None = None,
             srt_captions: str | Path | None = None,
             music_volume: float = 0.25) -> Path:
    """
    Normalize to vertical spec, optionally mix music and burn captions.

    music         : path to a LICENSED audio file (see docs/COMPLIANCE.md).
    srt_captions  : path to an .srt file; burned in as styled subtitles.
    """
    v = settings()["video"]
    w, h = v["resolution"].split("x")
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Scale + pad to exact 9:16, set fps.
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,"
          f"crop={w}:{h},fps={v['fps']}")
    if srt_captions:
        srt = str(Path(srt_captions).resolve()).replace(":", r"\:")
        vf += (f",subtitles='{srt}':force_style="
               "'Fontsize=14,Outline=2,Alignment=2,MarginV=120,"
               "PrimaryColour=&H00FFFFFF,BorderStyle=1'")

    args = ["ffmpeg", "-y", "-i", str(video_in)]
    if music:
        args += ["-i", str(music)]

    args += ["-vf", vf]
    if music:
        # Lower music under any source audio; loop music to video length.
        args += ["-filter_complex",
                 f"[1:a]volume={music_volume}[m]",
                 "-map", "0:v", "-map", "[m]", "-shortest"]
    args += ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(out_path)]
    _run(args)
    return out_path
