# app.py

import os, requests, time, shutil, re, textwrap, subprocess, json, base64, mimetypes
from pathlib import Path
from typing import List, Dict, Optional, TypedDict, Any
from openai import OpenAI
import gradio as gr
from langgraph.graph import StateGraph, END
import os.path as p
from urllib.parse import urlparse
from difflib import SequenceMatcher

# 🧩 NOTE: 실제 GitHub에 올릴 때는 이 파일을 포함한 모든 파일을 import 하도록 구조를 잡아야 합니다.
# 현재는 Colab 환경에서 하나의 파일로 통합하여 실행하는 방식에 맞게 재구성했습니다.
from agent_nodes import State, node_parse_all, node_tool_search, node_generate_page_content, node_generate_script, node_tts, node_make_video, node_accumulate_and_step, router_continue_or_done, node_concat, node_generate_quiz, LLM_MODEL, TTS_MODEL, client

# --- Graph Compilation ---
builder = StateGraph(State)
builder.add_node("parse_ppt", node_parse_all)
builder.add_node("tool_search", node_tool_search)
builder.add_node("gen_page_content", node_generate_page_content)
builder.add_node("gen_script", node_generate_script)
builder.add_node("tts", node_tts)
builder.add_node("make_video", node_make_video)
builder.add_node("accumulate", node_accumulate_and_step)
builder.add_node("concat", node_concat)
builder.add_node("make_quiz", node_generate_quiz)

builder.add_conditional_edges("accumulate", router_continue_or_done, {
    "continue": "tool_search",
    "done": "concat"
})

builder.set_entry_point("parse_ppt")
builder.add_edge("parse_ppt", "tool_search")
builder.add_edge("tool_search", "gen_page_content")
builder.add_edge("gen_page_content", "gen_script")
builder.add_edge("gen_script", "tts")
builder.add_edge("tts", "make_video")
builder.add_edge("make_video", "accumulate")
builder.add_edge("concat", "make_quiz")
builder.add_edge("make_quiz", END)

app = builder.compile()


# --- Gradio Wrapper Functions ---

def generate_state_and_run(pptx_file, tone, voice, style, target_duration_sec, speed):
    # API Key 로딩 (Gradio 환경에서 재실행 방지)
    # NOTE: GitHub에서는 이 부분이 환경 변수 설정으로 대체되어야 합니다.
    if not os.getenv('OPENAI_API_KEY'):
        return None, None, "API 키가 설정되지 않았습니다.", []
        
    # 작업 디렉터리 설정
    WORK_DIR = os.path.join("./gradio_output", f"run-{int(time.time())}")
    MEDIA_DIR = os.path.join(WORK_DIR, "media")
    SLIDES_DIR = os.path.join(WORK_DIR, "slides")

    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    os.makedirs(SLIDES_DIR, exist_ok=True)

    # 임시 파일 경로 설정 및 복사
    uploaded_file_path = pptx_file.name # Gradio File 객체의 name 속성이 파일 경로
    pptx_path = os.path.join(WORK_DIR, os.path.basename(uploaded_file_path))
    shutil.copy(uploaded_file_path, pptx_path)
    
    # State 초기화 및 설정
    USER_PROMPT = {
        "tone": tone,
        "voice": voice,
        "style": style,
        "target_duration_sec": int(target_duration_sec),
        "speed": float(speed)
    }

    state = {
        "pptx_path": pptx_path,
        "work_dir": WORK_DIR,
        "prompt": USER_PROMPT,
        "slide_index": 0
    }

    # 실제 Agent 그래프(app) 실행
    final_state = app.invoke(state, config={"recursion_limit": 100})

    final_video = final_state.get("final_video", None)
    quiz_set = final_state.get("quiz_set", [])
    quiz_md = display_quizzes(quiz_set)

    # Gradio는 File 객체나 경로를 반환해야 다운로드가 가능
    if final_video and os.path.exists(final_video):
        return final_video, final_video, quiz_md, quiz_set
    else:
        return None, None, "❌ 영상 제작에 실패했습니다. (로그 확인 필요)", []


