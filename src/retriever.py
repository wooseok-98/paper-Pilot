import json
from pathlib import Path

import faiss

from embedding import embed

def retrieve(query: str, k: int = 5, index_dir: str = "data") -> list[dict]:
    """질문과 유사한 논문 top-k를 검색하여 반환"""
    index_dir = Path(index_dir)

    # FAISS 인덱스 로드
    index = faiss.read_index(str(index_dir / "index.faiss"))

    # 논문 메타데이터 로드
    with open(index_dir / "metadata.json", "r", encoding="utf-8") as f:
        papers = json.load(f)

    # 쿼리 임베딩
    query_vector = embed([query]).astype("float32")

    # FAISS 검색
    scores, indices = index.search(query_vector, k)

    # 검색 결과 논문 반환 (질문 한개씩 처리)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        paper = papers[idx]
        results.append({
            **paper,                 # 기존 paper dict 정보 유지
            "score": float(score)
        })

    return results