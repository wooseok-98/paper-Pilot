"""eval.metrics 순수 함수 테스트 — 지표 수식이 맞는지 (LLM·IO 없음)"""
import pytest

from metrics import precision, recall, f1


@pytest.mark.parametrize(
    "selected, relevant, expected",
    [
        (["1", "2", "3", "4"], ["1", "2"], 0.5),   # 4개 중 2개 관련
        (["1", "2"], ["1", "2"], 1.0),             # 전부 관련
        (["3", "4"], ["1", "2"], 0.0),             # 하나도 관련 없음
        ([], ["1"], 0.0),                          # 아무것도 안 고름
    ],
)
def test_precision(selected, relevant, expected):
    assert precision(selected, relevant) == expected


@pytest.mark.parametrize(
    "selected, relevant, expected",
    [
        (["1"], ["1", "2"], 0.5),                  # 관련 2개 중 1개만 건짐
        (["1", "2"], ["1", "2"], 1.0),             # 다 건짐
        (["1", "2", "9"], ["1", "2"], 1.0),        # 잡음 섞여도 관련은 다 건짐
        (["1"], [], 0.0),                          # 정답이 없음
    ],
)
def test_recall(selected, relevant, expected):
    assert recall(selected, relevant) == expected


def test_f1_balances_precision_recall():
    # precision=0.5, recall=1.0 -> f1 = 2*.5*1/(1.5) = 0.666...
    assert f1(["1", "2"], ["1"]) == pytest.approx(2 / 3)


def test_f1_zero_when_no_overlap():
    assert f1(["3"], ["1", "2"]) == 0.0
