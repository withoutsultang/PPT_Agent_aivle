"""Local Gradio interface. Start with `python app.py`."""

import logging
import os

import gradio as gr

from pipeline import run_pipeline

logger = logging.getLogger(__name__)


def display_quizzes(quizzes: list[dict]) -> str:
    if not quizzes:
        return "복습 퀴즈가 생성되면 여기에 표시됩니다."
    return "\n\n".join(
        f"### Q{i}. {quiz['question']}\n" + "\n".join(f"- {option}" for option in quiz["options"])
        for i, quiz in enumerate(quizzes, 1)
    )


def display_answers(quizzes: list[dict]) -> str:
    if not quizzes:
        return "먼저 강의를 생성해 주세요."
    return "\n\n".join(f"**Q{i}.** {quiz['answer']}" for i, quiz in enumerate(quizzes, 1))


def generate_state_and_run(pptx_file, tone, voice, style, target_duration_sec, speed):
    try:
        result = run_pipeline(pptx_file, tone, voice, style, target_duration_sec, speed)
    except ValueError as error:
        return None, gr.update(value=None, visible=False), "", "", [], str(error)
    except Exception as error:
        # Provider exceptions may contain request data. Show a concise error only.
        logger.error("Lecture generation stopped (%s).", type(error).__name__)
        return None, gr.update(value=None, visible=False), "", "", [], "강의를 완성하지 못했습니다. API 설정과 미디어 프로그램을 확인한 뒤 다시 시도해 주세요."
    video = result["final_video"]
    quizzes = result.get("quiz_set", [])
    status = f"{result['total_slides']}개 슬라이드의 강의 영상이 완성됐습니다."
    if result.get("notices"):
        status += "\n\n" + "\n".join(result["notices"])
    return video, gr.update(value=video, visible=True), display_quizzes(quizzes), "", quizzes, status


def clear_results():
    return None, gr.update(value=None, visible=False), "", "", [], "강의를 생성하고 있습니다. 슬라이드 수와 분량에 따라 시간이 걸릴 수 있습니다."


def build_demo() -> gr.Blocks:
    with gr.Blocks(theme=gr.themes.Soft(), title="AI 강사 Agent") as demo:
        gr.Markdown("# PPT를 하나의 강의로\n자료를 업로드하면 슬라이드 흐름에 맞춘 대본·음성·강의 영상과 복습 퀴즈를 만듭니다.")
        with gr.Row():
            with gr.Column(scale=1):
                upload = gr.File(label="강의 자료", file_types=[".pptx"], type="filepath")
                tone = gr.Dropdown(["친절하고 명료한 강의 톤", "열정적이고 에너지 넘치는 발표 톤", "차분하고 신뢰감 있는 설명 톤", "격식 있고 전문적인 톤"], value="친절하고 명료한 강의 톤", label="말투")
                voice = gr.Radio([("기본", "alloy"), ("이야기", "fable"), ("차분함", "onyx"), ("생동감", "verse"), ("부드러움", "coral")], value="alloy", label="목소리")
                style = gr.Dropdown(["예시와 핵심 요점 중심", "스토리텔링 중심", "데이터 기반 설명", "감정과 공감 중심"], value="예시와 핵심 요점 중심", label="설명 방식")
                with gr.Row():
                    duration = gr.Number(value=60, minimum=15, maximum=300, precision=0, label="페이지당 목표 분량(초)")
                    speed = gr.Slider(0.8, 2.0, value=1.0, step=0.1, label="음성 재생 속도")
                gr.Markdown("분량은 대본 작성 목표입니다. 음성은 AI로 생성됩니다.")
                run = gr.Button("강의 만들기", variant="primary")
                status = gr.Markdown()
            with gr.Column(scale=2):
                video = gr.Video(label="완성된 강의", interactive=False)
                download = gr.DownloadButton("영상 다운로드", visible=False)
                with gr.Accordion("복습 퀴즈", open=True):
                    quiz = gr.Markdown()
                    answers_button = gr.Button("정답 확인")
                    answers = gr.Markdown()
        quiz_state = gr.State([])
        outputs = [video, download, quiz, answers, quiz_state, status]
        run.click(clear_results, outputs=outputs, queue=False).then(
            generate_state_and_run, inputs=[upload, tone, voice, style, duration, speed],
            outputs=outputs, concurrency_limit=1,
        )
        answers_button.click(display_answers, inputs=quiz_state, outputs=answers)
    return demo


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_demo().queue().launch(server_name="127.0.0.1", share=os.getenv("GRADIO_SHARE", "false").lower() == "true")
