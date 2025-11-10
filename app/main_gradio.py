import os, gradio as gr
from graph.build_graph import build_agent_graph
from typing import TypedDict, List, Dict
from openai import OpenAI

class State(TypedDict, total=False):
    pptx_path: str
    work_dir: str
    prompt: Dict
    slide_index: int
    slide_image: List[str]
    texts: List[str]
    tables: List[List[List[str]]]
    images: List[str]
    page_content: str
    script: str
    audio: str
    video_path: str

app = build_agent_graph(State)

def generate_state_and_run(pptx_file, slide_images, tone, voice, style, slide_index):
    WORK_DIR = os.path.abspath("./gradio_output")
    os.makedirs(WORK_DIR, exist_ok=True)
    state = {
        "pptx_path": pptx_file,
        "work_dir": WORK_DIR,
        "prompt": {"tone": tone, "voice": voice, "style": style},
        "slide_index": int(slide_index),
        "slide_image": [str(f) for f in slide_images],
    }
    state = app.invoke(state)
    return state.get("video_path", "")

tone_choices = ["친절하고 명료한 강의 톤", "열정적이고 에너지 넘치는 발표 톤", "차분하고 신뢰감 있는 설명 톤", "격식 있고 전문적인 톤"]
voice_choices = ["alloy", "fable", "verse", "coral", "onyx"]
style_choices = ["예시와 핵심 요점 중심", "스토리텔링 중심", "데이터 기반 설명", "감정과 공감 중심"]

demo = gr.Interface(
    fn=generate_state_and_run,
    inputs=[
        gr.File(label="🎞️ PPTX 파일 업로드", file_types=[".pptx"], type="filepath"),
        gr.Files(label="🖼️ PNG 슬라이드 이미지 업로드", file_types=[".png"], type="filepath"),
        gr.Radio(label="🗣️ 말투", choices=tone_choices, value="친절하고 명료한 강의 톤"),
        gr.Radio(label="🎤 목소리", choices=voice_choices, value="fable"),
        gr.Radio(label="🧩 스타일", choices=style_choices, value="예시와 핵심 요점 중심"),
        gr.Number(label="📄 슬라이드 인덱스", value=0, precision=0)
    ],
    outputs=gr.Video(label="📽️ 생성된 강의 영상", format="mp4"),
    title="🎬 AI 슬라이드 강의 생성기",
)
demo.launch(debug=True)
