"""Context-aware script prompts, separated for review and regression tests."""


def build_script_messages(state: dict) -> list[dict[str, str]]:
    titles = state.get("titles", [])
    index = int(state.get("slide_index", 0))
    if not titles or not 0 <= index < len(titles):
        raise ValueError("현재 슬라이드와 목차를 확인해 주세요.")
    scripts = state.get("all_scripts", [])
    previous = scripts[index - 1] if index > 0 and len(scripts) >= index else "없음"
    options = state.get("prompt", {})
    if len(titles) == 1:
        flow = "한 장으로 구성된 전체 강의입니다. 인사말 없이 주제를 소개하고 본문을 설명한 뒤 핵심 요약과 마무리 끝인사를 포함하세요."
    elif index == 0:
        flow = "첫 번째 슬라이드입니다. 인사말 없이 전체 강의를 소개하는 도입부로 시작하세요. 이전 내용 요약과 마무리 인사는 금지합니다."
    elif index == len(titles) - 1:
        flow = "마지막 슬라이드입니다. 직전 설명에서 자연스럽게 이어가고, 전체 강의의 핵심 요약과 마무리 끝인사를 포함하세요. 다음 내용 예고는 금지합니다."
    else:
        flow = (
            f"중간 슬라이드입니다. 직전 대본의 끝부분 '{previous[-100:]}'에서 이어서 본론을 시작하세요. "
            f"마지막에는 다음 주제 '{titles[index + 1]}'로 이어지는 짧은 전환 문장을 포함하세요. "
            "매번 새로운 강의를 시작하는 듯한 인사와 이전 내용의 반복 요약은 금지합니다."
        )
    return [
        {"role": "system", "content": (
            "당신은 전문 AI 강사입니다. 여러 슬라이드가 하나의 연속적인 강의 영상이 되도록 대본을 작성하세요. "
            "목차, 직전 대본, 현재 슬라이드의 근거를 함께 참고하세요. 자료에 없는 수치나 출처를 만들어내지 마세요."
        )},
        {"role": "user", "content": f"""전체 강의 목차: {titles}
현재 슬라이드: {index + 1}/{len(titles)} · {titles[index]}
직전 슬라이드 대본:
{previous}
현재 슬라이드 핵심 내용:
{state.get('page_content', '')}
작성 조건:
- 톤: {options.get('tone', '친절하고 명료한 강의 톤')}
- 스타일: {options.get('style', '예시와 핵심 요점 중심')}
- 목표 분량: 약 {options.get('target_duration_sec', 60)}초, 재생 속도 1.0 기준
- 위치별 흐름: {flow}
- 마지막 장의 끝인사를 제외하고 '안녕하세요', '오늘', '이번 강의에서는', '감사합니다'를 반복하지 마세요.
- 화면에 있는 그래프·표·수치를 설명할 때 근거를 명시하세요. 없는 그래프를 언급하지 마세요.
- 한국어 구어체로 작성하고 제목, 번호, 코드블록, 대본 시작/종료 표시는 출력하지 마세요.
"""},
    ]