def display_quizzes(quiz_set):
    """퀴즈 목록을 Markdown 형태로 포맷팅"""
    if not quiz_set:
        return "❌ 생성된 퀴즈가 없습니다."
    md = "## 🧠 복습 퀴즈\\n\\n"
    for i, q in enumerate(quiz_set, 1):
        md += f"**Q{i}. {q['question']}**\\n"
        for opt in q[\"options\"]:
            md += f"- {opt}\\n"
        md += "\\n"
    return md

def display_answers(quiz_set):
    """정답을 Markdown 형태로 포맷팅"""
    if not quiz_set:
        return "❌ 퀴즈 데이터가 없습니다."
    md = "## ✅ 정답 보기\\n\\n"
    for i, q in enumerate(quiz_set, 1):
        md += f"**Q{i}.** **{q['answer']}**\\n"
    return md


# --- Gradio Interface ---
tone_choices = ["친절하고 명료한 강의 톤", "열정적이고 에너지 넘치는 발표 톤", "차분하고 신뢰감 있는 설명 톤", "격식 있고 전문적인 톤"]
voice_choices = ["교육·온라인 수업용 -alloy", "감정 전달 중심 -fable", "기술 세미나용 -onyx", "홍보·SNS용 -verse", "명상·상담용 -coral"]
style_choices = ["예시와 핵심 요점 중심", "스토리텔링 중심", "데이터 기반 설명", "감정과 공감 중심"]


with gr.Blocks(theme=\"soft\", title=\"🎬 AI 슬라이드 강의 생성기\") as demo:
    gr.Markdown("## 🎬 AI 슬라이드 강의 생성기")
    gr.Markdown("PPTX를 업로드하고, 말투·목소리·스타일·속도를 선택한 뒤 **실행**을 누르면 AI가 자동으로 강의 영상을 생성합니다.")

    # 내부 상태 저장용
    quiz_state = gr.State([])

    # 입력 영역
    with gr.Row():
        inp_ppt = gr.File(label=\"🎞️ PPTX 파일 업로드\", file_types=[\".pptx\"], type=\"filepath\")

    with gr.Row():
        inp_tone  = gr.Radio(label=\"🗣️ 말투 (tone)\", choices=tone_choices, value=\"친절하고 명료한 강의 톤\")
        inp_voice = gr.Radio(label=\"🎤 목소리 (voice)\", choices=voice_choices, value=\"교육·온라인 수업용 -alloy\")

    with gr.Row():
        inp_style = gr.Radio(label=\"🧩 스타일 (style)\", choices=style_choices, value=\"예시와 핵심 요점 중심\")
        inp_duration = gr.Number(label=\"📄 페이지 당 목표 시간 (초)\", value=60, precision=0)
        inp_speed = gr.Slider(
            label=\"🎚️ 음성 속도 (Speed)\",
            minimum=0.8, maximum=2.0, step=0.1, value=1.0, info=\"음성 재생 속도를 조절하세요 (0.8x~2.0x)\"
        )

    run_btn = gr.Button("🚀 실행", variant=\"primary\")

    # 출력 구역
    with gr.Row():
        out_video = gr.Video(label=\"📽️ 최종 동영상 미리보기\", interactive=False)
        quiz_md = gr.Markdown(label=\"🧠 복습 퀴즈\", value=\"(퀴즈가 여기에 표시됩니다.)\")

    out_download = gr.DownloadButton(label=\"💾 동영상 다운로드\", visible=False)

    # ✅ 정답 보기 추가
    show_answer_btn = gr.Button("✅ 정답 보기", variant=\"secondary\")
    out_answer_md = gr.Markdown(label=\"정답\", value=\"(정답을 보려면 버튼을 누르세요)\")
    
    # 버튼 연결
    run_btn_outputs = [out_video, out_download, quiz_md, quiz_state]
    run_btn.click(
        fn=generate_state_and_run,
        inputs=[inp_ppt, inp_tone, inp_voice, inp_style, inp_duration, inp_speed],
        outputs=run_btn_outputs
    ).then(
        # 다운로드 버튼 활성화 (visibility 속성 업데이트 필요)
        lambda x: gr.update(value=x, visible=True),
        inputs=out_download,
        outputs=out_download
    )

    show_answer_btn.click(
        fn=display_answers,
        inputs=[quiz_state],
        outputs=[out_answer_md]
    )

if __name__ == '__main__':
    demo.launch(share=True)