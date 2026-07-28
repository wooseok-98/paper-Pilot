"""검색 관련도 평가 — CRAG 필터 OFF vs ON, 대체쿼리 recall 기여

datasets/search_gold.json(사람이 라벨한 골드셋)을 읽어 두 가지를 측정:
  1) 필터 효과(precision) — filter_relevant를 실제 호출(live)해 OFF/ON 비교
  2) 대체쿼리 recall 기여 — source 라벨만으로 결정적 계산

실행: 프로젝트 루트에서  .venv/bin/python eval/run_search_eval.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.researcher import filter_relevant
from metrics import precision, recall, f1

GOLD = Path(__file__).parent / "datasets" / "search_gold.json"


def load_gold() -> list[dict]:
    if not GOLD.exists():
        raise SystemExit(f"{GOLD} 없음 — 먼저 build_gold.py 실행")
    data = json.loads(GOLD.read_text(encoding="utf-8"))
    for g in data:                                        # 라벨 누락 방지
        todo = [c for c in g["candidates"] if c["relevant"] is None]
        if todo:
            raise SystemExit(f"'{g['topic']}'에 라벨 안 된 후보 {len(todo)}개 — relevant를 채워주세요")
    return data


def eval_topic(g: dict) -> dict:
    candidates = g["candidates"]
    pool_ids = [c["paper_id"] for c in candidates]                       # 필터 전 전체 풀
    relevant_ids = [c["paper_id"] for c in candidates if c["relevant"]]  # 정답(사람 라벨)

    # (1) 필터 효과 — filter_relevant를 실제 호출
    filtered = filter_relevant(g["query"], candidates)
    kept_ids = [p["paper_id"] for p in filtered]

    # (2) 대체쿼리 recall 기여 — 원본이 놓쳤는데 대체가 건진 관련 논문
    alt_gain = [c["paper_id"] for c in candidates if c["relevant"] and c["source"] == "alt"]

    return {
        "topic": g["topic"],
        "pool": len(pool_ids),
        "kept": len(kept_ids),
        "off_p": precision(pool_ids, relevant_ids),   # 필터 안 하고 다 저장했을 때 정확도
        "on_p": precision(kept_ids, relevant_ids),    # 필터 후 정확도
        "on_r": recall(kept_ids, relevant_ids),       # 필터가 관련 논문을 얼마나 유지했나
        "on_f1": f1(kept_ids, relevant_ids),
        "alt_gain": len(alt_gain),
    }


def main():
    rows = [eval_topic(g) for g in load_gold()]

    header = f"{'topic':<20}{'pool':>5}{'kept':>5}{'OFF_P':>7}{'ON_P':>7}{'ON_R':>7}{'ON_F1':>7}{'alt+':>6}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(f"{r['topic']:<20}{r['pool']:>5}{r['kept']:>5}"
              f"{r['off_p']:>7.2f}{r['on_p']:>7.2f}{r['on_r']:>7.2f}{r['on_f1']:>7.2f}{r['alt_gain']:>6}")

    n = len(rows)
    avg_off = sum(r["off_p"] for r in rows) / n
    avg_on = sum(r["on_p"] for r in rows) / n
    total_alt = sum(r["alt_gain"] for r in rows)
    print("\n[요약]")
    print(f"  필터 효과   : 평균 precision {avg_off:.2f} → {avg_on:.2f}  ({avg_on - avg_off:+.2f})")
    print(f"  대체쿼리 기여: 원본이 놓친 관련 논문 {total_alt}개를 추가 확보")


if __name__ == "__main__":
    main()
