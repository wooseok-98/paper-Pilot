from llm import call_structured
from qa import build_context

MAX_RETRIES = 3

GROUNDING_SCHEMA = {
    "type": "object",
    "properties": {
        "issues":{
            "type": "array",
            "items": {"type": "string"},
            "description": "답변에서 제공된 초록에 근거가 없는 주장들 (모두 근거가 있으면 빈 배열을)",
        },
        "grounded": {"type": "boolean"},
    },
    "required": ["issues", "grounded"],
}

def check_grounding(answer: str, papers: list[dict]) -> dict:
    """답변의 각 주장이 초록에 실제로 근거하는지 대조"""
    return call_structured(
        prompt= f"논문 초록:\n{build_context(papers)}\n\n"
                f"생성된 답변:\n{answer}\n\n"
                f"초록에 근거가 없는 주장을 issues로 나열하고, "
                f"모든 주장에 근거가 있으면 grounded=true로 판정해줘.",
        schema=GROUNDING_SCHEMA,
    )