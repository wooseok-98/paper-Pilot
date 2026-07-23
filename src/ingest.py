import json
from pathlib import Path

import faiss

from embedding import embed

def load_metadata(out_dir: Path) -> list[dict]:
    """기존 메타 데이터 로드, 없으면 빈 리스트"""
    meta_path = out_dir / "metadata.json"
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            return json.load(f)
    return []


def load_index(out_dir: Path, dim: int) -> faiss.Index:
    """기존 인덱스 로드, 없으면 dim 차원의 새 index 생성"""
    index_path = out_dir / "index.faiss"
    if index_path.exists():
        return faiss.read_index(str(index_path))
    return faiss.IndexFlatIP(dim)


def ingest_papers(papers: list[dict], out_dir: str = "data") -> int:
    """새 논문을 기존 FAISS 인덱스에 누적 저장"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 기존 metadata 로드 -> 중복 제거
    metadata = load_metadata(out_dir)
    existing_ids = {p["paper_id"] for p in metadata}
    new_papers = [p for p in papers if p["paper_id"] not in existing_ids]
    if not new_papers:
        return len(metadata)

    # 2. 새 논문 임베딩
    texts = [p["title"] + " " + p["abstract"] for p in new_papers]
    vectors = embed(texts).astype("float32")
    dim = vectors.shape[1]

    # 3. index 로드/생성 후 add
    index = load_index(out_dir, dim)
    index.add(vectors)

    # 4. metadata 같은 순서로 이어붙임
    metadata.extend(new_papers)

    # 5. 저장
    faiss.write_index(index, str(out_dir / "index.faiss"))
    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return len(metadata)