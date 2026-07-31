"""retriever의 방어 가드 테스트

통합 테스트가 `retrieve`를 mock으로 갈아끼우기 때문에 retriever 자체는
검증되지 않는 사각지대였음(실제로 `faiss.read_index`에 Path를 넘겨 깨진 채
전체 테스트가 통과한 적 있음). 여기서는 mock 없이 임시 디렉토리에 진짜
인덱스를 만들어 호출한다.

검증 대상 두 가지
- 인덱스/metadata 파일이 없을 때 크래시 대신 빈 리스트 (배포 직후 data/ 없음)
- 코퍼스가 k보다 작을 때 FAISS가 채우는 -1 슬롯 제외 (papers[-1] 오동작 방지)
"""
import json

import faiss
import numpy as np
import pytest

from retriever import retrieve

DIM = 384   # all-MiniLM-L6-v2 출력 차원


def make_corpus(dir_path, n):
    """n편짜리 임시 코퍼스 생성

    벡터 내용은 검증 대상이 아니므로 embed()를 태우지 않고 단위벡터를 직접 넣는다.
    """
    index = faiss.IndexFlatIP(DIM)
    index.add(np.eye(n, DIM, dtype="float32"))
    faiss.write_index(index, str(dir_path / "index.faiss"))

    papers = [{"paper_id": f"p{i}", "title": f"제목{i}", "abstract": f"초록{i}"}
              for i in range(n)]
    (dir_path / "metadata.json").write_text(json.dumps(papers), encoding="utf-8")


@pytest.mark.parametrize(
    "missing",
    [
        None,               # 두 파일 다 없음 (배포 직후)
        "index.faiss",      # metadata만 남음
        "metadata.json",    # 인덱스만 남음 -> 위치 정렬을 신뢰할 수 없음
    ],
)
def test_retrieve_returns_empty_when_files_missing(tmp_path, missing):
    if missing is not None:
        make_corpus(tmp_path, 3)
        (tmp_path / missing).unlink()

    assert retrieve("질문", k=5, index_dir=tmp_path) == []


@pytest.mark.parametrize(
    "corpus_size, k, expected",
    [
        (10, 5, 5),   # 코퍼스 > k -> k개
        (5, 5, 5),    # 경계
        (3, 5, 3),    # 코퍼스 < k -> 있는 만큼만
        (1, 5, 1),    # 극단
    ],
)
def test_retrieve_drops_padding_slots(tmp_path, corpus_size, k, expected):
    make_corpus(tmp_path, corpus_size)
    results = retrieve("질문", k=k, index_dir=tmp_path)

    assert len(results) == expected
    assert len({r["paper_id"] for r in results}) == expected   # 같은 논문 반복 금지
    assert all(r["score"] > -1e30 for r in results)            # -3.4e38 빈 슬롯 점수 배제
