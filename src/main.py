import sys
import anthropic

from graph import graph
from llm import StructuredOutputError

if __name__ == "__main__":
    question = sys.argv[1]
    
    try:
        result = graph.invoke({"question": question}, config={"recursion_limit": 40})
    except (anthropic.APIError, StructuredOutputError) as e:
        print("LLM 서비스에 접근할 수 없습니다:", e)
        sys.exit(1)

    print("intent:", result.get("intent"))
    if result.get("gave_up"):
        print(f"항복 ({result['give_up_reason']}):", result["answer"])
    elif result["intent"] == "search":
        papers = result.get("papers", [])
        print(f"검색 결과 {len(papers)}편:")
        for p in papers:
            print(f"  [{p['paper_id']}] {p['title']}")
    else:
        print("answer:\n", result.get("answer"))