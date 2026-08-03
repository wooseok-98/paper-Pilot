"""FastAPI 진입점 - LangGraph 엔진을 감싸는 얇은 HTTP 어댑터"""
import anthropic
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from graph import graph
from llm import StructuredOutputError

app = FastAPI(title="Paper Pilot")

# 요청
class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=300)

# 응답
class PaperOut(BaseModel):
    paper_id: str
    title: str

class AskResponse(BaseModel):
    intent: str                     # Orchestrator의 판단 (search / query)
    answer: str | None = None       # query 결과
    papers: list[PaperOut] = []
    grounded: bool | None = None    # Critic 검증 통과 여부
    search_retries: int = 0         # QA 재검색 횟수 (self-RAG)
    critic_runs: int = 0            # Critic이 검증한 횟수 (1 = 한 번에 통과)
    gave_up: bool = False
    give_up_reason: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    try:
        state = graph.invoke(
            {"question": req.question},
            config={"recursion_limit": 40,}
        )
    except (anthropic.APIError, StructuredOutputError):
        raise HTTPException(status_code=503, detail="LLM 호출 실패")

    return AskResponse(
        intent=state.get("intent",""),
        answer=state.get("answer"),
        papers=state.get("papers", []),
        grounded=state.get("grounded"),
        search_retries=state.get("search_retries", 0),
        critic_runs=state.get("critic_retries", 0),
        gave_up=state.get("gave_up", False),
        give_up_reason=state.get("give_up_reason"),
    )