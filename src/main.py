import sys
from graph import graph

if __name__ == "__main__":
    question = sys.argv[1]
    result = graph.invoke({"question": question})

    print("intent:", result["intent"])
    if result["intent"] == "search":
        papers = result.get("papers", [])
        print(f"검색 결과 {len(papers)}편:")
        for p in papers:
            print(f"  [{p['paper_id']}] {p['title']}")
    elif result.get("gave_up"):
        print(f"항복 ({result['give_up_reason']}):", result["answer"])
    else:
        print("answer:\n", result.get("answer"))