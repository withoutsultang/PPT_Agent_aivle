"""Build the graph and run one isolated PPTX-to-video job."""

import json
import math
import os
import shutil
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from pptx import Presentation

from agent_nodes import (
    State, node_parse_all, node_tool_search, node_generate_page_content,
    node_generate_script, node_tts, node_make_video, node_accumulate_and_step,
    router_continue_or_done, node_concat, node_generate_quiz,
)
from utils import ffprobe_duration, require_media_tools

load_dotenv()
MAX_SLIDES = 60


def build_graph():
    builder = StateGraph(State)
    nodes = {
        "parse_ppt": node_parse_all,
        "tool_search": node_tool_search,
        "gen_page_content": node_generate_page_content,
        "gen_script": node_generate_script,
        "tts": node_tts,
        "make_video": node_make_video,
        "accumulate": node_accumulate_and_step,
        "concat": node_concat,
        "make_quiz": node_generate_quiz,
    }
    for name, function in nodes.items():
        builder.add_node(name, function)
    builder.set_entry_point("parse_ppt")
    chain = list(nodes)[:7]
    for source, target in zip(chain, chain[1:]):
        builder.add_edge(source, target)
    builder.add_conditional_edges("accumulate", router_continue_or_done,
                                  {"continue": "tool_search", "done": "concat"})
    builder.add_edge("concat", "make_quiz")
    builder.add_edge("make_quiz", END)
    return builder.compile()


def resolve_upload(upload) -> Path:
    if upload is None:
        raise ValueError("PPTX 파일을 선택해 주세요.")
    value = upload if isinstance(upload, (str, os.PathLike)) else getattr(upload, "name", None)
    if not value:
        raise ValueError("업로드한 파일을 확인해 주세요.")
    path = Path(value).resolve()
    if path.suffix.lower() != ".pptx" or not path.is_file():
        raise ValueError("PPTX 형식의 파일을 선택해 주세요.")
    if path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("50MB 이하의 PPTX를 선택해 주세요.")
    return path


def run_pipeline(upload, tone: str = "친절하고 명료한 강의 톤", voice: str = "alloy",
                 style: str = "예시와 핵심 요점 중심", target_duration_sec: int = 60,
                 speed: float = 1.0) -> State:
    path = resolve_upload(upload)
    target = float(target_duration_sec)
    playback_speed = float(speed)
    if not math.isfinite(target) or not 15 <= target <= 300:
        raise ValueError("페이지당 목표 분량은 15~300초로 설정해 주세요.")
    if not math.isfinite(playback_speed) or not 0.8 <= playback_speed <= 2.0:
        raise ValueError("재생 속도는 0.8~2.0으로 설정해 주세요.")
    allowed_voices = {"alloy", "fable", "onyx", "verse", "coral"}
    selected_voice = voice.split("-")[-1].strip()
    if selected_voice not in allowed_voices:
        raise ValueError("지원하는 목소리를 선택해 주세요.")
    try:
        count = len(Presentation(str(path)).slides)
    except Exception as error:
        raise ValueError("PPTX를 열 수 없습니다. 암호를 해제한 파일로 다시 시도해 주세요.") from error
    if not 1 <= count <= MAX_SLIDES:
        raise ValueError(f"1~{MAX_SLIDES}장으로 구성된 PPTX를 선택해 주세요.")
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError(".env에 OPENAI_API_KEY를 설정한 뒤 실행해 주세요.")
    require_media_tools()
    root = Path(os.getenv("OUTPUT_DIR", "outputs")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="lecture-", dir=root))
    source = directory / "input.pptx"
    shutil.copy2(path, source)
    state: State = {
        "pptx_path": str(source), "work_dir": str(directory), "slide_index": 0,
        "prompt": {"tone": tone, "voice": selected_voice, "style": style,
                   "target_duration_sec": int(target), "speed": playback_speed},
    }
    result = build_graph().invoke(state, config={"recursion_limit": 8 * count + 10})
    final = result.get("final_video")
    if not final or not Path(final).is_file():
        raise RuntimeError("강의 영상이 생성되지 않았습니다. 실행 환경을 확인해 주세요.")
    # Save outputs and references without credentials or raw provider responses.
    manifest = {
        "slides": result["total_slides"], "prompt": result["prompt"],
        "video_duration_sec": ffprobe_duration(final),
        "video_files": [Path(p).name for p in result["video_paths"]],
        "quiz_count": len(result.get("quiz_set", [])), "notices": result.get("notices", []),
    }
    (directory / "result.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
