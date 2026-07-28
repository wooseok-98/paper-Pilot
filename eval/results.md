# PaperPilot — 평가 결과 (Scorecard)

각 자율 장치의 baseline. 개선 후 같은 지표로 재측정해 before/after 비교.

**2026-07-28 재측정 (ADR-019 `temperature=0` 적용 후):** 이전 수치는 `call_structured`가 API 기본 temperature(1.0)로 호출돼 실행마다 흔들리는 표본이었음. 고정 후 같은 스크립트를 연속 2회 실행 → **전 지표 완전 동일 재현**(검색 precision/recall/F1, Critic 검출·오탐, 이슈 개수까지). 아래 수치는 결정적 baseline.

---

## 1. 검색 관련도 — CRAG 필터 (Researcher)
`eval/run_search_eval.py` · 골드셋 20개 (관련 4, 사람 라벨)

| 구분 | precision | recall | F1 | kept |
| --- | --- | --- | --- | --- |
| OFF (필터 전) | 0.20 | 1.00 | — | 20 |
| **ON (필터 후, baseline)** | **0.44** | **1.00** | **0.62** | 9 |

- 대체쿼리 recall 기여: 원본이 놓친 관련 논문 **3개** 확보
- 진단: 오염 5개가 아직 통과 (borderline 응용 논문 추정) → 필터 프롬프트 튜닝 여지
- 개선 목표: **recall 1.00 유지하며 precision ↑**

## 2. Critic 검출률 — Reflection
`eval/run_critic_eval.py` · grounding_cases.json (환각 심은 답변 + clean 답변)

| 지표 | baseline |
| --- | --- |
| 검출률 (심은 환각을 반려) | **3/3 = 1.00** |
| 오탐률 (clean을 잘못 반려) | **0/3 = 0.00** |

## 3. RAG 근거 일치 — QA (self-RAG)
`eval/run_qa_eval.py` · qa_cases.json (answerable + unanswerable)
> 한계: 채점을 자체 Critic으로 하는 self-judge — 사람 spot-check 병행

| 지표 | baseline |
| --- | --- |
| 근거 일치율 (answerable) | **2/2 = 1.00** |
| 정직한 항복률 (unanswerable) | **2/2 = 1.00** |

> ⚠️ 검출기 구조는 여전히 문자열 부분일치(`ABSTAIN_MARKER = "초록에 없"`)라 표현이 조금만
> 달라져도(예: "정보가 포함되어 있지 않습니다") 다시 과소집계될 수 있는 잠재 버그.
> 이번 재현에선 두 답변 모두 우연히 정확 문구를 포함해 정상 집계됐을 뿐 — 근본 수정은
> 항복 신호를 구조화(sentinel 토큰)하거나 LLM 판정으로 교체해야 함

## 4. 자기교정 발동·개선폭 — self-RAG 재검색 (보류)
FAISS 코퍼스 + "첫 검색이 부족하도록" 유도한 질문셋이 있어야 재검색 전/후를 잼
→ **코퍼스 구축 후 측정** (지금은 코퍼스가 비어 정직하게 측정 불가)
