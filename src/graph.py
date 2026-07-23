from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from agents.orchestrator import classify_intent
from agents.researcher import research
from agents.qa import check_sufficiency, generate_answer
from agents.critic import check_grounding
from retriever import retrieve

MAX_RETRIES = 3
TOP_K = 5


class State(TypedDict, total=False):
    question: str                   # 원본 질문
    intent: str                     # search or query (검색 혹은 질의응답)
    query: str                      # 현재 검색 쿼리 (QA: 내부 논문 검색)
    rewritten_query: str            # check_sufficiency가 제안한 재검색 쿼리
    papers: list                    # 논문 리스트
    answer: str                     # 생성된 답변 (critic이 점검)
    issues: list                    # 근거 없는 주장 목록 (답변 재생성 피드백)
    sufficient: bool                # 답변 생성하기에 초록의 내용이 충분한지 여부 (self-RAG 판단)
    grounded: bool                  # 생성된 답변이 초록에 근거하는지 여부 (critic 판단)
    search_retries: int
    critic_retries: int
    gave_up: bool                   # 상한 도달로 포기했는지 여부
    give_up_reason: str             # 포기 사유 (초록 불충분 / 답변 근거 없음)


# [노드]
# 질문 보고 어디로 분기할지 결정
def orchestrator_node(state: State) -> dict:
    result = classify_intent(state["question"])
    return {"intent": result["intent"]} # search / query

# Search: 논문 검색+저장
def researcher_node(state: State) -> dict:
    return {"papers": research(state["question"])}

# QA: 질문 답에 필요한 논문 리스트에서 검색
def retrieve_node(state: State) -> dict:
    if state.get("query"):           
        query = state["query"]
    else:                            # 첫 실행 시
        query = state["question"]

    return {"papers": retrieve(query, k=TOP_K)}

# QA: 질문을 가지고 있는 논문 내에서 답할 수 있는 여부 판단
def check_sufficiency_node(state: State) -> dict:
    result = check_sufficiency(state["question"], state["papers"])
    return {"sufficient": result["sufficient"], "rewritten_query": result["rewritten_query"]}

# 새로 작성된 query 업데이트, 재시도 횟수 증가
def rewrite_query_node(state: State) -> dict:
    return {"query": state["rewritten_query"], 
            "search_retries": state.get("search_retries", 0) + 1}

# 답변 작성 (피드백(critic) 있을 경우 feedback 참고 답변)
def generate_answer_node(state: State) -> dict:
    answer = generate_answer(state["question"], state["papers"], feedback=state.get("issues"))
    return {"answer": answer}

# 생성된 답변 근거 기반 여부 확인, 재시도 횟수 증가
def critic_node(state: State) -> dict:
    result = check_grounding(state["answer"], state["papers"])
    return {"grounded": result["grounded"], "issues": result["issues"], 
            "critic_retries": state.get("critic_retries", 0) + 1}

# 검색 실패: 초록 불충분 포기 / 근거 실패: 답변 근거 없음 포기
def give_up_node(state: State) -> dict:
    if not state.get("sufficient"):
        reason = "insufficient"
        answer = "관련 논문을 찾지 못했습니다. 해당 주제의 논문을 먼저 검색해주세요."
    else:
        reason = "ungrounded"
        answer = "근거를 갖춘 답변을 생성하지 못했습니다. 질문을 더 구체적으로 해주세요."
    return {"gave_up": True, "give_up_reason": reason, "answer": answer}


# [라우팅]
# 질문 의도 분류 판단 후 분기 (검색 / 질의응답)
def route_intent(state: State) -> str:
    if state["intent"] == "search":
        return "researcher"
    else:
        return "retrieve"

# 초록이 충분한지 판단 후 분기 (답변 생성 / 질문 query 재작성 / 포기)
def route_sufficiency(state: State) -> str:
    if state["sufficient"]:
        return "generate_answer"
    if state.get("search_retries", 0) < MAX_RETRIES:
        return "rewrite_query"
    return "give_up"                    # 재검색 상한 도달 -> 포기

# 답변이 초록에 근거한지 판단 후 분기 (질문 답변 완료 / 답변 재생성 / 포기)
def route_grounding(state: State) -> str:
    if state["grounded"]:
        return END
    if state.get("critic_retries", 0) < MAX_RETRIES:
        return "generate_answer"
    return "give_up"                    # 재생성 상한 도달 -> 포기


# [그래프 조립]
def build_graph():
    g = StateGraph(State)

    # 노드
    g.add_node("orchestrator", orchestrator_node)
    g.add_node("researcher", researcher_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("check_sufficiency", check_sufficiency_node)
    g.add_node("rewrite_query", rewrite_query_node)
    g.add_node("generate_answer", generate_answer_node)
    g.add_node("critic", critic_node)
    g.add_node("give_up", give_up_node)

    # 엣지
    g.add_edge(START, "orchestrator")
    g.add_conditional_edges("orchestrator", route_intent)
    g.add_edge("researcher", END)
    g.add_edge("retrieve", "check_sufficiency")
    g.add_conditional_edges("check_sufficiency", route_sufficiency)
    g.add_edge("rewrite_query", "retrieve")
    g.add_edge("generate_answer", "critic")
    g.add_conditional_edges("critic", route_grounding)
    g.add_edge("give_up", END)
    return g.compile()


graph = build_graph()