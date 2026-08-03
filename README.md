# PaperPilot

논문 주제를 검색해 관련 논문을 찾고, 근거 기반으로 질의응답하는 **순차 멀티 에이전트** 연구 어시스턴트

> 설계 문서는 [docs/architecture.md](docs/architecture.md) 참고

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
| 서빙 | FastAPI (Router-Controller, LangGraph 엔진을 감싸는 HTTP 어댑터) |

## 프로젝트 구조
```
app.py              # FastAPI 진입점 (HTTP 어댑터)
src/
├── main.py         # CLI 진입점 (graph.invoke)
├── config.py       # 코퍼스 경로 설정
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
eval/               # 평가 하네스 (검색·Critic·QA scorecard)
tests/              # 유닛·통합 테스트 (pytest)
data/               # FAISS 인덱스 + 논문 메타데이터
```

## 실행

**설치**
```bash
pip install -r requirements.txt
cp .env.example .env   # ANTHROPIC_API_KEY 입력
```

**API 서버**
```bash
PYTHONPATH=src uvicorn app:app --port 8000 --workers 1
```
브라우저에서 `http://localhost:8000/docs` — Swagger UI로 바로 시연 가능

> `--workers 1` 필수 — 코퍼스 쓰기를 프로세스 내 락으로 보호하므로 워커가 여럿이면 락이 무효

**CLI**
```bash
PYTHONPATH=src python src/main.py "RAG에서 환각을 줄이는 방법은?"
```

**테스트**
```bash
pytest
```

## API

| 엔드포인트 | 용도 |
| --- | --- |
| `POST /ask` | 논문 검색 요청 또는 질의응답 (**Orchestrator가 의도를 판단해 라우팅**) |
| `GET /health` | 헬스체크 |

요청·응답 예시
```jsonc
// POST /ask
{ "question": "RAG에서 환각을 줄이는 방법은?" }

// 200 OK
{
  "intent": "query",              // Orchestrator의 판단 (search / query)
  "answer": "...[2510.22344v1]...",
  "papers": [{ "paper_id": "2510.22344v1", "title": "FAIR-RAG: ..." }],
  "grounded": true,               // Critic 근거 검증 통과 여부
  "search_retries": 1,            // QA가 재검색한 횟수 (self-RAG)
  "critic_runs": 1,               // Critic 검증 횟수 (1 = 한 번에 통과)
  "gave_up": false,
  "give_up_reason": null
}
```

`search_retries`·`critic_runs`·`grounded`를 응답에 노출해 **에이전트의 자기교정·검증 과정이 밖에서 보이도록** 구성

| 상태 코드 | 상황 |
| --- | --- |
| 200 | 답변 성공 또는 **정직한 항복**(`gave_up: true`) |
| 422 | 입력 형식 오류 |
| 503 | LLM 서비스 접근 불가 |

> arXiv 장애는 500이 아니라 **200 + 항복 메시지** — 시스템은 정상 동작했고 외부 검색만 실패한 상황이므로

## 알려진 한계

- **의도 분류 오분류** — `temperature=0`으로 줄였으나 20회 표본에서 15% 잔존. 질문을 검색 요청으로 오분류하면 논문 목록이 반환됨
- **코퍼스 밖 주제는 답변 불가** — 재검색 상한 후 정직하게 항복. 질의응답 중 자동 수집은 Future Work
- **초록에 없는 세부사항 답변 불가** — 초록 레벨 MVP이므로 PDF 전문 파싱은 Non-Goal
- **단일 워커 전제** — 코퍼스 쓰기를 프로세스 내 락으로 보호. 스케일 아웃 시 벡터 DB 이전 필요

## 문서
- [docs/architecture.md](docs/architecture.md) — Goals/Non-Goals, Agent Design, Design Decisions
- [docs/decisions.md](docs/decisions.md) — ADR
- [docs/evaluation.md](docs/evaluation.md) — 평가 방법
- [eval/results.md](eval/results.md) — 측정 결과

---
## 회고
[PaperPilot 회고 벨로그](https://velog.io/@dan9872/series/PaperPilot-%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8-multi-agent-%ED%94%84%EB%A1%9C%EC%A0%9D%ED%8A%B8)
