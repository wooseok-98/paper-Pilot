from llm import call_structured

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "reason": {"type": "string"},
        "intent": {
            "type": "string",
            "enum": ["search", "query"],
            "description": "search=논문을 찾아, 수집해 달라는 요청, query=내용이나 사실을 묻는 질문",
        },
    },
    "required": ["reason", "intent"],    
}


def classify_intent(question: str) -> dict:
    """사용자 요청을 search / query로 분류 (라우팅)"""
    return call_structured(
        prompt= f"사용자 요청: {question}\n\n"
                f"이 요청을 분류해줘."
                f"- search: 특정 주제의 논문을 찾아달라·수집해달라는 요청 (예: '~논문 찾아줘', '~조사해줘')\n"
                f"- query: 어떤 내용이나 사실을 묻는 질문 (예: '~할 수 있나?', '~는 무엇인가?')",
        schema=INTENT_SCHEMA,
    )
