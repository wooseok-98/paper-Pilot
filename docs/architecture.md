# PaperPilot — Design Doc

논문 주제를 검색해 관련 논문을 찾고, 질의응답·요약을 제공하는 **순차 멀티 에이전트 연구 어시스턴트**

---

## Overview

연구자가 새 분야를 조사할 때 반복하는 흐름 — **검색 → 스크리닝 → 정독 → 검증** — 중 앞단(검색·스크리닝·근거 기반 질의응답)을 자동화

논문 초록(abstract) 레벨의 RAG를 기본으로 하고, Orchestrator가 사용자 의도에 따라 처리 경로를 라우팅

**설계 원칙:** 각 노드는 단순 함수·LLM 1회 호출이 아니라 **결과를 보고 스스로 다음 행동을 결정하는 에이전트** (리트머스: "결과를 보고 자기 행동을 바꾸는가?")

---

## Goals / Non-Goals

### Goals
- 주제 검색 → 관련 논문 목록·초록·메타데이터 수집
- 초록 기반 RAG 질의응답
- 의도별 라우팅 (Orchestrator)
- 각 노드의 자기교정(self-correction) 루프
- 생성 답변의 근거 검증(Critic) — 환각 억제

### Non-Goals (→ Future Work)
- **PDF 전문(full-text) 파싱·인덱싱** — 다운로드·파싱·청킹은 별도 하위 시스템 → v2 (초록으로 스크리닝 후 선택 논문만 정독하는 2단 구조 전제)
- **전문 기반 요약** — 초록은 이미 요약이라 가치 낮음, 전문 확보 후 승격
- **병렬 fan-out** (하위주제 분해 → Researcher N개 동시 실행) — 순차로 핵심 루프 검증 후 확장
- 논문 저장·라이브러리 관리 UI 고도화

---

## Architecture

```
                         [사용자 질문]
                             │
                             ▼
                   ┌───────────────────┐
                   │    Orchestrator   │   Layer 1: 라우팅
                   └─────────┬─────────┘
                       의도 분류로 분기
              ┌──────────────┴──────────────┐
              ▼                             ▼
      ┌───────────────┐             ┌───────────────┐
      │   Researcher  │             │      QA       │   Layer 2: 작업 워커
      │  검색 자기교정 ⟳ │             │  self-RAG ⟳   │   (둘 중 하나로 라우팅)
      └───────┬───────┘             └───────┬───────┘
              │ 논문 저장                     │ 초안 답변
              │                             ▼
              │                     ┌───────────────┐
              │                     │     Critic    │   Layer 3: 근거 검증
              │                     │   검증 반려 ⟳   │◀─┐
              │                     └───────┬───────┘  │ 미근거 → QA 재작성
              │                             │ 통과      │
              │                             └──────────┘
              │                             │    
              ▼                             ▼
                        [사용자에게 응답]
```

- **Orchestrator**: 요청을 `search`(검색·저장) / `query`(질의응답)로 분류해 워커로 라우팅
- **Layer 2 (Researcher·QA)**: Orchestrator가 의도 보고 **둘 중 하나** 선택하는 형제 워커
- **Layer 3 (Critic)**: 라우팅 대상이 아니라, QA가 답을 만들면 **그 뒤에 자동으로 붙어** 근거를 검사하는 리뷰어
- **각 노드의 `⟳`**: 결과를 평가해 필요하면 스스로 재시도하는 자기교정 루프

---

## Agent Design

각 노드가 "에이전트"인 근거 — **결과를 보고 스스로 다음 행동을 결정** (없으면 정적 파이프라인·도구)

| 에이전트 | Layer | 자율 행동 | 패턴 |
| --- | --- | --- | --- |
| **Orchestrator** | 1 | 의도 분류 → 워커 라우팅 | Routing |
| **Researcher** | 2 | 검색 결과가 의도와 어긋나면 **쿼리를 수정해 재검색** | Self-correction |
| **QA** | 2 | 검색된 초록으로 답변 가능한지 판정, 부족하면 **쿼리 재작성 후 재검색** | Self-RAG / CRAG |
| **Critic** | 3 | 답변이 초록에 실제 근거 있는지 채점, 미근거면 **QA에 재작성 반려** | Reflection / Generator-Critic |

