#!/usr/bin/env python3
"""Show what the document index holds for approved proposals, for the demo's evidence moment.

    python3 scripts/demo_rag_search.py "What is the total budget?"
    python3 scripts/demo_rag_search.py "Who supplies the sponsorship?" --top-k 2

An approved proposal is split into one passage per page and stored with its page number and
section title. This asks the RAG service for the passages closest to a question, the same call
Core's lifecycle uses to index them. Standard library only; the RAG service listens on
127.0.0.1:8002 in the compose stack.
"""

import argparse
import json
import sys
import textwrap
import urllib.error
import urllib.request


def search(url: str, query: str, top_k: int, event_id: str | None) -> list[dict]:
    body: dict[str, object] = {"query": query, "top_k": top_k, "collection": "proposals"}
    if event_id:
        body["event_id"] = event_id
    request = urllib.request.Request(
        f"{url}/v1/retrieval/search",
        method="POST",
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read())["candidates"]
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"cannot reach the RAG service at {url}: {error}")
        sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--event", help="limit to one event id")
    parser.add_argument("--url", default="http://127.0.0.1:8002")
    args = parser.parse_args()

    passages = search(args.url, args.query, args.top_k, args.event)
    print(f'Approved proposals, closest passages for: "{args.query}"\n')
    if not passages:
        print("Nothing is indexed yet. A proposal is indexed when a campus admin approves it.")
        return 1
    for rank, passage in enumerate(passages, start=1):
        print(f"{rank}. page {passage['page_start']}: {passage['section'] or '(no title)'}")
        print(f"   {passage['evidence_id']}")
        body = " ".join(passage["excerpt"].split())
        print(textwrap.indent(textwrap.fill(body, 96, max_lines=4, placeholder=" ..."), "   "))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
