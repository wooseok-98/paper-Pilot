# PaperPilot — 평가 결과 (Scorecard)

각 자율 장치의 baseline. 개선 후 같은 지표로 재측정해 before/after 비교.
(수치는 LLM 비결정성으로 실행마다 소폭 흔들림 — 여러 번 평균 권장)

---

## 1. 검색 관련도 — CRAG 필터 (Researcher)
`eval/run_search_eval.py` · 골드셋 20개 (관련 4, 사람 라벨)

| 구분 | precision | recall | kept |
| --- | --- | --- | --- |
| OFF (필터 전) | 0.20 | 1.00 | 20 |
| **ON (필터 후, baseline)** | **0.44** | **1.00** | 9 |

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
| 정직한 항복률 (unanswerable) | 실제 **2/2** — 단, 키워드 검출기는 1/2로 과소집계 |

> ⚠️ 측정 버그: `ABSTAIN_MARKER = "초록에 없"` 정확 문구만 찾아, "정보가 포함되어
> 있지 않습니다" 같은 다른 표현의 항복을 놓침. 모델은 2/2 정직하게 항복함(텍스트 확인).
> → 항복 신호를 구조화(sentinel 토큰)하거나 LLM 판정으로 교체해야 정확 측정

## 4. 자기교정 발동·개선폭 — self-RAG 재검색 (보류)
FAISS 코퍼스 + "첫 검색이 부족하도록" 유도한 질문셋이 있어야 재검색 전/후를 잼
→ **코퍼스 구축 후 측정** (지금은 코퍼스가 비어 정직하게 측정 불가)
