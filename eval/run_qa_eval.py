"""RAG 근거 일치 평가 — generate_answer가 초록에 근거해 답하고, 없으면 정직하게 항복하는가

datasets/qa_cases.json 의 각 질문에 generate_answer(question, papers)를 호출:
  - answerable   → check_grounding으로 근거 여부 판정 (grounded=True 기대)
  - unanswerable → 답변이 '초록에 없...' 류로 항복했는지 (환각 대신 abstain)

근거 일치율 = grounded 답변 / answerable 질문
정직한 항복률 = 항복한 답변 / unanswerable 질문

한계: answerable 채점을 자체 Critic(check_grounding)으로 하는 self-judge —
      숫자는 참고용, 실제 답변 텍스트를 사람이 spot-check 병행 권장.

실행: 프로젝트 루트에서  .venv/bin/python eval/run_qa_eval.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.qa import generate_answer
from agents.critic import check_grounding

CASES = Path(__file__).parent / "datasets" / "qa_cases.json"
ABSTAIN_MARKER = "초록에 없"        # ANSWER_SYSTEM이 지시한 항복 문구


def main():
    cases = json.loads(CASES.read_text(encoding="utf-8"))

    n_ans = n_unans = 0
    grounded_ok = abstain_ok = 0

    for c in cases:
        answer = generate_answer(c["question"], c["papers"])
        abstained = ABSTAIN_MARKER in answer

        if c["kind"] == "answerable":
            n_ans += 1
            grounded = check_grounding(answer, c["papers"])["grounded"]
            ok = grounded and not abstained            # 근거 있게 실제로 답함
            if ok:
                grounded_ok += 1
            verdict = f"grounded={grounded}"
        else:                                           # unanswerable
            n_unans += 1
            ok = abstained                              # 없는 걸 지어내지 않고 항복
            if ok:
                abstain_ok += 1
            verdict = f"abstained={abstained}"

        print(f"[{c['id']}] {c['kind']} — {verdict} {'✓' if ok else '✗'}")
        print(f"  Q: {c['question']}")
        print(f"  A: {answer.strip()[:200]}\n")

    print("[요약]")
    if n_ans:
        print(f"  근거 일치율 (answerable):   {grounded_ok}/{n_ans} = {grounded_ok / n_ans:.2f}")
    if n_unans:
        print(f"  정직한 항복률 (unanswerable): {abstain_ok}/{n_unans} = {abstain_ok / n_unans:.2f}")


if __name__ == "__main__":
    main()
