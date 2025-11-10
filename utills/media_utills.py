import subprocess, base64, mimetypes

def ffprobe_duration(path: str) -> float:
    out = subprocess.check_output([
        "ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1", path]).decode().strip()
    return float(out)

def img_to_data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def render_mp4(image_path: str, audio_path: str, out_mp4: str,
               width=1920, height=1080):
    dur = ffprobe_duration(audio_path)
    vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
    cmd = ["ffmpeg", "-y", "-loop", "1", "-i", image_path, "-i", audio_path,
           "-t", str(dur), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", out_mp4]
    subprocess.check_call(cmd)
