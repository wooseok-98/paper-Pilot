# Architecture Decision Records (ADR)

결정을 **시간순으로 누적**하는 로그.
상세 설계 근거는 `architecture.md` 참조.

---

## 목차

**에이전트 아키텍처**
- [ADR-001](#adr-001) 순차 멀티 에이전트 재설계
- [ADR-002](#adr-002) 임베딩 모델 영어(all-MiniLM-L6-v2)로 교체
- [ADR-003](#adr-003) 서빙 Streamlit → FastAPI 변경
- [ADR-004](#adr-004) 누락(recall) 대응: 첫 검색 시 대체 쿼리 병행
- [ADR-005](#adr-005) 오염(precision) 대응: 쿼리 재작성 → 결과 필터링(CRAG) 전환
- [ADR-006](#adr-006) QA: self-RAG — 쿼리 재작성 후 재검색
- [ADR-007](#adr-007) Critic Reflection — 근거 누락 피드백 새 프롬프트 적용
- [ADR-008](#adr-008) 그래프 노드 분해 — QA: 다중 노드, Researcher: 단일 노드
- [ADR-009](#adr-009) 데이터: 덮어쓰기 → 누적 저장

**평가·스코프**
- [ADR-010](#adr-010) 평가 정답지: 사람 라벨 (LLM 채점 순환 회피)
- [ADR-011](#adr-011) 그래프 테스트: LLM을 mock한 통합 테스트
- [ADR-012](#adr-012) CRAG 필터 프롬프트 강화 시도 → baseline 복구
- [ADR-013](#adr-013) 검색 성능보다 에이전트 완성 우선
- [ADR-014](#adr-014) "원논문+중요 논문" 목표 — 인용 신호 필요 → arXiv 불가
- [ADR-015](#adr-015) S2 인용 그래프 큐레이션 스코프아웃 (v2)
- [ADR-016](#adr-016) S2 사용 시 paper_id S2 ID로 통일
- [ADR-017](#adr-017) 완성 우선 — end-to-end 데모 → UI → 배포

**Phase 1 검증·프로덕션 하드닝**
- [ADR-018](#adr-018) `call_structured`에 temperature=0 고정
- [ADR-019](#adr-019) Researcher 재검색 루프 — 검색 범위를 회차마다 확장
- [ADR-020](#adr-020) 코퍼스 동시 쓰기 보호 — 프로세스 내 락 + 임시파일 교체
- [ADR-021](#adr-021) 외부 장애 처리 위치 — arXiv: 노드, LLM: 진입점
- [ADR-022](#adr-022) 검색 입력을 요청 문장에서 영어 키워드로 분리
- [ADR-023](#adr-023) HTTP는 `/ask` 단일 엔드포인트 — Orchestrator를 우회하지 않기 위해

**배포**
- [ADR-024](#adr-024) 인증 — 포트는 열고 애플리케이션에서 토큰 검사
- [ADR-025](#adr-025) 배포 — EC2 1대 + Docker + 호스트 볼륨, ARM(t4g) 선택
- [ADR-026](#adr-026) 이미지 구성 — CPU 전용 torch, 임베딩 모델 사전 탑재
- [ADR-027](#adr-027) UI — 정적 HTML 한 장을 FastAPI가 서빙

---

<a id="adr-001"></a>
## ADR-001: 순차 멀티 에이전트 재설계
- **맥락:** 초기엔 Searcher/QA/Comparator 라우터 구조
- **결정:** **Orchestrator → Researcher** / **Orchestrator → QA → Critic** 순차 멀티 에이전트로 전환. Comparator는 제외
- **근거:** "결과를 보고 자기 행동을 바꾸는가?"로 판정 — Comparator는 자기교정 루프 없는 정적 LLM 체인(가짜 에이전트) → 제거 (노드는 도구·1회 호출이 아니라 자기교정하는 에이전트여야 함)

<a id="adr-002"></a>
## ADR-002: 임베딩 모델 영어(all-MiniLM-L6-v2)로 교체
- **맥락:** 기존 RAG 챗봇은 한국어 모델(`ko-sroberta`) 사용
- **결정:** 논문 초록이 영어이므로 **영어 모델**로 교체
- **근거:** 쿼리↔초록 언어 정합성

<a id="adr-003"></a>
## ADR-003: 서빙 Streamlit → FastAPI 변경
- **맥락:** 초기 서빙 계획은 Streamlit
- **결정:** **FastAPI (Router-Controller, 얇은 HTTP 어댑터)** 로 변경
- **근거:** 최종 목표가 API 서비스라 Streamlit 배제, 그래프는 CLI 스모크 테스트로 UI 없이 먼저 검증

<a id="adr-004"></a>
## ADR-004: 누락(recall) 대응: 첫 검색 시 대체 쿼리 병행
- **맥락:** 검색 누락(원조 논문을 못 찾음) 대응
- **결정:** 결과를 보고 재검색하는 **반응형이 아니라**, 처음부터 원본 + LLM이 제안한 대체 용어를 **병행 검색**해 병합
- **근거:** 결과만 보는 자기교정은 "애초에 없는 논문"을 못 알아챔. `expand_query` 단발 호출로 충분

<a id="adr-005"></a>
## ADR-005: 오염(precision) 대응: 쿼리 재작성 → 결과 필터링(CRAG) 전환
- **맥락:** `"stable diffusion"` 검색에서 재료과학 등 오염 발견. 첫 설계는 "결과 평가 → `revised_query` 재검색"
- **결정:** 쿼리 재작성 대신 **결과 필터링(`filter_relevant`, CRAG)** 으로 전환
- **근거:** LLM이 만든 `NOT ...` 제외 쿼리를 **arXiv가 지원 안 함** → 5회 재시도 전부 실패 후 오염 저장 → arXiv(통제 불가) 대신 **결과 필터(코드 통제)** 로 이동. 저장은 통과분만 진행

<a id="adr-006"></a>
## ADR-006: QA: self-RAG — 쿼리 재작성 후 재검색
- **맥락:** 검색된 초록으로 무조건 답하면 정적 RAG
- **결정:** 관련성·충분성을 채점해 **부족하면 쿼리 재작성 후 재검색**하는 self-RAG 루프
- **근거:** Researcher(arXiv)와 달리 QA는 **우리 FAISS 코퍼스**를 검색 → 쿼리를 바꾸면 임베딩이 바뀌어 실제 응답에 필요한 다른 논문 반환 (교정 행동이 결과를 실제로 바꿈)

<a id="adr-007"></a>
## ADR-007: Critic Reflection — 근거 누락 피드백 새 프롬프트 적용
- **맥락:** 답변 생성 후 근거 검증(환각 억제)
- **결정:** `issues`(구체적 지적)를 `generate_answer(feedback=...)`로 전달해 **다음 생성 프롬프트에 반영**
- **근거:** 같은 입력으로 재생성하면 같은 환각 반복 → **교정이 입력을 실제로 바꿔야** 재시도가 의미 (초기 `{revision}` 프롬프트 누락으로 피드백 전달 안 된 버그 겪음)
- **실증:** 심은 환각 3개 모두 검출 → 재생성 후 통과

<a id="adr-008"></a>
## ADR-008: 그래프 노드 분해 — QA: 다중 노드, Researcher: 단일 노드
- **맥락:** LangGraph `StateGraph` 배선 시 에이전트별 노드화 정도
- **결정:** **QA는 4노드로 펼침**(retrieve·check_sufficiency·rewrite_query·generate_answer), **Researcher는 1노드**
- **근거:** 기준 "다른 에이전트와 연결 시 다중 노드, 독립적일 시 단일 노드" — QA의 self-RAG는 Critic 사이클과 얽힘, Researcher CRAG는 독립

<a id="adr-009"></a>
## ADR-009: 데이터: 덮어쓰기 → 누적 저장
- **맥락:** `ingest_papers`가 매번 새 인덱스를 만들어 덮어씀 → 새 주제 조사 시 이전 논문 소실
- **결정:** `faiss.read_index()`로 기존 인덱스에 `add`, 메타데이터도 이어붙임 (paper_id로 중복 제거)

---

<a id="adr-010"></a>
## ADR-010: 평가 정답지: 사람 라벨 (LLM 채점 순환 회피)
- **맥락:** CRAG 필터가 잘 작동하는지 precision으로 재려면 "정답(관련/무관)"이 필요
- **결정:** 후보 논문을 **사람이 직접 라벨**. LLM 자동 라벨은 배제
- **근거:** 평가 대상(`filter_relevant`)이 LLM인데 채점도 LLM이면 **자기 채점 순환** → 무의미

<a id="adr-011"></a>
## ADR-011: 그래프 테스트: LLM을 mock한 통합 테스트
- **결정:** 순수 함수는 `parametrize` 유닛 테스트 + **LLM을 `monkeypatch`로 mock해 컴파일된 그래프를 `invoke`하는 통합 테스트**
- **근거:** LangGraph의 진짜 리스크는 개별 함수가 아니라 **조건부 엣지 배선·루프·종료** → 실제로 돌려 경로 검증. LLM 판단(비결정)은 유닛이 아니라 평가 영역

<a id="adr-012"></a>
## ADR-012: CRAG 필터 프롬프트 강화 시도 → baseline 복구
- **맥락:** baseline **precision 0.44 / recall 1.00 / F1 0.61**. 오답 통과 5개(SD를 다른 태스크·도메인에 응용)
- **결정(1차):** 프롬프트를 "핵심 기여가 검색 대상이 아니면 제외"로 강화
- **결과:** precision 0.50이지만 **recall 1.00→0.25 붕괴, F1 0.61→0.33** (과잉교정). 생성적 응용까지 버림
- **결정(수정):** **baseline 원복.** 근본 원인은 관련성이 검색어만으론 underspecified → scope 명시화가 해법이나 우선순위상 v2 ([[ADR-015]])

<a id="adr-013"></a>
## ADR-013: 검색 성능보다 에이전트 완성 우선
- **결정:** **에이전트 완성(데모·서빙·배포) 우선.** 검색은 "충분히 좋음"으로 잠금
- **근거:** 프로젝트 정체성 멀티 에이전트 구현. 우선순위 구현

<a id="adr-014"></a>
## ADR-014: "원논문+중요 논문" 목표 - 인용 신호 필요 → arXiv 불가
- **맥락:** "이미지 생성 분야 diffusion의 **원논문 + 중요 파생 논문**" 요구 등장
- **결정:** 이 목표는 **인용 신호**가 있어야 가능 → arXiv 불가, Semantic Scholar 필요
- **근거:** arXiv는 텍스트 관련도만 정렬, **인용수 신호 없음** → 원조 논문이 검색 상위에 안 뜸(=recall 문제). 필터는 안 가져온 걸 못 넣으므로 더 나은 필터로 해결 불가

<a id="adr-015"></a>
## ADR-015: S2 인용 그래프 큐레이션 스코프아웃 (v2)
- **맥락:** [[ADR-014]] 목표의 최적 방법 = 주제→조상(원논문)·후손(중요 파생)의 **인용 그래프 큐레이션**. `src/scholar.py` 프로토타입까지 진행
- **결정:** 설계·프로토타입 남기되 **v2 스코프아웃.** `scholar.py`는 main에 커밋하지 않고 로컬 보관
- **근거:** (1) Researcher **재설계** 규모라 에이전트 완성([[ADR-013]])이 먼저 (2) S2 무인증 rate limit(429) 리스크(코퍼스 캐싱으로 데모는 회피 가능) (3) 미배선 dead code를 포트폴리오 레포에 안 넣음

<a id="adr-016"></a>
## ADR-016: S2 사용 시 paper_id S2 ID로 통일
- **결정:** `paper_id`는 **항상 S2 paperId**. arXiv ID는 링크·PDF용 별도 필드로만 보관
- **근거:** arXiv ID는 옵셔널이라 폴백 쓰면 **ID 체계가 섞임** → 일관성 붕괴. 소스를 바꾸면 ID 체계도 통일

<a id="adr-017"></a>
## ADR-017: 완성 우선 — end-to-end 데모 → UI → 배포
- **결정:** **Phase 1 end-to-end 검증 → FastAPI → UI → 배포** 순. UI는 단일턴 먼저, 멀티턴(`checkpointer`+`thread_id`)은 옵션
- **근거:** 그래프는 지금까지 mock으로만 검증 → 실제 동작 확인 필요. 멀티턴은 별도 메모리 구현이 필요한 설계 선택

---

<a id="adr-018"></a>
## ADR-018: `call_structured`에 temperature=0 고정
- **맥락:** `call_structured`가 `temperature`를 명시하지 않아 API 기본값(1.0, 최대 무작위)으로 호출돼 `intent` 판단이 흔들림(`search`↔`query` 뒤바뀜)
- **결정:** **판단(`call_structured`)은 `temperature=0`으로 고정. 생성(`call_llm`)은 그대로 둠**(자유 텍스트 답변은 표현 다양성이 허용 범위)
- **근거:** Orchestrator·CRAG 필터·충분성 판단·근거 검증은 전부 이진/분류 판단 — 같은 입력에 같은 출력이 나와야 라우팅·재검색·반려가 예측 가능
- **한계:** `temperature=0`도 100% 결정성을 보장하진 않음(20회 표본 15% 오분류 잔존) — 상세는 아래 펼쳐보기

<details>
<summary>실측 상세 (baseline → 재검증 → 정정)</summary>

반복 10회 `Counter({'query': 10})`로 고정을 확인했으나, mock 테스트는 항상 고정값을 반환해 이 비결정성을 구조적으로 잡지 못함(#8 "손으로 쓴 가짜 답변이라 재생성이 우연히 깨끗해 테스트가 잘못된 이유로 통과"와 같은 계열) → `eval/results.md`의 기존 수치는 temperature=1.0 표본이라 재측정 필요

**정정(같은 세션):** `temperature=0`이 비결정성을 **완전히 제거하진 못함** — 표본을 20회로 늘려 재확인하니 같은 질문에 `Counter({'query': 17, 'search': 3})`(15% 오분류). 10회 표본에서 전부 `query`였던 건 우연. temperature=0도 GPU 배치 연산의 부동소수점 특성상 100% greedy가 보장되지 않는다는 것이 실측으로 드러남 → "결정적으로 고쳤다"가 아니라 "무작위성을 크게 줄였다"로 주장을 하향. 비용 비대칭이 큰 라우팅(query 오분류=답변 불가, search 오분류=단순 저장 낭비)은 temperature만으론 안전망이 부족 → 별도 안전장치(예: 프롬프트 기준 재점검, 낮은 확신 시 재분류) 검토 여지 남음
</details>

<a id="adr-019"></a>
## ADR-019: Researcher 재검색 루프 — 검색 범위를 회차마다 확장
- **맥락:** `research()`의 재시도 while 루프가 매 회차 동일한 `search_papers(query, 20)`을 호출 — arXiv는 같은 쿼리·정렬(Relevance)에 항상 같은 20건을 반환해, `merge_by_paper_id`가 전부 중복 제거하고 후보가 안 늘어남(재시도라는 이름만 있고 API만 두드리는 헛수고)
- **결정:** 요청 개수를 회차(`retries`)에 따라 **확장**: `search_papers(query, 20 * (retries + 2))` → 40, 60, 80...
- **근거:** #6(arXiv `NOT` 무시)·#8(`{revision}` 누락)과 같은 계열 — **교정 행동이 실제로 입력(요청 범위)을 바꿔야** 재시도가 의미 있음
- **한계:** 검색 범위 확장은 "존재하지만 놓친" 논문엔 유효하나, **주제 자체가 arXiv에 없는 경우**(가상 주제 테스트에서 후보 0개, 범위를 넓혀도 그대로 0)는 재시도로 해결 불가 — 풀 수 있는 실패와 풀 수 없는 실패를 구분해야 함

<details>
<summary>검증 상세</summary>

`search_papers`에 40/60/80을 직접 요청해 각각 그 개수만큼 반환됨을 확인, 실사용 쿼리(quantum error correction)로 `research()`를 돌려 1회차에 후보 41개로 증가·필터 통과 26개로 `min_results` 충족 후 종료됨을 실증
</details>

<a id="adr-020"></a>
## ADR-020: 코퍼스 동시 쓰기 보호 — 프로세스 내 락 + 임시파일 교체
- **맥락:** CLI는 1회 실행이라 문제없었으나, FastAPI 서빙은 요청마다 스레드가 붙어 `ingest_papers`(읽기→임베딩→쓰기, 인덱스·metadata 두 파일로 분리 저장)가 동시에 실행될 수 있음
- **결정:** `threading.Lock`으로 **읽기~쓰기 전체**를 감싸고, 저장은 `.tmp`에 완성한 뒤 `os.replace`로 이름을 교체
- **근거:** 쓰기만 잠그면 두 요청이 같은 값을 읽어 한쪽 작업이 통째로 사라짐

<a id="adr-021"></a>
## ADR-021: 외부 장애 처리 위치 — arXiv: 노드, LLM: 진입점
- **맥락:** arXiv와 Claude 모두 외부 서비스라 언제든 실패할 수 있는데, 예외가 `graph.invoke` 밖으로 나가면 HTTP 500이 됨
- **결정:** **arXiv 장애는 `researcher_node`에서, LLM 장애는 진입점(`main.py`/`app.py`)에서** 처리
- **근거:** 영향 범위가 다름 — arXiv가 죽어도 **QA 경로는 정상 동작**하므로 노드에서 잡아 그 경로만 항복시키는 게 맞음. LLM이 죽으면 의도 분류부터 모든 노드가 멈춰 부분 응답이 불가능하므로, 노드마다 잡으면 코드만 지저분해짐

<details>
<summary>구현 상세</summary>

`search.py`에 `SearchUnavailable`, `llm.py`에 `StructuredOutputError` 신설. arXiv 호출은 `list()`로 감싸야 함 — `.results()`가 제너레이터라 반환 시점이 아니라 **순회 시점에 예외가 나서** `try` 블록 밖으로 샘. `llm.py`에는 `timeout=30`도 명시
</details>

<a id="adr-022"></a>
## ADR-022: 검색 입력을 요청 문장에서 영어 키워드로 분리
- **맥락:** `research()`가 사용자 요청 문장을 그대로 arXiv에 넘기고 있었음. `"확산 모델 논문 찾아줘"`는 arXiv에서 약 0건이라, 실질적으로 `expand_query`가 만든 용어 하나가 10건으로 전체를 버티는 상태 — [[ADR-004]]의 "원본+대체 용어 병행 검색" 구조가 한국어 입력에서 붕괴
- **결정:** `to_search_keyword`로 **요청 문장 → 영어 검색 키워드**를 먼저 뽑고, 검색·대체 용어 확장·관련성 필터에 모두 그 키워드를 사용
- **근거:** `filter_relevant`에도 키워드를 넘긴 이유는 **baseline(precision 0.44 / recall 1.00)이 키워드로 측정된 수치**여서 — 입력 형태를 바꾸면 그 측정이 무효가 되고, 필터가 과하게 좁혀져 recall이 떨어질 위험이 있음([[ADR-012]] 선례)

<details>
<summary>영향 상세</summary>

`expand_query`도 짧은 키워드를 입력으로 가정하고 만든 프롬프트(`'stable diffusion' -> 'latent diffusion model'`)라 긴 문장을 받으면 설계와 어긋남. `arxiv.Client(page_size=max_results)`도 함께 조정 — 기본값이 100이라 10건을 원해도 arXiv에 100건을 요청하고 있었음. 첫 두 호출에서 요청량 90% 감소. 다만 429는 요청 횟수 기준이라 직접적 해결책은 아니고 API를 필요한 만큼만 쓰는 교정
</details>

<a id="adr-023"></a>
## ADR-023: HTTP는 `/ask` 단일 엔드포인트 — Orchestrator를 우회하지 않기 위해
- **맥락:** search와 query는 응답 스키마가 달라 엔드포인트를 나누는 게 자연스러워 보였음
- **결정:** **`POST /ask` 하나**로 두고, 응답에 `intent`를 실어 Orchestrator의 판단을 노출
- **근거:** 나누면 **사용자가 의도를 직접 지정**하게 되어 Orchestrator를 우회함 — 네 에이전트 중 Routing 패턴이 API 표면에서 사라짐. 응답 스키마 차이는 선택적 필드로 해소되는 수준

<details>
<summary>영향 상세</summary>

응답에 `search_retries`·`critic_runs`·`grounded`를 함께 노출해 **자기교정과 근거 검증이 API 밖에서 관측되게** 함. `critic_runs`는 State의 `critic_retries`를 **응답 계층에서만 개명** — `critic_node`가 첫 검증부터 세기 때문에 `1`이 "한 번에 통과"를 뜻하는데 `retries`라는 이름은 "한 번 다시 씀"으로 읽힘. 그래프는 건드리지 않고 API 이름만 정확하게
</details>

---

<a id="adr-024"></a>
## ADR-024: 인증 — 포트는 열고 애플리케이션에서 토큰 검사
- **맥락:** 배포 환경이 WiFi라 공인 IP가 바뀌고, 데모를 다른 사람이 볼 수도 있어서 보안 그룹의 "내 IP" 제한만으로는 운용이 어려움
- **결정:** **8000번은 `0.0.0.0/0`으로 열고, `/ask`만 `X-API-Token` 헤더를 검사**. SSH(22)는 내 IP 유지, `/health`는 개방
- **근거:** 인증 없이 열면 요청 1건이 LLM 최대 8회 + arXiv 호출이라 크레딧 소진·arXiv IP 차단 위험. 반대로 IP 제한만 쓰면 네트워크가 바뀔 때마다 수정해야 하고 데모 공유가 불가. `/health`를 연 것은 healthcheck가 호출해야 하고 노출되는 정보가 없기 때문
- **한계:** `PAPERPILOT_TOKEN` 미설정 시 인증이 꺼지는 설계(로컬 개발 편의)

<details>
<summary>겪은 버그</summary>

`secrets.compare_digest`는 str끼리 비교할 때 **ASCII만 허용**해 한글이 섞인 토큰이 오면 `TypeError` → 500. 인증 실패는 어떤 입력이든 401로 일관돼야 하고, 500과 401이 갈리면 공격자에게 신호가 됨 → `.encode()`로 바이트 비교. `"wrong"` 같은 ASCII 값으로만 테스트했으면 못 찾았을 버그
</details>

<a id="adr-025"></a>
## ADR-025: 배포 — EC2 1대 + Docker + 호스트 볼륨, ARM(t4g) 선택
- **맥락:** 커리큘럼에서 배운 선택지(Lambda + API Gateway, ELB, EFS, Blue/Green 등) 중 무엇을 쓸지
- **결정:** **EC2 `t4g.small`(ARM/Graviton) 1대 + Docker Compose + 호스트 볼륨 마운트**
- **근거:** **ARM을 고른 것은 빌드 머신이 Apple Silicon이라 아키텍처가 일치**하기 때문 — x86을 고르면 이미지가 `exec format error`로 실행되지 않고, 에뮬레이션 빌드는 torch 설치가 매우 느림

<details>
<summary>배제한 대안 · 영향</summary>

Lambda + API Gateway는 **API Gateway의 29초 타임아웃이 고정**이라 `research()`가 초과 / ELB는 인스턴스 1대엔 불필요하고 idle timeout 60초 함정이 있음 / EFS는 락 때문에 스케일 아웃이 불가하니 EBS로 충분 / Blue-Green·Canary는 인스턴스 여러 대가 전제

**영향:** 데이터는 이미지가 아니라 볼륨에 둠 — 이미지에 넣으면 재배포할 때마다 수집한 논문이 초기 상태로 되돌아감. `.env`도 이미지에 넣지 않음(레지스트리를 통해 유출). 결과적으로 EC2에 두는 것은 `docker-compose.yml`·`.env`·`data/` 세 가지뿐이고 코드는 전부 이미지 안에 있음
</details>

<a id="adr-026"></a>
## ADR-026: 이미지 구성 — CPU 전용 torch, 임베딩 모델 사전 탑재
- **맥락:** 첫 빌드 결과 이미지가 **8.89GB**
- **결정:** torch를 **CPU 전용 인덱스에서 먼저 설치**하고, 임베딩 모델을 `RUN`으로 이미지에 굽고, 레이어를 **의존성 → 모델 → 코드** 순으로 배치
- **근거:** 기본 torch 휠이 GPU용이라 `nvidia` 2.9GB + `triton` 652MB가 딸려옴 — GPU를 쓰지 않으므로 전부 낭비였고, **EC2 우분투의 기본 루트 볼륨이 8GB라 이대로면 물리적으로 들어가지 않음**. CPU 전용으로 바꿔 2.17GB(압축 499MB)로 축소

<details>
<summary>영향 상세</summary>

모델을 미리 받아두지 않으면 컨테이너를 띄울 때마다 90MB를 내려받고 런타임이 외부 서비스에 의존하게 됨. 레이어 순서는 코드가 가장 자주 바뀌므로 무거운 `pip install` 층이 캐시로 살아남게 하기 위함. `PYTHONUNBUFFERED=1` 추가 — 없으면 `print()` 출력이 버퍼에 갇혀 `docker logs`에 나타나지 않음. 실제로 이것 때문에 arXiv 실패 원인을 못 보고 헤맸음(예전 `python -u` 이슈가 컨테이너에서 재현). `HF_HUB_OFFLINE=1`로 모델이 이미 있는데도 허브를 조회하는 것을 차단
</details>

<a id="adr-027"></a>
## ADR-027: UI — 정적 HTML 한 장을 FastAPI가 서빙
- **맥락:** 데모용 화면이 필요한데, [[ADR-003]]에서 Streamlit을 "최종 목표가 API 서비스라 버릴 코드"로 배제한 이력이 있음
- **결정:** **정적 HTML 한 장을 FastAPI가 서빙**하고, 그 페이지가 `/ask`를 호출하는 구조
- **근거:** Streamlit·React는 배포 대상이 둘로 늘고 [[ADR-003]]과 어긋남. 정적 페이지는 같은 앱이 서빙하므로 버릴 코드가 아니고 의존성도 추가되지 않음
- **설계 의도:** 답변만 보여주면 여느 챗봇과 구별되지 않으므로 **`intent`·`search_retries`·`critic_runs`·`grounded`를 배지로 노출** — 자기교정과 근거 검증이 실제로 돌았다는 것이 화면에서 보이는 게 목적. 항복은 실패가 아니라 정직한 응답이므로 오류와 다른 색으로 구분. `[paper_id]` 인용은 arXiv 링크로 변환해 근거를 바로 확인할 수 있게 함
