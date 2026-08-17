"""
LangGraph state machine for TestGhost test generation.
Nodes: classifier -> planner -> writer -> validator
Retry edge: validator -> writer (if not validated and retry_count < 2)
"""

from langgraph.graph import END, StateGraph

from langgraph_pipeline.nodes.classifier import classifier_node
from langgraph_pipeline.nodes.planner import planner_node
from langgraph_pipeline.nodes.validator import validator_node
from langgraph_pipeline.nodes.writer import writer_node
from langgraph_pipeline.state import AgentState


def _should_retry(state: AgentState) -> str:
    """Route: retry writer if validation failed and retries remain."""
    if not state.get("validation_passed") and state.get("retry_count", 0) < 2:
        return "retry"
    return "done"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("classifier", classifier_node)
    graph.add_node("planner", planner_node)
    graph.add_node("writer", writer_node)
    graph.add_node("validator", validator_node)

    graph.set_entry_point("classifier")
    graph.add_edge("classifier", "planner")
    graph.add_edge("planner", "writer")
    graph.add_edge("writer", "validator")

    graph.add_conditional_edges(
        "validator",
        _should_retry,
        {"retry": "writer", "done": END},
    )

    return graph


# Compiled graph — import this in generate.py
test_generation_graph = build_graph().compile()
