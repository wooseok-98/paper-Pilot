# PaperPilot — 평가 & 테스트 계획

`architecture.md`의 Evaluation 섹션을 **실행 가능한 계획**으로 구체화한 문서
"무엇을 · 왜 · 어떻게" 검증·측정할지 정리 — 코딩 착수 전 기준선

---

## 1. 두 종류의 검증 — 목적이 다름

"테스트"라는 말에 서로 다른 두 가지가 섞여 있음 — 분리해서 다룸

| 구분 | 유닛 테스트 (Correctness) | 평가 (Performance) |
| --- | --- | --- |
| 질문 | "코드가 **맞게 동작**하는가" | "에이전트가 **실제로 효과** 있는가" |
| 도구 | `pytest` | 자체 평가 하네스 + 골드셋 |
| 대상 | 순수 함수 (분기·병합 로직) | 검색·RAG·자기교정·Critic |
| 산출물 | pass/fail (수치 아님) | **지표 수치** (%, 개선폭) |
| 목적 | 회귀 방지, 리팩터 안전망 | 설계 결정의 증거 |
| 포트폴리오 기여 | 엔지니어링 규율 | **증거 기반 + 개선 수치** |
| 단계 | Tier 0 (지금) | Tier 1 (다음) |

> **핵심:** "자기교정 후 X%→Y%" 같은 **수치는 평가(2절)에서만** 나옴 — 유닛 테스트는 수치가 아니라 안전망

---

## 2. 유닛 테스트 (pytest) — Correctness

LLM·네트워크·파일 없이 입력→출력이 결정적인 **순수 함수**부터 (mock 불필요)

| 함수 | 위치 | 검증 케이스 |
| --- | --- | --- |
| `merge_by_paper_id` | `researcher.py` | 중복 `paper_id` 병합, 순서·개수 |
| `route_intent` | `graph.py` | `search`→researcher / `query`→retrieve |
| `route_sufficiency` | `graph.py` | 충분→생성 / 부족+재시도<상한→rewrite / 상한→give_up |
| `route_grounding` | `graph.py` | 근거O→END / 미근거+재시도<상한→재생성 / 상한→give_up |
| `give_up_node` | `graph.py` | `sufficient` 여부 → `insufficient`/`ungrounded` |

**후속(현재 제외):** LLM 호출 함수(`classify_intent`·`check_sufficiency`·`filter_relevant`·`check_grounding`)는 `monkeypatch`로 LLM 응답을 mock해서 분기·파싱만 검증

**알려진 제약:** `graph.py`/`researcher.py` import 시 임베딩 모델 로딩·Anthropic 클라이언트 생성이 **import 시점에 실행**됨 → 순수 함수 테스트도 무거움·env 의존. 정리 후보(면접 소재: import 부작용과 테스트 용이성)

**실행:** `PYTHONPATH=src pytest` 또는 `tests/conftest.py`로 `src`를 `sys.path`에 추가

---

## 3. 평가 (Performance) — 수치가 나오는 곳

`architecture.md`의 지표 4개를 측정 방법까지 구체화
**공통 원칙:** 자기교정/검증 **OFF(baseline) vs ON** 을 비교해 "그 장치가 실제로 개선했는가"를 수치로 증명

### 3.1 검색 관련도 — Researcher · Retriever
- **지표:** Precision@k (반환 논문 중 주제에 적합한 비율)
- **측정:** 주제 쿼리 → 상위 k개 중 정답 라벨과 일치 비율
- **비교:** CRAG 필터 OFF(원본 검색) vs ON(필터 후), 대체 쿼리 OFF vs ON
- **기대 서사:** 오염(precision)·누락(recall) 대응이 관련도를 얼마나 올렸는가

### 3.2 RAG 근거 일치 — QA
- **지표:** Groundedness (답변 주장이 초록에 근거한 비율), Hallucination rate
- **측정:** 고정 질문셋 → 답변 생성 → 각 주장 ↔ 초록 대조 (사람 라벨 + LLM-judge 보조)
- **비교:** 근거 강제 프롬프트(`ANSWER_SYSTEM`) 유무

### 3.3 자기교정 효과 — Self-RAG / CRAG
- **지표:** 재검색 발동률, 재검색 **전/후 관련도·충분성 개선폭**
- **측정:** 첫 검색 결과 vs 재검색 후 결과의 3.1 지표 차이

### 3.4 Critic 효과 — Reflection
- **지표:** 반려율, **심은-환각 검출률**, 반려 후 근거 일치 개선폭
- **측정:** 근거 없는 주장을 의도적으로 심은 답변셋 → 검출 수 / 심은 수 (이미 3/3 검출 실증 → 데이터셋으로 수치화)
- **비교:** Critic OFF(초안 그대로) vs ON(반려·재생성 후) 의 3.2 근거 일치율

---

## 4. 평가 데이터셋

재현 가능한 **소규모 골드셋** — json 파일로 고정 (시드·질문 고정)

| 파일 | 내용 | 규모(초기) |
| --- | --- | --- |
| `eval/topics.json` | 주제 쿼리 → 관련 `paper_id` 정답 라벨 | 주제 3~5 |
| `eval/questions.json` | 질문 → 근거 초록·정답 라벨 | 질문 10~15 |
| `eval/hallucinated.json` | 환각 심은 답변 + 심은 주장 목록 (Critic용) | 5~8 |

- 작게 시작 — 손 라벨 감당 가능한 규모, 필요 시 확장
- **LLM-judge는 보조** — 근거 일치 자동 채점에 쓰되 일부 사람 검수 병행 (judge 자체의 오류 감안)

---

## 5. 측정 하네스 (구현은 Tier 1)

- **runner 스크립트:** 데이터셋 로드 → 그래프/도구 실행 → 지표 집계 → 결과 표(csv/markdown)
- **baseline 토글:** 자기교정·Critic을 끄고 켜서 before/after 비교 (핵심 수치)
- **산출 예시:**

  | 지표 | Baseline | 자기교정 ON | 개선 |
  | --- | --- | --- | --- |
  | 검색 관련도 (P@5) | — | — | — |
  | 근거 일치율 | — | — | — |
  | 환각 검출률 | — | — | — |

---

## 6. 진행 순서

| 단계 | 작업 | 산출 |
| --- | --- | --- |
| **지금 (Tier 0)** | 순수 함수 pytest | 회귀 안전망 (수치 X) |
| **다음 (Tier 1)** | 골드셋 + 측정 하네스 | **before/after 수치** |
| 이후 | LLM 함수 mock 테스트 | 분기·파싱 회귀 방지 |

---

## 7. 포트폴리오 연결
- **수치 문장:** "CRAG 필터로 검색 관련도 P@5 X%→Y%", "Critic이 심은 환각 N/N 검출"
- **증거 기반 서사:** 각 자율 장치(대체쿼리·필터·self-RAG·Critic)를 OFF/ON 비교로 **효과를 실측** → 이 프로젝트가 지켜온 "검증 없이 확정 안 함" 원칙의 완결
- **PDF 승격 정당화:** 3.2 근거 일치가 초록만으로 낮게 나오면 → PDF 전문 인덱싱(Tier 2)의 실측 근거
