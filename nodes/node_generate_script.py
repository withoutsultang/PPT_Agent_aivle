import os
from openai import OpenAI

LLM_MODEL = "gpt-4o-mini"
client = OpenAI()

def node_generate_script(state: dict) -> dict:
    """
    강의 스크립트 생성
    - 슬라이드 요약(page_content)을 기반으로 발표 대본 작성
    """
    page_content = state.get("page_content", "")
    prompt = state.get("prompt", {}) or {}
    tone = prompt.get("tone", "전문적이고 신뢰감을 주는 톤")
    style = prompt.get("style", "쉬운 이해 중심")
    work_dir = state.get("work_dir", "./")

    if not page_content.strip():
        raise ValueError("state['page_content']가 비어 있습니다. 먼저 node_generate_text를 실행하세요.")

    system_prompt = (
        "당신은 슬라이드 내용을 바탕으로 발표 대본을 작성하는 전문 발표 코치입니다.\n"
        "대본은 약 60~90초 분량으로, 인트로 → 본문 → 마무리 구조를 따르고, 자연스럽게 청중에게 말하듯이 작성합니다."
    )

    user_prompt = (
        f"[요약 내용]\n{page_content}\n\n"
        f"규칙:\n"
        f"- {tone}으로 말할 것\n"
        f"- {style}으로 구성할 것\n"
        f"- 글머리표 금지, 자연스러운 단락 유지\n"
        f"- 불필요한 반복과 과장 금지\n"
        f"- 분량은 60~90초에 해당하는 길이로 작성"
    )

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
    )

    script = response.choices[0].message.content.strip()
    state["script"] = script

    os.makedirs(work_dir, exist_ok=True)
    script_path = os.path.join(work_dir, "script.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    return state
