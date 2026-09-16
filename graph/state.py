from typing import List, TypedDict


class SearchResult(TypedDict, total=False):
    id: str
    title: str
    content: str
    url: str
    domain: str
    query: str
    query_number: int


class ResearchState(TypedDict):
    topic: str
    plan: List[str]
    search_results: List[SearchResult]
    summary: str
    critique: str
    final_report: str
    revision_number: int
    max_revisions: int
