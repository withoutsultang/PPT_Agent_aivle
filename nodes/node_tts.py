import os
from openai import OpenAI
from utils.media_utils import ffprobe_duration

TTS_MODEL = "gpt-4o-mini-tts"
client = OpenAI()

def node_tts(state: dict) -> dict:
    """
    발표 스크립트를 TTS로 음성(mp3) 파일로 변환
    입력:
        - state["script"]: 발표 대본
        - state["prompt"]["voice"]: 음성 프리셋 (기본 alloy)
        - state["work_dir"]: 저장 경로
    출력:
        - state["audio"]: mp3 경로
    """
    script = state.get("script", "")
    prompt = state.get("prompt", {}) or {}
    voice = prompt.get("voice", "alloy")
    work_dir = state.get("work_dir", "./")

    if not script.strip():
        raise ValueError("state['script']가 비어 있습니다. node_generate_script 이후 실행하세요.")

    os.makedirs(work_dir, exist_ok=True)
    audio_path = os.path.join(work_dir, "narration.mp3")

    response = client.audio.speech.create(
        model=TTS_MODEL,
        voice=voice,
        input=script,
        response_format="mp3"
    )

    with open(audio_path, "wb") as f:
        f.write(response.read())

    duration = ffprobe_duration(audio_path)
    print(f"[TTS] 생성된 MP3 길이: {round(duration, 1)}초")

    state["audio"] = audio_path
    return state
