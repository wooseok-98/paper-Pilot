from search import search_papers
from ingest import ingest_papers
from llm import call_structured

MAX_RESEARCH_RETRIES = 2

KEYWORD_SCHEMA = {
    "type": "object",
    "properties": {
        "keyword": {
            "type": "string",
            "description": "arXiv 검색에 넣을 영어 기술 키워드 (문장이 아니라 2~5단어 검색어)",
        }
    },
    "required": ["keyword"],
}

EXPAND_SCHEMA = {
    "type": "object",
    "properties": {
        "alt_query": {
            "type": "string",
            "description": "원본 쿼리와 같은 주제를 가리키는, 논문에서 쓰이는 공식 기술 용어",
        }
    },
    "required": ["alt_query"],
}

FILTER_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "검색어 주제와 실제로 관련 있는 논문의 paper_id 목록",
        }
    },
    "required": ["relevant_ids"],
}


def to_search_keyword(question: str) -> str:
    """사용자 요청 문장에서 arXiv 검색용 영어 키워드를 추출"""
    result = call_structured(
        prompt=f"사용자 요청: {question}\n\n"
               f"이 요청에서 찾으려는 논문 주제를 arXiv 검색에 넣을 영어 기술 키워드로 만들어줘. "
               f"문장이 아니라 검색어 형태로. 예: '확산 모델 논문 찾아줘' -> 'diffusion model'",
        schema=KEYWORD_SCHEMA,
    )
    return result["keyword"]


def expand_query(query: str) -> str:
    """원본 쿼리의 주제와 관련된 공식 기술 용어를 찾아서 반환 (누락 대응)"""
    result = call_structured(
        prompt=f"'{query}' 검색어와 같은 주제를 다루는 논문에서 쓰이는 공식 기술 용어를 반환해줘. 예를 들어: 'stable diffusion' -> 'latent diffusion model'",
        schema=EXPAND_SCHEMA,
    )
    return result["alt_query"]


def merge_by_paper_id(*paper_lists: list[dict]) -> list[dict]:
    """검색 결과를 paper_id 기준으로 병합하고, 중복된 논문은 제거"""
    merged = {}
    for papers in paper_lists:
        for paper in papers:
            merged[paper["paper_id"]] = paper
    return list(merged.values())


def filter_relevant(query: str, papers: list[dict]) -> list[dict]:
    """논문별로 관련성을 채점해 관련 있는 것만 남김 (CRAG 필터링, 오염 대응)"""
    listing = "\n".join(
        f"[{p['paper_id']}] {p['title']}: {p['abstract'][:200]}" for p in papers
    )
    result = call_structured(
        prompt= f"검색어: '{query}'\n\n논문 목록:\n{listing}\n\n"
                f"검색어가 가리키는 **구체적인 대상과 직접** 관련된 논문만 골라줘. "
                f"단지 비슷한 기법(diffusion)을 다른 분야(DNA·음성·로봇 등)에 쓴 논문은 제외.",
        schema=FILTER_SCHEMA,
    )
    keep = set(result["relevant_ids"])
    return [p for p in papers if p["paper_id"] in keep]


def research(query: str, min_results: int = 3, max_retries: int = MAX_RESEARCH_RETRIES) -> list[dict]:
    """넓게 검색(recall) -> 관련성 필터(precision) -> 부족하면 더 검색 -> 저장"""
    keyword = to_search_keyword(query)
    alt_query = expand_query(keyword)
    papers = merge_by_paper_id(search_papers(keyword, 10), search_papers(alt_query, 10))
    relevant = filter_relevant(keyword, papers)

    retries = 0
    while len(relevant) < min_results and retries < max_retries:
        papers = merge_by_paper_id(papers, search_papers(keyword, 20 * (retries + 2)))
        relevant = filter_relevant(keyword, papers)
        retries += 1

    count = ingest_papers(relevant)
    print(
        f"keyword='{keyword}' | alt_query='{alt_query}' | 후보 {len(papers)}개 -> 필터 통과 {len(relevant)}개"
        f" (재검색 {retries}회) | 코퍼스 총 {count}편"
    )
    return relevant
