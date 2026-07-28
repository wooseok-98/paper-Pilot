"""검색 골드셋 라벨 틀 생성 (1회용 헬퍼)

토픽별로 원본 쿼리 + 대체 쿼리(expand_query)를 각각 검색해, 후보 논문을
어느 쿼리가 찾았는지(source) 태그와 함께 datasets/search_gold.json에 덤프한다.
`relevant`는 null로 비워두고 → 사람이 각 후보를 true/false로 채우면 골드셋 완성.

실행: 프로젝트 루트에서  .venv/bin/python eval/build_gold.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from search import search_papers
from agents.researcher import expand_query

# 평가할 토픽 — 오염/누락이 알려진 주제로 시작 (필요 시 추가)
TOPICS = [
    {"topic": "stable diffusion", "query": "stable diffusion"},
]
SEARCH_SIZE = 10
OUT = Path(__file__).parent / "datasets" / "search_gold.json"


def source_tag(pid: str, base_ids: set, alt_ids: set) -> str:
    """이 논문을 원본/대체/양쪽 중 어느 쿼리가 찾았는지"""
    if pid in base_ids and pid in alt_ids:
        return "both"
    return "base" if pid in base_ids else "alt"


def build_topic(topic: str, query: str) -> dict:
    alt_query = expand_query(query)                       # LLM: 대체 기술 용어
    base = search_papers(query, SEARCH_SIZE)
    alt = search_papers(alt_query, SEARCH_SIZE)
    base_ids = {p["paper_id"] for p in base}
    alt_ids = {p["paper_id"] for p in alt}

    merged = {}                                           # paper_id 기준 중복 제거
    for p in base + alt:
        merged.setdefault(p["paper_id"], p)

    candidates = [
        {
            "paper_id": p["paper_id"],
            "title": p["title"],
            "abstract": p["abstract"],
            "source": source_tag(p["paper_id"], base_ids, alt_ids),
            "relevant": None,                             # ← 사람이 채울 칸 (true/false)
        }
        for p in merged.values()
    ]
    return {"topic": topic, "query": query, "alt_query": alt_query, "candidates": candidates}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    gold = [build_topic(t["topic"], t["query"]) for t in TOPICS]
    OUT.write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")
    n = sum(len(g["candidates"]) for g in gold)
    print(f"후보 {n}개를 {OUT} 에 저장")
    print("→ 각 후보의 relevant를 true/false로 채운 뒤 run_search_eval.py 실행")


if __name__ == "__main__":
    main()
