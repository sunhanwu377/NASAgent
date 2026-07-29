from nasagent.agent.state.models import AgentState


class Synthesizer:
    def summarize(self, state: AgentState) -> str:
        names: list[str] = []
        for step in state.step_results:
            for result in step.tool_results:
                names.append(result.tool_name)
        if not names:
            return "No tools executed."
        return "Executed tools: " + ", ".join(names)
