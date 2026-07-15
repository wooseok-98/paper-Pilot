import anthropic
from dotenv import load_dotenv

load_dotenv()
MODEL = "claude-haiku-4-5"

_client = anthropic.Anthropic()   # ANTHROPIC_API_KEY 환경변수 자동 인식


def call_llm(prompt: str, system: str = "") -> str:
    """자유 텍스트 응답"""
    response = _client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def call_structured(prompt: str, schema: dict, system: str = "") -> dict:
    """schema 형식의 구조화된(JSON) 응답"""
    tool = {
        "name": "respond",
        "description": "주어진 스키마 형식으로 응답",
        "input_schema": schema,                            # 출력 형태 깅제
    }
    response = _client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        tools=[tool],
        tool_choice={"type": "tool", "name": "respond"},   # respond 도구 호출 강제
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("구조화 출력을 받지 못함")