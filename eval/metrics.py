"""검색 평가 지표 — 전부 순수 함수 (집합 연산만, LLM·IO 없음 → 유닛 테스트 가능)

선택된 논문(selected)과 정답 관련 논문(relevant)을 paper_id 집합으로 비교.
"""


def precision(selected_ids, relevant_ids) -> float:
    """선택한 것 중 실제 관련된 비율 = |선택 ∩ 관련| / |선택|

    "내가 고른 게 얼마나 정확한가" — 오염(irrelevant 혼입)이 많으면 낮아짐
    """
    selected = set(selected_ids)
    if not selected:
        return 0.0
    return len(selected & set(relevant_ids)) / len(selected)


def recall(selected_ids, relevant_ids) -> float:
    """관련된 것 중 선택된 비율 = |선택 ∩ 관련| / |관련|

    "정답을 얼마나 놓치지 않았나" — 관련 논문을 버리면 낮아짐
    """
    relevant = set(relevant_ids)
    if not relevant:
        return 0.0
    return len(set(selected_ids) & relevant) / len(relevant)


def f1(selected_ids, relevant_ids) -> float:
    """precision과 recall의 조화평균 — 둘의 균형을 한 숫자로"""
    p = precision(selected_ids, relevant_ids)
    r = recall(selected_ids, relevant_ids)
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)
