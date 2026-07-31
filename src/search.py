"""arXiv 논문 검색 — 주제로 검색해 제목·초록·메타데이터 반환"""
import arxiv

class SearchUnavailable(RuntimeError):
    """arXiv API 장애 — '결과 0건'과 구분하기 위한 예외"""

def search_papers(query: str, max_results: int = 10) -> list[dict]:
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    # list()로 감싸 네트워크 요청을 try 블록 안에서 끝냄
    try:
        results = list(arxiv.Client(delay_seconds=3, num_retries=3).results(search))
    except Exception as e:
        raise SearchUnavailable(f"arXiv 검색 실패: {e}") from e
    
    papers = []
    for r in results:
        papers.append({
            "paper_id": r.entry_id.split("/")[-1],   # arXiv ID
            "title": r.title,
            "abstract": r.summary,
            "authors": [a.name for a in r.authors],
            "published": r.published.date().isoformat(),
            "pdf_url": r.pdf_url,
        })
    return papers