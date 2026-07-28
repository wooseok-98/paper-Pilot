"""Critic 검출률 평가 — 심은 환각을 잡는가 + 멀쩡한 답변을 오탐하는가

datasets/grounding_cases.json 의 각 케이스에 check_grounding(answer, papers)를 호출:
  - hallucinated 케이스 → grounded=False 여야 검출 성공
  - clean 케이스        → grounded=True  여야 오탐 아님

검출률 = 잡은 환각 / 전체 환각      (Critic이 실제로 일하는가)
오탐률 = 잘못 반려한 clean / 전체 clean  (멀쩡한 답을 죽이지 않는가)

실행: 프로젝트 루트에서  .venv/bin/python eval/run_critic_eval.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.critic import check_grounding

CASES = Path(__file__).parent / "datasets" / "grounding_cases.json"


def main():
    cases = json.loads(CASES.read_text(encoding="utf-8"))

    n_hallu = n_clean = 0
    detected = false_positive = 0

    print(f"{'id':<24}{'kind':<14}{'grounded':>9}{'issues':>7}  판정")
    print("-" * 70)
    for c in cases:
        result = check_grounding(c["answer"], c["papers"])
        grounded = result["grounded"]
        caught = not grounded                       # Critic이 문제를 잡았나

        if c["kind"] == "hallucinated":
            n_hallu += 1
            ok = caught                             # 잡아야 정답
            if caught:
                detected += 1
        else:                                        # clean
            n_clean += 1
            ok = grounded                            # 통과시켜야 정답
            if caught:
                false_positive += 1

        mark = "✓" if ok else "✗"
        print(f"{c['id']:<24}{c['kind']:<14}{str(grounded):>9}{len(result['issues']):>7}  {mark}")

    print("\n[요약]")
    print(f"  검출률: {detected}/{n_hallu}"
          + (f" = {detected / n_hallu:.2f}" if n_hallu else ""))
    print(f"  오탐률: {false_positive}/{n_clean}"
          + (f" = {false_positive / n_clean:.2f}" if n_clean else ""))


if __name__ == "__main__":
    main()
