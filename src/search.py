"""arXiv 논문 검색 — 주제로 검색해 제목·초록·메타데이터 반환"""
import arxiv


def search_papers(query: str, max_results: int = 5) -> list[dict]:
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    papers = []
    for r in arxiv.Client().results(search):
        papers.append({
            "paper_id": r.entry_id.split("/")[-1],   # arXiv ID
            "title": r.title,
            "abstract": r.summary,
            "authors": [a.name for a in r.authors],
            "published": r.published.date().isoformat(),
            "pdf_url": r.pdf_url,
        })
    return papers