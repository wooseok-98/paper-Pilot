from llm import call_llm, call_structured

SUFFICIENCY_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string"},
        "sufficient": {"type": "boolean"},
        "rewritten_query": {
            "type": "string",
            "description": "부족할 때 다시 검색할 쿼리 (다른 표현, 더 구체적인 용어로 재작성)",
        },
    },
    "required": ["reason", "sufficient", "rewritten_query"],
}

ANSWER_SYSTEM = (
    "제공된 논문 초록에 있는 내용만 근거로 답변한다. "
    "초록에 없는 내용은 추측하지 말고 '초록에 없는 내용입니다.'라고 답변한다. "
    "답변에는 근거가 된 논문의 paper_id를 함께 포함한다. "
)

def build_context(papers: list[dict]) -> str:
    """검색된 논문들을 prompt에 넣을 수 있는 문자열로 변환"""
    return "\n\n".join(
        f"[{p['paper_id']}] {p['title']}\n{p['abstract']}" for p in papers
    )

def check_sufficiency(question: str, papers: list[dict]) -> dict:
    """검색된 초록으로 질문에 답할 수 있는지 판단 (self-RAG)"""
    return call_structured(
        prompt= f"질문: {question}\n\n검색된 논문 초록:\n{build_context(papers)}\n\n"
                f"이 초록들만으로 질문에 답할 수 있는지 판단해줘.",
        schema=SUFFICIENCY_SCHEMA,
    )

def generate_answer(question: str, papers: list[dict], feedback: list[str] | None = None) -> str:
    """검색된 초록을 근거로 질문에 답변 (feedback 있으면 지적사항 반영해 재작성)"""
    revision = ""
    if feedback:
        revision = ("\n\n이전 답변에서 다음 내용이 초록에 근거가 없다고 피드백 받았다.:\n"
                    + "\n".join(f"- {f}" for f in feedback)
                    + "\n해당 부분을 제거하거나 '초록에 없는 내용입니다.'로 수정해서 다시 작성해줘.")
    return call_llm(
        prompt= f"질문: {question}\n\n검색된 논문 초록:\n{build_context(papers)}\n\n"
                f"위 초록들을 근거로 질문에 답변해줘.{revision}",
        system=ANSWER_SYSTEM,
    )