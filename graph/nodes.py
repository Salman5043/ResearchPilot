import json
import re
from typing import Any

from utils.llm import invoke_llm
from utils.search_tool import web_search


def clean_json_response(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()


def _source_block(results: list[dict[str, Any]]) -> str:
    blocks = []
    for result in results:
        blocks.append(
            f"[{result.get('id', 'S?')}] {result.get('title', '')}\n"
            f"Domain: {result.get('domain', '')}\n"
            f"URL: {result.get('url', '')}\n"
            f"Evidence: {result.get('content', '')}"
        )
    return "\n\n--- SOURCE ---\n\n".join(blocks)


def _source_index(results: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"[{r.get('id', 'S?')}] {r.get('title', '')} | {r.get('domain', '')} | {r.get('url', '')}"
        for r in results
    )


# ============================================================
# PLANNER
# ============================================================

def _parse_planner_output(content: str, limit: int = 5) -> list[str]:
    """Parse planner output defensively.

    The planner intentionally uses a line-based format instead of JSON because
    smaller/hosted models sometimes return malformed JSON (unescaped quotes,
    markdown fences, or trailing commentary). We still accept JSON when it is
    valid so older prompts/outputs remain compatible.
    """
    text = clean_json_response(content)

    # First try valid JSON for compatibility.
    try:
        data = json.loads(text)
        if isinstance(data, dict) and isinstance(data.get("subtopics"), list):
            items = data["subtopics"]
            return list(dict.fromkeys(str(x).strip() for x in items if str(x).strip()))[:limit]
    except json.JSONDecodeError:
        pass

    # Preferred robust format: one question per line, optionally numbered.
    items = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Remove common numbering such as "1.", "2)", "-", or "*".
        line = re.sub(r"^(?:[-*]|\d+[.)])\s*", "", line).strip()
        if not line:
            continue
        # Ignore obvious explanatory wrappers.
        if line.lower() in {"subtopics:", "research questions:", "questions:"}:
            continue
        items.append(line)

    return list(dict.fromkeys(items))[:limit]


def planner_node(state):
    topic = state["topic"]
    prompt = f"""
You are a professional research planner.

Research topic:
{topic}

Create exactly 5 non-overlapping research questions that together provide broad,
balanced coverage. Prioritize current evidence, key developments, measurable facts,
risks/challenges, and competing perspectives where relevant.

OUTPUT FORMAT — IMPORTANT:
Return ONLY 5 plain-text lines, one research question per line.
Do NOT use JSON. Do NOT use markdown bullets. Do NOT add explanations.

Example:
What is the current state of ...?
What are the latest developments in ...?
What evidence shows ...?
What are the main risks and competing views ...?
What is the outlook for ...?
"""
    try:
        response = invoke_llm(prompt, max_tokens=500)
        subtopics = _parse_planner_output(response.content, limit=5)
        if len(subtopics) < 5:
            raise ValueError(f"Planner returned only {len(subtopics)} usable questions")
    except Exception as exc:
        print(f"Planner error: {exc}; using fallback plan.")
        subtopics = [
            f"What is {topic} and what are its key concepts?",
            f"What are the latest developments and evidence about {topic}?",
            f"What are the major benefits, applications, or impacts of {topic}?",
            f"What are the main limitations, risks, and competing viewpoints about {topic}?",
            f"What is the outlook for {topic} and what should decision-makers watch?",
        ]
    return {"plan": subtopics[:5]}


# ============================================================
# RESEARCH
# ============================================================

def research_node(state):
    plan = state["plan"]
    search_results = []
    seen_urls = set()
    source_counter = 1

    for index, query in enumerate(plan, start=1):
        try:
            results = web_search(query, max_results=3)
            for result in results:
                url = result.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                result["id"] = f"S{source_counter}"
                result["query"] = query
                result["query_number"] = index
                search_results.append(result)
                source_counter += 1
                if len(search_results) >= 15:
                    break
        except Exception as exc:
            print(f"Search failed for query {index}: {exc}")
        if len(search_results) >= 15:
            break

    return {"search_results": search_results}


# ============================================================
# EVIDENCE SYNTHESIS
# ============================================================

def summarizer_node(state):
    topic = state["topic"]
    results = state["search_results"]
    research_data = _source_block(results)[:16000]

    prompt = f"""
You are an evidence-focused research analyst.

Topic: {topic}

SOURCE MATERIAL:
{research_data}

Produce an evidence map / research summary.

Rules:
1. Every substantive factual claim MUST include one or more source IDs like [S1].
2. Use only information supported by the supplied sources.
3. If sources disagree, explicitly say so and cite both sides.
4. Distinguish facts from interpretation.
5. Do not invent statistics, dates, names, or URLs.
6. Organize by the most useful themes for the topic.
7. End with a short "Evidence gaps" section.
8. Keep it under about 1200 words.
"""
    response = invoke_llm(prompt, max_tokens=1300)
    return {"summary": response.content}


# ============================================================
# DRAFT REPORT
# ============================================================

def draft_report_node(state):
    topic = state["topic"]
    summary = state["summary"][:8000]
    sources = _source_index(state["search_results"])[:7000]

    prompt = f"""
You are a senior research writer.

Write a decision-useful research report about: {topic}

EVIDENCE MAP:
{summary}

SOURCE INDEX:
{sources}

Requirements:
- Use a clear title and meaningful headings.
- Cite factual claims inline with source IDs such as [S1] or [S2][S5].
- Do not cite a source unless it supports the claim.
- Do not invent information.
- Explain uncertainty and conflicting evidence.
- Prefer concrete findings over generic filler.
- Do not mention AI, prompts, or the review process.
- End with "Sources" containing only the cited source IDs, titles, domains and URLs.
- Keep the report below about 1500 words.

Return only the report.
"""
    response = invoke_llm(prompt, max_tokens=1400)
    return {
        "final_report": response.content,
        "revision_number": 0,
    }


# ============================================================
# CRITIC
# ============================================================

def critic_node(state):
    draft = state["final_report"][:9000]
    sources = _source_block(state["search_results"])[:11000]

    prompt = f"""
You are a rigorous fact-checking editor.

DRAFT REPORT:
{draft}

SOURCE INDEX AND EVIDENCE:
{sources}

Review the report against the supplied evidence.
Check:
1. Unsupported or overstated claims.
2. Incorrect source attribution.
3. Missing important findings from the research.
4. Contradictions or unresolved source disagreements.
5. Bias or one-sided framing.
6. Weak conclusions or reasoning.
7. Citation completeness.

Return either exactly:
NO_MAJOR_ISSUES

or concise actionable findings, each stating what must change. Do not rewrite the report.
"""
    response = invoke_llm(prompt, max_tokens=800)
    return {"critique": response.content.strip()}


# ============================================================
# REVISION / FINALIZATION
# ============================================================

def should_revise(state):
    critique = state.get("critique", "").strip()
    if not critique or critique == "NO_MAJOR_ISSUES":
        return "finish"
    if state.get("revision_number", 0) >= state.get("max_revisions", 1):
        return "finish"
    return "revise"


def final_report_node(state):
    # IMPORTANT: Groq enforces an 8K TPM request limit for the current model.
    # The previous implementation sent the full source evidence + draft + critique
    # in one request, which could exceed that limit. For revision, the critic has
    # already checked the draft against the evidence, so the revision model only
    # needs the compact source index plus the relevant report/feedback.
    draft = state["final_report"][:9000]
    critique = state["critique"][:3500]
    sources = _source_index(state["search_results"])[:5000]
    revision = state.get("revision_number", 0) + 1

    prompt = f"""
You are a senior research editor performing a final revision.

TOPIC: {state['topic']}

CURRENT REPORT:
{draft}

EDITOR FEEDBACK:
{critique}

SOURCE INDEX (use only these source IDs and URLs):
{sources}

Revise the report only where supported by the supplied evidence and reviewer feedback.
Requirements:
- Preserve useful content.
- Fix unsupported, overstated, or incorrectly cited claims identified by the reviewer.
- Address every valid criticism.
- Keep factual claims cited as [S#].
- Do not invent information or citations.
- Keep a balanced, professional structure.
- End with a concise Sources section containing only sources actually cited.
- Do not mention the editing/review process or AI.
- Return only the final report.
- Keep the revised report under 1100 words.
"""
    try:
        response = invoke_llm(prompt, max_tokens=1600)
    except Exception as exc:
        # A final defensive fallback: make one smaller request if a provider
        # rejects the request for context/TPM size.
        if "413" not in str(exc) and "tokens per minute" not in str(exc).lower():
            raise
        compact_prompt = f"""
Revise this research report using the editor feedback. Keep factual claims cited with
the existing [S#] citations. Do not invent facts. Return only the revised report.

REPORT:
{draft[:6500]}

FEEDBACK:
{critique[:2200]}
"""
        response = invoke_llm(compact_prompt, max_tokens=1000)

    return {
        "final_report": response.content,
        "revision_number": revision,
    }
