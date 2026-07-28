"""graph의 라우팅·포기 순수 함수 테스트

State(dict)를 넣으면 다음 노드 이름(또는 END)을 돌려주는 분기 로직만 검증.
경계값(MAX_RETRIES 직전/도달)과 카운터 키 누락 케이스를 포함.

주의: `from graph import ...`가 graph.py 전체를 import하므로
임베딩 모델 로딩·Anthropic 클라이언트 생성이 딸려 일어남(첫 실행이 느릴 수 있음).
"""
import pytest
from langgraph.graph import END

from graph import (
    route_intent,
    route_sufficiency,
    route_grounding,
    give_up_node,
    MAX_RETRIES,
)


@pytest.mark.parametrize(
    "intent, expected",
    [
        ("search", "researcher"),
        ("query", "retrieve"),
    ],
)
def test_route_intent(intent, expected):
    assert route_intent({"intent": intent}) == expected


@pytest.mark.parametrize(
    "state, expected",
    [
        ({"sufficient": True, "search_retries": 99}, "generate_answer"),          # 충분하면 재시도 무관 생성
        ({"sufficient": False, "search_retries": 0}, "rewrite_query"),            # 부족 + 여유 -> 재검색
        ({"sufficient": False, "search_retries": MAX_RETRIES - 1}, "rewrite_query"),  # 경계 직전
        ({"sufficient": False, "search_retries": MAX_RETRIES}, "give_up"),        # 상한 도달 -> 포기
        ({"sufficient": False}, "rewrite_query"),                                 # 카운터 키 없음 -> 0 취급
    ],
)
def test_route_sufficiency(state, expected):
    assert route_sufficiency(state) == expected


@pytest.mark.parametrize(
    "state, expected",
    [
        ({"grounded": True, "critic_retries": 99}, END),                          # 근거 있으면 종료
        ({"grounded": False, "critic_retries": 0}, "generate_answer"),            # 미근거 + 여유 -> 재생성
        ({"grounded": False, "critic_retries": MAX_RETRIES - 1}, "generate_answer"),  # 경계 직전
        ({"grounded": False, "critic_retries": MAX_RETRIES}, "give_up"),          # 상한 도달 -> 포기
    ],
)
def test_route_grounding(state, expected):
    assert route_grounding(state) == expected


@pytest.mark.parametrize(
    "state, expected_reason",
    [
        ({"sufficient": False}, "insufficient"),   # 초록 불충분으로 포기
        ({"sufficient": True}, "ungrounded"),      # 초록은 충분했으나 근거 검증 실패
        ({}, "insufficient"),                      # 키 없음 -> 불충분 취급
    ],
)
def test_give_up_reason(state, expected_reason):
    out = give_up_node(state)
    assert out["gave_up"] is True
    assert out["give_up_reason"] == expected_reason
    assert out["answer"]                           # 사용자 안내 메시지 존재
