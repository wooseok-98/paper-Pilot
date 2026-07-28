"""researcher.merge_by_paper_id 순수 함수 테스트 (LLM·arXiv 호출 없음)"""
import pytest

from agents.researcher import merge_by_paper_id


@pytest.mark.parametrize(
    "lists, expected_ids",
    [
        ([[{"paper_id": "1"}], [{"paper_id": "1"}, {"paper_id": "2"}]], ["1", "2"]),  # 중복 제거
        ([], []),                                                                     # 인자 없음
        ([[], []], []),                                                               # 빈 리스트들
        ([[{"paper_id": "1"}, {"paper_id": "2"}, {"paper_id": "3"}]], ["1", "2", "3"]),  # 단일 리스트 보존
    ],
)
def test_merge_dedups_by_paper_id(lists, expected_ids):
    merged = merge_by_paper_id(*lists)
    assert [p["paper_id"] for p in merged] == expected_ids


def test_merge_later_list_wins():
    # 같은 paper_id면 뒤에 온 dict로 덮어써짐
    merged = merge_by_paper_id(
        [{"paper_id": "1", "title": "old"}],
        [{"paper_id": "1", "title": "new"}],
    )
    assert len(merged) == 1
    assert merged[0]["title"] == "new"
