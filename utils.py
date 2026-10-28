"""Text and media utilities shared by the lecture pipeline."""

import base64
import math
import mimetypes
import re
import shutil
import subprocess
from pathlib import Path


def clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def split_sents(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]


def require_media_tools() -> None:
    missing = [name for name in ("soffice", "pdftoppm", "ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        raise RuntimeError("필요한 프로그램을 설치하세요: " + ", ".join(missing))


def ffprobe_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True, timeout=30,
    )
    duration = float(result.stdout.strip())
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("미디어 길이를 확인할 수 없습니다.")
    return duration


def img_to_data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(Path(path).read_bytes()).decode('ascii')}"


def render_mp4(image_path: str, audio_path: str, out_mp4: str,
               width: int = 1920, height: int = 1080) -> None:
    if width < 2 or height < 2:
        raise ValueError("영상 크기는 2픽셀 이상이어야 합니다.")
    width, height = width // 2 * 2, height // 2 * 2
    duration = ffprobe_duration(audio_path)
    Path(out_mp4).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", str(image_path),
         "-i", str(audio_path), "-t", str(duration),
         "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black",
         "-r", "25", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-af", "aresample=async=1:first_pts=0", "-movflags", "+faststart", str(out_mp4)],
        check=True, capture_output=True, timeout=max(120, duration * 8),
    )


def concat_videos_ffmpeg(video_paths: list[str], out_path: str, reencode: bool = True) -> None:
    if not video_paths or any(not Path(p).is_file() for p in video_paths):
        raise ValueError("병합할 영상 파일을 모두 확인해 주세요.")
    output = Path(out_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    listing = output.with_suffix(".ffconcat")
    # FFconcat uses its own quoting rules, even though no shell is involved.
    listing.write_text("ffconcat version 1.0\n" + "".join(
        "file '" + str(Path(p).resolve()).replace("'", "'\\''") + "'\n" for p in video_paths
    ), encoding="utf-8")
    command = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing)]
    if reencode:
        command += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-ar", "48000", "-ac", "2", "-af", "aresample=async=1:first_pts=0"]
    else:
        command += ["-c", "copy"]
    subprocess.run(command + ["-movflags", "+faststart", str(output)],
                   check=True, capture_output=True, timeout=1800)
    ffprobe_duration(str(output))


def export_slide_as_png(state: dict, dpi: int = 150) -> dict:
    """Convert PPTX to PDF once per job and render the requested page."""
    directory = Path(state["work_dir"]).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    pptx = Path(state["pptx_path"]).resolve()
    if not pptx.is_file():
        raise FileNotFoundError("PPTX 파일을 찾을 수 없습니다.")
    index = int(state.get("slide_index", 0))
    if index < 0:
        raise ValueError("슬라이드 번호가 올바르지 않습니다.")
    pdf = directory / f"{pptx.stem}.pdf"
    if not pdf.is_file():
        profile = (directory / "lo-profile").as_uri()
        subprocess.run(
            ["soffice", "--headless", f"-env:UserInstallation={profile}",
             "--convert-to", "pdf:impress_pdf_Export", "--outdir", str(directory), str(pptx)],
            check=True, capture_output=True, timeout=180,
        )
        if not pdf.is_file():
            raise RuntimeError("PPTX를 PDF로 변환하지 못했습니다.")
    prefix = directory / f"slide-{index + 1:03d}"
    png = prefix.with_suffix(".png")
    if not png.is_file():
        subprocess.run(
            ["pdftoppm", "-f", str(index + 1), "-l", str(index + 1), "-singlefile",
             "-png", "-r", str(dpi), str(pdf), str(prefix)],
            check=True, capture_output=True, timeout=120,
        )
    if not png.is_file():
        raise RuntimeError(f"슬라이드 {index + 1}의 이미지를 만들지 못했습니다.")
    return {**state, "slide_image": str(png)}
