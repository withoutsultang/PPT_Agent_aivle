# Step1_AI 강사 Agent v1.0

AI 강의 영상을 자동 생성하는 LangGraph 기반 Agent 시스템입니다.

## 🚀 기능
- PPT 슬라이드 분석 (텍스트, 표, 이미지 추출)
- LLM 기반 내용 요약 및 발표 대본 생성
- OpenAI TTS 음성 합성
- 이미지 + 음성 합성하여 영상 자동 제작
- Gradio 인터페이스를 통한 실행 UI

## 📁 디렉토리 구조

```bash
Step1_AI_강사_Agent_v1.0/
│
├── README.md
├── requirements.txt
│
├── config/
│   └── load_api_key.py
│
├── utils/
│   ├── text_utils.py
│   ├── media_utils.py
│   └── common_utils.py
│
├── nodes/
│   ├── node_parse_ppt.py
│   ├── node_generate_text.py
│   ├── node_generate_script.py
│   ├── node_tts.py
│   └── node_make_video.py
│
├── graph/
│   └── build_graph.py
│
├── app/
│   ├── main_gradio.py
│   └── main_colab_test.py
│
└── data/
    ├── sample1.pptx
    └── sample1.png



## ⚙️ 실행 환경
```bash
!apt-get -y install ffmpeg libreoffice poppler-utils
pip install python-pptx pillow langgraph openai gradio

## ▶️ 실행 방법
python app/main_gradio.py
