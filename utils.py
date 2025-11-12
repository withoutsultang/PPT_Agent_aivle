# utils.py

import os, re, subprocess, base64, mimetypes, shlex
from typing import List
from pathlib import Path
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.shapes import PP_PLACEHOLDER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from difflib import SequenceMatcher

# ===============================
# 🔹 텍스트 처리 유틸리티
# ===============================

def clean_text(s: str) -> str:
    """공백(줄바꿈 포함)을 하나로 통일하고 앞뒤 공백 제거"""
    return re.sub(r"\\s+", " ", s).strip()

def split_sents(t: str) -> List[str]:
    """긴 문자열을 문장 단위로 분리"""
    parts = re.split(r'([\.?!])', t)
    merged = []
    for i in range(0, len(parts)-1, 2):
        sent = (parts[i] + parts[i+1]).strip()
        if sent: merged.append(sent)
    if len(parts) % 2 == 1 and parts[-1].strip():
        merged.append(parts[-1].strip())
    return [s for s in merged if s]

# ===============================
# 🔹 미디어/FFmpeg 유틸리티
# ===============================

def ffprobe_duration(path: str) -> float:
    """오디오/비디오 파일의 길이(초)를 계산"""
    try:
        out = subprocess.check_output([
            "ffprobe","-v","error","-show_entries","format=duration",
            "-of","default=noprint_wrappers=1:nokey=1", path]).decode().strip()
        return float(out)
    except Exception as e:
        print(f"[FFPROBE 오류] 파일 길이 측정 실패: {path}, {e}")
        return 0.0

def img_to_data_url(path: str) -> str:
    """로컬 이미지를 Data URL (base64)로 변환"""
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def render_mp4(image_path: str, audio_path: str, out_mp4: str,
               width=1920, height=1080):
    """배경 이미지와 오디오를 합쳐 MP4 영상 생성"""
    dur = ffprobe_duration(audio_path)
    if dur == 0:
        raise ValueError(f"오디오 파일 길이가 0입니다: {audio_path}")
        
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
          f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black")

    # FFmpeg 명령
    cmd = ["ffmpeg", "-y",
            "-loop", "1", "-i", image_path,   
            "-i", audio_path,                 
            "-t", str(dur),                   
            "-vf", vf,                        
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",        
            out_mp4]
    subprocess.check_call(cmd)

def concat_videos_ffmpeg(video_paths: List[str], out_path: str, reencode: bool=False):
    """여러 MP4 파일을 하나의 영상으로 병합"""
    list_path = out_path + ".txt"
    with open(list_path, "w", encoding="utf-8") as f:
        for v in video_paths:
            # 절대 경로 사용
            f.write(f"file '{os.path.abspath(v)}'\\n") 
    if reencode:
        cmd = [
            "ffmpeg","-y","-safe","0","-f","concat","-i",list_path,
            "-vf","format=yuv420p",
            "-c:v","libx264","-preset","veryfast",
            "-c:a","aac","-b:a","192k",
            out_path
        ]
    else:
        # reencode=False (copy)를 사용하면 매우 빠르지만, 입력 파일의 메타데이터 불일치 시 실패 가능성이 있음
        cmd = ["ffmpeg","-y","-safe","0","-f","concat","-i",list_path,"-c","copy",out_path]
    subprocess.check_call(cmd)

def export_slide_as_png(state: dict, dpi: int = 220) -> dict:
    """PPTX 슬라이드를 PNG 이미지로 변환 (PDF 중간 변환 방식)"""
    work_dir = Path(state["work_dir"]).expanduser().resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    pptx = Path(state["pptx_path"]).expanduser().resolve()
    if not pptx.exists():
        raise FileNotFoundError(f"PPTX 없음: {pptx}")

    idx = int(state.get("slide_index", 0)) 
    page_no = idx + 1
    out_prefix = work_dir / "slide_img"

    env = os.environ.copy()
    env.update({"LANG": "ko_KR.UTF-8", "LC_ALL": "ko_KR.UTF-8"})

    # --- 1️⃣ PPT → PDF (한 번만 변환) ---
    pdf_path = work_dir / f"{pptx.stem}.pdf"
    if not pdf_path.exists():
        lo_cmd = ["soffice","--headless","-env:UserInstallation=file:///tmp/lo_profile","--convert-to","pdf:impress_pdf_Export","--outdir", str(work_dir), str(pptx)]
        res_pdf = subprocess.run(lo_cmd, capture_output=True, text=True, env=env)
        if res_pdf.returncode != 0:
            raise RuntimeError(f"PPTX → PDF 변환 실패: {res_pdf.stderr}")

    # --- 2️⃣ PDF → PNG (슬라이드별 추출) ---
    png_path = Path(f"{out_prefix}-{page_no}.png")
    ppm_cmd = ["pdftoppm", "-f", str(page_no), "-l", str(page_no), "-png", "-r", str(dpi), str(pdf_path), str(out_prefix)]
    res2 = subprocess.run(ppm_cmd, capture_output=True, text=True, env=env)
    if res2.returncode != 0:
        print(f"[경고] pdftoppm 변환 실패: {res2.stderr}")

    if not png_path.exists():
        raise FileNotFoundError(f"슬라이드 {page_no} PNG 변환 실패: {png_path}")

    # --- 3️⃣ 변환 후 PDF 삭제 (선택적) ---
    try:
        if pdf_path.exists():
            os.remove(pdf_path)
    except Exception as e:
        print(f"[경고] PDF 삭제 실패: {e}")

    # --- 4️⃣ 최종 PNG 경로 반환 ---
    state["slide_image"] = str(png_path)
    return state