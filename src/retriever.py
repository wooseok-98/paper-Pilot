import json
from pathlib import Path
from config import DATA_DIR

import faiss

from embedding import embed

def retrieve(query: str, k: int = 5, index_dir: str | Path = DATA_DIR) -> list[dict]:
    """질문과 유사한 논문 top-k를 검색하여 반환"""
    index_dir = Path(index_dir)
    index_path = index_dir / "index.faiss"
    meta_path = index_dir / "metadata.json"

    # 디렉토리가 아니라 두 파일의 존재를 확인 (한쪽만 있으면 정렬이 어긋난 상태)
    if not index_path.exists() or not meta_path.exists():
        return []

    # FAISS 인덱스 로드
    index = faiss.read_index(str(index_path))

    # 논문 메타데이터 로드
    with open(meta_path, "r", encoding="utf-8") as f:
        papers = json.load(f)

    # 쿼리 임베딩
    query_vector = embed([query]).astype("float32")

    # FAISS 검색
    scores, indices = index.search(query_vector, k)

    # 검색 결과 논문 반환 (질문 한개씩 처리)
    results = []
    for score, idx in zip(scores[0], indices[0]):
        # 현재 논문 개수 k보다 작은 경우 idx = -1
        if idx < 0 or idx >= len(papers):
            continue
        results.append({**papers[idx], "score": float(score)})
    return results