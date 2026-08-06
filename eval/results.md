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

> ⚠️ **이 수치가 그래프의 동작을 뜻하지 않음 (정정).** `run_qa_eval.py`는 LangGraph를
> 우회해 `generate_answer`를 직접 호출하고, 논문도 `retrieve`가 아니라 JSON 픽스처에서
> 받음. 즉 `check_sufficiency` → 재작성 루프 → `give_up` 경로는 **평가에서 한 번도
> 실행되지 않음**. unanswerable 2건은 "맞는 논문을 찾았는데 초록에 그 사실만 없는" 유형인데,
> 실제 그래프에서는 이 질문이 `sufficient=False`로 판정돼 재작성을 소진한 뒤 항복할
> 가능성이 있음 — 그 경우 사용자에게는 "근거를 찾지 못했다"가 나가고, 여기서 측정한
> 정직한 항복 문구는 나오지 않음. **그래프를 통과시키는 평가가 별도로 필요**

## 4. 자기교정 발동·개선폭 — self-RAG 재검색 (미측정)
FAISS 코퍼스 + "첫 검색이 부족하도록" 유도한 질문셋이 있어야 재검색 전/후를 잼

> **측정 가능해짐 (정정).** "코퍼스가 비어 측정 불가"라고 적었던 것은 낡은 기록 —
> 현재 코퍼스는 60편 이상이고 주제가 4개(diffusion / RAG / efficient attention /
> quantum error correction)로 비교적 깔끔히 갈려 있어, `metadata.json` 제목만 보고도
> 사람이 "코퍼스 안 / 인접하지만 없음 / 아예 없음"을 라벨링할 수 있음

## 5. 의도 분류 정확도 — Orchestrator (미측정)
라우팅 정확도를 지키는 장치가 아직 없음. ADR-019에서 20회 표본 15% 오분류가 관측됐고,
실사용에서도 재현 가능한 경계 케이스를 확보함

| 입력 | 정답 | 실제 |
| --- | --- | --- |
| `확산 모델의 추론 속도를 높이는 방법은?` | query | **search (반복 재현)** |
| `확산 모델의 추론 속도를 높이는 방법은 뭐야?` | query | query |
| `RAG에서 환각을 줄이려면 어떤 방법을 쓰나?` | query | 15% 오분류 (ADR-019) |

> **차이가 어미 하나** — 명사구로 끝나면 "그 주제를 찾아봐"로도 읽혀 문장 자체가 애매.
> 프롬프트를 고치지 않은 이유는 개선 여부를 확인할 측정 장치가 없고, ADR-013(프롬프트
> 강화 → recall 1.00→0.25 붕괴) 선례가 있기 때문. 순서는 **평가셋 → baseline → 개선 →
> 재측정**. 데이터셋은 명확 query 3~4 + 명확 search 3~4 + **경계 4~5**로 구성해야 하며,
> 쉬운 것만 넣으면 100%가 나와 거짓 안심을 하게 됨
