from typing import Any, TypedDict, cast

from langgraph.graph import END, START, StateGraph

from nasagent.agent.execution.step_runner import StepRunner
from nasagent.agent.graph.nodes import default_tool_registry
from nasagent.agent.planning.planner import Planner
from nasagent.agent.planning.schemas import Plan
from nasagent.agent.state.models import AgentState, StepResult
from nasagent.agent.synthesis.synthesizer import Synthesizer
from nasagent.config.settings import SafetySettings
from nasagent.llm.base import LlmProvider
from nasagent.nas.base import NasAdapter
from nasagent.safety.policy import SafetyPolicy
from nasagent.tools.base import ToolContext


class GraphState(TypedDict, total=False):
    goal: str
    plan: Plan
    step_results: list[StepResult]
    final_summary: str


def build_agent_graph(adapter: NasAdapter, provider: LlmProvider) -> Any:
    async def plan_node(state: GraphState) -> GraphState:
        planner = Planner(provider=provider)
        return {"plan": await planner.create_plan(state["goal"])}

    async def execute_node(state: GraphState) -> GraphState:
        runner = StepRunner(
            registry=default_tool_registry(),
            safety_policy=SafetyPolicy(SafetySettings()),
        )
        context = ToolContext(adapter=adapter)
        results: list[StepResult] = []
        for step in state["plan"].steps:
            results.append(await runner.run_step(step, context))
        return {"step_results": results}

    async def synthesize_node(state: GraphState) -> GraphState:
        agent_state = AgentState(
            goal=state["goal"],
            plan=state["plan"],
            step_results=state["step_results"],
        )
        return {"final_summary": Synthesizer().summarize(agent_state)}

    graph = StateGraph(GraphState)
    graph.add_node("plan", plan_node)
    graph.add_node("execute", execute_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_edge(START, "plan")
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "synthesize")
    graph.add_edge("synthesize", END)
    return graph.compile()


async def run_agent_once(goal: str, adapter: NasAdapter, provider: LlmProvider) -> AgentState:
    graph = build_agent_graph(adapter=adapter, provider=provider)
    raw_state = cast(GraphState, await graph.ainvoke({"goal": goal}))
    return AgentState(
        goal=raw_state["goal"],
        plan=raw_state["plan"],
        step_results=raw_state["step_results"],
        final_summary=raw_state["final_summary"],
    )
