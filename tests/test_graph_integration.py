"""LLM·검색을 mock한 그래프 통합 테스트

개별 라우팅 함수가 아니라, 컴파일된 그래프를 실제로 invoke해서
조건부 엣지 배선 · 자기교정 루프 · 종료 조건이 함께 도는지 검증.
LLM/검색 함수를 가짜로 갈아끼워 결정적으로 만든다.

graph.py가 `from agents.orchestrator import classify_intent` 식으로
LLM 함수를 자기 네임스페이스에 들여오므로, 노드는 호출 시점에 graph 모듈의
전역을 참조한다 -> `monkeypatch.setattr(gmod, "함수명", 가짜)`로 갈아끼움.
"""
import graph as gmod


def _paper(pid="1"):
    return {"paper_id": pid, "title": "t", "abstract": "a"}


def test_query_happy_path(monkeypatch):
    """query -> 충분 -> 생성 -> 근거O -> END"""
    monkeypatch.setattr(gmod, "classify_intent", lambda q: {"intent": "query"})
    monkeypatch.setattr(gmod, "retrieve", lambda q, k: [_paper()])
    monkeypatch.setattr(gmod, "check_sufficiency", lambda q, papers: {"sufficient": True, "rewritten_query": ""})
    monkeypatch.setattr(gmod, "generate_answer", lambda q, papers, feedback=None: "답변 [1]")
    monkeypatch.setattr(gmod, "check_grounding", lambda ans, papers: {"grounded": True, "issues": []})

    result = gmod.graph.invoke({"question": "질문"})

    assert not result.get("gave_up")
    assert result["answer"] == "답변 [1]"
    assert result["grounded"] is True


def test_query_gives_up_after_max_research_retries(monkeypatch):
    """query -> 계속 불충분 -> 재검색 상한 -> give_up(insufficient)"""
    monkeypatch.setattr(gmod, "classify_intent", lambda q: {"intent": "query"})
    monkeypatch.setattr(gmod, "retrieve", lambda q, k: [_paper()])
    monkeypatch.setattr(gmod, "check_sufficiency", lambda q, papers: {"sufficient": False, "rewritten_query": "다른 쿼리"})

    result = gmod.graph.invoke({"question": "코퍼스에 없는 주제"})

    assert result["gave_up"] is True
    assert result["give_up_reason"] == "insufficient"
    assert result["search_retries"] == gmod.MAX_RETRIES     # 상한까지 돌았는지


def test_critic_reflection_then_pass(monkeypatch):
    """근거 미달 1회 반려 -> 피드백 반영 재생성 -> 통과 (Reflection 루프)"""
    monkeypatch.setattr(gmod, "classify_intent", lambda q: {"intent": "query"})
    monkeypatch.setattr(gmod, "retrieve", lambda q, k: [_paper()])
    monkeypatch.setattr(gmod, "check_sufficiency", lambda q, papers: {"sufficient": True, "rewritten_query": ""})
    monkeypatch.setattr(gmod, "generate_answer", lambda q, papers, feedback=None: "답변")

    calls = {"n": 0}

    def fake_grounding(ans, papers):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"grounded": False, "issues": ["초록에 없는 주장"]}   # 첫 검증 반려
        return {"grounded": True, "issues": []}                          # 재생성 후 통과

    monkeypatch.setattr(gmod, "check_grounding", fake_grounding)

    result = gmod.graph.invoke({"question": "질문"})

    assert not result.get("gave_up")
    assert result["grounded"] is True
    assert result["critic_retries"] == 2                    # 두 번째 검증에서 통과


def test_search_path_runs_researcher(monkeypatch):
    """search -> researcher -> END (질의응답 경로로 새지 않음)"""
    monkeypatch.setattr(gmod, "classify_intent", lambda q: {"intent": "search"})
    monkeypatch.setattr(gmod, "research", lambda q: [_paper("1"), _paper("2")])

    result = gmod.graph.invoke({"question": "논문 찾아줘"})

    assert result["intent"] == "search"
    assert len(result["papers"]) == 2