> **Researcher 자기교정 근거:** arXiv 기본 검색은 단어를 넓게 매칭 — `"stable diffusion"` 검색 시 물리학 diffusion 논문이 혼입되는 문제를 실제로 확인. 정적 쿼리로는 해결 불가하므로 결과 평가 후 재검색하는 에이전트 구조가 필요

> **QA self-RAG 근거:** 검색 한 번 후 무조건 답하면 정적 RAG 함수 — 근거 부족 시 재검색하는 판단 루프가 있어야 에이전트. LLM grader가 **관련성·충분성**을 채점해 재검색 여부 결정

> **Critic 근거:** 초록 기반이라 "이 주장이 초록에 실제로 있나"를 검증하기 자연스러움. 답변 생성 후 근거 일치·환각 여부를 채점해 반려하는 Reflection 루프. MVP는 **QA 답변만** 검증(Researcher는 저장이 주 업무라 환각 위험 낮음), 후속으로 Researcher 요약까지 확장 가능

---

## Components

| 컴포넌트 | 계층 | 책임 |
| --- | --- | --- |
| **Orchestrator** | 에이전트 | 의도 분류 → 라우팅 |
| **Researcher** | 에이전트 | 논문 검색 + 결과 평가 → 쿼리 자기교정 → 저장 |
| **QA** | 에이전트 | 검색 충분성 판단 → 재검색 or 근거 기반 답변 |
| **Critic** | 에이전트 | 답변 근거 검증 → 통과 or QA 반려 |
| Ingestor (`ingest.py`) | 도구 | 초록·메타데이터 임베딩 → 벡터 DB (`paper_id` 태깅) |
| Retriever (`retriever.py`) | 도구 | 벡터 유사도 검색 (메타데이터 필터 지원) |
| Embedder (`embedding.py`) | 도구 | 문장 → 벡터 |
| arXiv API (`search.py`) | 도구 | 논문 검색 |
| LLM (`llm.py`) | 도구 | Claude API 래퍼 (모든 에이전트 공용 판단 창구, 구조화 출력) |

---

## Key Flows

### 1. 검색 (Researcher)
```
쿼리 → arXiv 검색 → 결과 평가 (의도와 맞나?)
                        ├ 부적합 → 쿼리 수정 → 재검색 (최대 N회)
                        └ 적합 → Ingestor (초록·메타데이터 임베딩 → DB)
```

### 2. 질의응답 (QA → Critic)
```
질문 → Retriever 검색 → grader: 관련성·충분성 판단
                          ├ 부족 → 쿼리 재작성 → 재검색 (최대 N회)
                          └ 충분 → 근거 기반 답변 생성 → Critic 검증
                                     ├ 미근거 → QA 재작성 (최대 N회)
                                     └ 통과 → 응답
```

> **루프 종료 조건:** 모든 자기교정·검증 루프는 재시도 상한(`max_retries`)을 두어 무한 반복 방지. 상한 도달 시 "정보 부족" 등 정직하게 항복

---

## Tech Stack

| 영역 | 선택 |
| --- | --- |
| 오케스트레이션 | LangGraph (조건부 라우팅 + 자기교정 사이클 표현) |
| LLM | Claude API (tool use, 구조화 출력) |
| 논문 검색 | arxiv (Semantic Scholar는 후속) |
| 임베딩 | sentence-transformers `all-MiniLM-L6-v2` (영어) |
| 벡터 DB | FAISS (인덱스 + 메타데이터 JSON) |
| 서빙 | FastAPI (Router-Controller — LangGraph 엔진을 그대로 감싸는 얇은 HTTP 어댑터) |

---

## Design Decisions

