import os
from utils.media_utils import render_mp4

def node_make_video(state: dict) -> dict:
    """
    슬라이드 이미지와 오디오를 합쳐 mp4 영상 제작
    입력:
        - state["slide_image"][0]: 슬라이드 이미지 경로
        - state["audio"]: mp3 오디오 경로
        - state["work_dir"]: 출력 폴더
    출력:
        - state["video_path"]: 생성된 mp4 파일 경로
    """
    slide_imgs = state.get("slide_image", [])
    audio_path = state.get("audio", "")
    work_dir = state.get("work_dir", "./")
    slide_index = state.get("slide_index", 0)

    if not slide_imgs or not os.path.exists(slide_imgs[0]):
        raise FileNotFoundError("슬라이드 이미지 파일이 없습니다.")
    if not os.path.exists(audio_path):
        raise FileNotFoundError("오디오 파일이 없습니다.")

    os.makedirs(work_dir, exist_ok=True)
    video_filename = f"slide{slide_index}_lecture.mp4"
    out_mp4 = os.path.join(work_dir, video_filename)

    render_mp4(
        image_path=slide_imgs[0],
        audio_path=audio_path,
        out_mp4=out_mp4
    )

    print(f"[VIDEO] 생성 완료: {out_mp4}")
    state["video_path"] = out_mp4
    return state
