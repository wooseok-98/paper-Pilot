import json
from pathlib import Path

import faiss
import numpy as np

from search import search_papers
from embedding import embed

def ingest_papers(papers: list[dict], out_dir: str = "data") -> int:
    """논문을 벡터화하여 FAISS 인덱스에 저장"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 임베딩할 텍스트 수집 (title + abstract)
    texts = [paper["title"] + " " + paper["abstract"] for paper in papers]
    
    # 텍스트 임베딩
    vectors = embed(texts).astype("float32")

    # FAISS 인덱스 생성
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    # FAISS 인덱스 저장
    faiss.write_index(index, str(out_dir / "index.faiss"))

    # 논문 메타데이터 저장
    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)

    return len(papers)