| 결정 | 선택 | 근거 |
| --- | --- | --- |
| 문서 단위 | **초록 기반** | PDF 파싱 비용 회피, 스크리닝엔 초록으로 충분 |
| 검색 소스 | **arXiv** | 공식 무료 API, Google Scholar는 크롤링 필요해 배제 |
| 임베딩 모델 | **영어 모델로 교체** | 기존 RAG 챗봇은 한국어 모델(`ko-sroberta`) 사용, 논문 초록은 영어이므로 언어 정합성 필요 |
| 벡터 DB | **FAISS** | 기존 RAG 챗봇 스택 재사용 (인덱스+메타 JSON 패턴) |
| 노드 설계 | **에이전트 우선** | 단순 도구·LLM 체인이 아닌 자기교정 루프 보유 (리트머스 통과) |
| 조율 방식 | **순차 라우팅 + Critic** | 병렬 fan-out 없이도 자율 루프 3개(Researcher·QA·Critic)로 멀티 에이전트 성립. 병렬은 복잡도 대비 이득이 MVP 스코프엔 불필요 |
| 검증 노드 | **Critic 추가** | 초록 기반 답변의 환각 억제, "RAG 환각 어떻게 막나" 대응. Reflection 패턴 |
| Comparator | **제외** | 자기교정 루프 없는 정적 LLM 체인 → 가짜 에이전트. 필요 시 루프 넣어 후속 부활 |
| 서빙 방식 | **Streamlit → FastAPI로 변경** | 최종 목표가 API 서비스라 Streamlit은 나중에 버릴 코드가 됨(YAGNI 위배). 그래프는 CLI 스모크 테스트(`graph.invoke()` + print)로 UI 없이 먼저 검증하고, 완성 후 FastAPI Router-Controller를 얇은 HTTP 어댑터로 씌움 — LangGraph 엔진 자체는 그대로 재사용 |

> 상세 결정 기록은 `docs/decisions.md` (ADR — 결정 시마다 누적)

---

## Evaluation

| 지표 | 측정 |
| --- | --- |
| 검색 관련도 | 주제 쿼리 대비 반환 논문 적합률 (자기교정 전/후 비교) |
| RAG 정확도 | 질의응답의 근거 일치 / 환각 여부 |
| 자기교정 효과 | 재검색 발동률, 재검색 후 개선폭 |
| Critic 효과 | 반려율, 반려 후 근거 일치 개선폭 |

---

## Future Work
- **PDF 전문 인덱싱 + 전문 기반 요약** — 심층 질의응답 (Non-Goal에서 승격)
- **병렬 fan-out** — 넓은 질문을 하위주제로 분해해 Researcher N개 동시 실행 + Synthesizer 병합 (LangGraph `Send` map-reduce)
- **Comparator 부활** — 비교표 빈칸 감지 시 추가 검색하는 자기교정 루프 부여
- 쿼리 확장(유의어), 다중 소스 폴백 (Semantic Scholar — 인용 그래프 확보)
- **임베딩 모델 파인튜닝** — `all-MiniLM-L6-v2`를 논문 도메인에 맞게 대조학습(contrastive learning)으로 파인튜닝(`sentence-transformers` `MultipleNegativesRankingLoss`). 학습 데이터는 arXiv 자체에서 라벨링 없이 구성(제목=anchor, 초록=positive, 또는 인용 관계). **동기:** 스파이크에서 실증한 어휘 불일치 문제(`"stable diffusion"` 검색이 원조 논문 "Latent Diffusion Models"를 못 찾음) 직접 해결. **검증:** Evaluation의 "검색 관련도" 지표로 파인튜닝 전/후 비교. SPECTER/SPECTER2(논문 특화 사전학습 임베딩) 대비 성능도 참고 가능
- **FastAPI 서빙** — 그래프 완성·CLI 검증 후, Router-Controller를 얇은 어댑터로 씌워 HTTP API화. `graph.astream()`으로 에이전트 중간 진행 상황(검색 중/검증 중 등) 스트리밍 고려
