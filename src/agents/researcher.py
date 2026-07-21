from search import search_papers
from ingest import ingest_papers
from llm import call_structured

MAX_RETRIES = 5

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


def research(query: str, min_results: int = 3, max_retries: int = MAX_RETRIES) -> list[dict]:
    """넓게 검색(recall) -> 관련성 필터(precision) -> 부족하면 더 검색 -> 저장"""
    alt_query = expand_query(query)
    papers = merge_by_paper_id(search_papers(query, 10), search_papers(alt_query, 10))
    relevant = filter_relevant(query, papers)

    retries = 0
    while len(relevant) < min_results and retries < max_retries:
        papers = merge_by_paper_id(papers, search_papers(query, 20))
        relevant = filter_relevant(query, papers)
        retries += 1

    count = ingest_papers(relevant)
    print(f"저장된 논문 수: {count} (후보 {len(papers)}개 중)")
    return relevant
