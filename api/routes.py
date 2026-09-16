import json
import os
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from graph.graph_builder import build_graph

router = APIRouter()
graph = build_graph()


class ResearchRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=500)


class Source(BaseModel):
    id: str
    title: str
    content: str
    url: str
    domain: str = ""
    query: str = ""
    query_number: int = 0


class ResearchResponse(BaseModel):
    topic: str
    plan: list[str]
    sources: list[Source]
    summary: str
    critique: str
    final_report: str
    revision_number: int


def send_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def initial_state(topic: str):
    return {
        "topic": topic,
        "plan": [],
        "search_results": [],
        "summary": "",
        "critique": "",
        "final_report": "",
        "revision_number": 0,
        "max_revisions": int(os.getenv("MAX_REVISIONS", "1")),
    }


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "AI Research Assistant",
        "version": "1.2.0",
        "environment": os.getenv("APP_ENV", "development"),
    }


def _result_from_state(topic: str, state: dict) -> dict:
    return {
        "topic": topic,
        "plan": state.get("plan", []),
        "sources": state.get("search_results", []),
        "summary": state.get("summary", ""),
        "critique": state.get("critique", ""),
        "final_report": state.get("final_report", ""),
        "revision_number": state.get("revision_number", 0),
    }


def research_stream(topic: str):
    final_state = {}
    status_messages = {
        "planner": "Planning research questions...",
        "research": "Searching and deduplicating web sources...",
        "summarizer": "Building an evidence map...",
        "draft_report": "Writing a cited draft report...",
        "critic": "Fact-checking claims and citations...",
        "final_report": "Revising the report against reviewer feedback...",
    }

    try:
        yield send_event({"type": "start", "message": "Research started", "topic": topic})

        for update in graph.stream(initial_state(topic), stream_mode="updates"):
            if not isinstance(update, dict):
                continue

            for node_name, node_output in update.items():
                if not isinstance(node_output, dict):
                    node_output = {}
                final_state.update(node_output)

                yield send_event({
                    "type": "progress",
                    "node": node_name,
                    "message": status_messages.get(node_name, f"Running {node_name}..."),
                })

                if node_name == "planner":
                    yield send_event({"type": "plan", "plan": node_output.get("plan", [])})

                elif node_name == "research":
                    sources = node_output.get("search_results", [])
                    for source in sources:
                        yield send_event({"type": "source", "source": source})
                    yield send_event({"type": "search_complete", "count": len(sources)})

                elif node_name == "summarizer":
                    yield send_event({"type": "summary", "summary": node_output.get("summary", "")})

                elif node_name == "critic":
                    yield send_event({"type": "critique", "critique": node_output.get("critique", "")})

                elif node_name in {"draft_report", "final_report"}:
                    report = node_output.get("final_report", "")
                    if report:
                        yield send_event({
                            "type": "final_report",
                            "final_report": report,
                            "revision_number": node_output.get("revision_number", 0),
                        })

        result = _result_from_state(topic, final_state)
        if not result["final_report"]:
            yield send_event({"type": "error", "message": "Research completed, but no final report was produced."})
            return

        yield send_event({"type": "result", "result": result})
        yield send_event({"type": "complete", "message": "Research completed", "result": result})

    except Exception as exc:
        traceback.print_exc()
        yield send_event({"type": "error", "message": f"{type(exc).__name__}: {exc}"})


@router.post("/research/stream")
def research_stream_endpoint(request: ResearchRequest):
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Research topic cannot be empty.")

    return StreamingResponse(
        research_stream(topic),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/research", response_model=ResearchResponse)
def research(request: ResearchRequest):
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Research topic cannot be empty.")

    try:
        result = graph.invoke(initial_state(topic))
        return ResearchResponse(**_result_from_state(topic, result))
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}") from exc
