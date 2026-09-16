from langgraph.graph import END, StateGraph

from graph.nodes import (
    critic_node,
    draft_report_node,
    final_report_node,
    planner_node,
    research_node,
    should_revise,
    summarizer_node,
)
from graph.state import ResearchState


def build_graph():
    builder = StateGraph(ResearchState)

    builder.add_node("planner", planner_node)
    builder.add_node("research", research_node)
    builder.add_node("summarizer", summarizer_node)
    builder.add_node("draft_report", draft_report_node)
    builder.add_node("critic", critic_node)
    builder.add_node("final_report", final_report_node)

    builder.set_entry_point("planner")
    builder.add_edge("planner", "research")
    builder.add_edge("research", "summarizer")
    builder.add_edge("summarizer", "draft_report")
    builder.add_edge("draft_report", "critic")

    builder.add_conditional_edges(
        "critic",
        should_revise,
        {
            "revise": "final_report",
            "finish": END,
        },
    )
    # A revision must be reviewed again. The critic decides whether to
    # accept the revised report or stop when max_revisions is reached.
    builder.add_edge("final_report", "critic")

    return builder.compile()
