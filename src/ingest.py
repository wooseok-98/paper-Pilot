import json
import os
import threading
from pathlib import Path

import faiss

from config import DATA_DIR
from embedding import embed

# 모듈 로드 시 한 번만 생성
_write_lock = threading.Lock()


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


def ingest_papers(papers: list[dict], out_dir: str | Path = DATA_DIR) -> int:
    """새 논문을 기존 FAISS 인덱스에 누적 저장"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 읽기~쓰기 전체를 한 단위로 (쓰기만 감싸면 두 요청이 같은 값을 읽어 한쪽 작업이 사라짐)
    with _write_lock:
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

        # 5. 같은 디렉토리의 .tmp에 완성한 뒤 이름만 교체
        tmp_index = out_dir / "index.faiss.tmp"
        tmp_meta = out_dir / "metadata.json.tmp"

        faiss.write_index(index, str(tmp_index))
        with open(tmp_meta, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        os.replace(tmp_index, out_dir / "index.faiss")
        os.replace(tmp_meta, out_dir / "metadata.json")

        return len(metadata)
