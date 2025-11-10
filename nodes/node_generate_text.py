from openai import OpenAI
from utils.text_utils import clean_text, split_sents
from utils.media_utils import img_to_data_url

client = OpenAI()
LLM_MODEL = "gpt-4o-mini"

def node_generate_text(state):
    texts_raw = state.get("texts", [])
    texts = clean_text(" ".join(map(str, texts_raw)))
    tables = state.get("tables", [])
    images = state.get("images", [])
    prompt = str(state.get("prompt", ""))

    table_text = ""
    if tables:
        first_table = tables[0][:6]
        table_text = "\n".join([" | ".join(map(str, row)) for row in first_table])

    image_data_urls = []
    for img_path in images[:3]:
        try:
            image_data_urls.append(img_to_data_url(img_path))
        except Exception:
            continue

    content_input = (
        f"[텍스트]\n{texts}\n\n[표]\n{table_text}\n\n"
        f"[프롬프트]\n{prompt}\n---\n요약문을 4~6문장으로 작성하세요."
    )

    messages = [
        {"role": "system", "content": "당신은 슬라이드 요약 전문가입니다."},
        {"role": "user", "content": [{"type": "text", "text": content_input}]}
    ]
    for img_url in image_data_urls:
        messages[-1]["content"].append({"type": "image_url", "image_url": {"url": img_url}})

    response = client.chat.completions.create(model=LLM_MODEL, messages=messages)
    page_content = clean_text(response.choices[0].message.content)
    state["page_content"] = " ".join(split_sents(page_content))
    return state

