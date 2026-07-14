# PaperPilot

논문 주제를 검색해 관련 논문을 찾고, 근거 기반으로 질의응답하는 **순차 멀티 에이전트** 연구 어시스턴트

> 개발 진행 중 — 설계는 [docs/architecture.md](docs/architecture.md) 참고

## 아키텍처

```
사용자 질문 → Orchestrator (라우팅)
                 ├ search → Researcher (검색 자기교정 ⟳) → 저장
                 └ query  → QA (self-RAG ⟳) → Critic (근거 검증 ⟳) → 응답
```

각 노드는 단순 함수 호출이 아니라 **결과를 보고 스스로 다음 행동을 결정하는 에이전트**

| 에이전트 | 역할 |
| --- | --- |
| Orchestrator | 의도 분류 → Researcher/QA 라우팅 |
| Researcher | arXiv 검색 → 결과 부적합하면 쿼리 수정 후 재검색 |
| QA | 검색된 초록으로 self-RAG 질의응답, 근거 부족하면 재검색 |
| Critic | 생성된 답변이 초록에 실제 근거하는지 검증, 미근거면 QA에 반려 |

## 주요 기능
- 주제 검색 → 관련 논문 목록·초록·메타데이터 수집 (arXiv)
- 초록 기반 RAG 질의응답 (Self-RAG / CRAG)
- 답변 근거 검증으로 환각 억제 (Reflection)

## 기술 스택

| 영역 | 선택 |
| --- | --- |
| 오케스트레이션 | LangGraph |
| LLM | Claude API |
| 논문 검색 | arXiv API |
| 임베딩 | sentence-transformers (`all-MiniLM-L6-v2`) |
| 벡터 DB | FAISS |
| UI | Streamlit |

## 프로젝트 구조
```
src/
├── search.py       # arXiv 검색
├── embedding.py    # 문장 → 벡터
├── ingest.py       # 임베딩 → FAISS 저장
├── retriever.py    # FAISS 벡터 검색
├── llm.py          # Claude API 래퍼
├── graph.py        # LangGraph 배선
└── agents/
    ├── orchestrator.py
    ├── researcher.py
    ├── qa.py
    └── critic.py
```

## 실행
```bash
pip install -r requirements.txt
cp .env.example .env   # API 키 입력
```

## 문서
- [docs/architecture.md](docs/architecture.md) — Goals/Non-Goals, Agent Design, Design Decisions
