import anthropic
from dotenv import load_dotenv

load_dotenv()
MODEL = "claude-haiku-4-5"

# ANTHROPIC_API_KEY 환경변수 자동 인식
_client = anthropic.Anthropic(timeout=30.0, max_retries=2)

class StructuredOutputError(RuntimeError):
    """LLM이 구조화 출력(tool_use)을 반환하지 않음"""

def call_llm(prompt: str, system: str = "", max_tokens: int = 2048) -> str:
    """자유 텍스트 응답"""
    response = _client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def call_structured(prompt: str, schema: dict, system: str = "") -> dict:
    """schema 형식의 구조화된(JSON) 응답"""
    tool = {
        "name": "respond",
        "description": "주어진 스키마 형식으로 응답",
        "input_schema": schema,                            # 출력 형태 강제
    }
    response = _client.messages.create(
        model=MODEL,
        max_tokens=1024,
        temperature=0,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        tools=[tool],
        tool_choice={"type": "tool", "name": "respond"},   # respond 도구 호출 강제
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    # stop_reason이 max_tokens면 응답이 잘린 것 → 원인이 바로 보임
    raise StructuredOutputError(f"구조화 출력을 받지 못함 (stop_reason={response.stop_reason})")