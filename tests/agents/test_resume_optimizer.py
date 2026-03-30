"""Resume Optimizer ReAct Agent tests."""

from slayer.agents.resume_optimizer.agent import build_resume_optimizer_agent, should_continue
from slayer.schemas import ResumeBlock, ResumeOptimizationOutput, parsed_resume_to_blocks


def test_react_agent_builds():
    agent = build_resume_optimizer_agent()
    assert agent is not None
    assert type(agent).__name__ == "CompiledStateGraph"


def test_parsed_resume_to_blocks(sample_resume):
    blocks = parsed_resume_to_blocks(sample_resume)
    assert len(blocks) > 0
    assert all(isinstance(b, ResumeBlock) for b in blocks)
    block_types = [b.block_type.value for b in blocks]
    assert "personal_info" in block_types
    assert "skills" in block_types


def test_should_continue_done_by_score():
    state = {"current_score": 85.0, "target_ats_score": 80.0, "iteration": 1, "max_iterations": 3}
    assert should_continue(state) == "done"


def test_should_continue_done_by_iterations():
    state = {"current_score": 50.0, "target_ats_score": 80.0, "iteration": 3, "max_iterations": 3}
    assert should_continue(state) == "done"


def test_should_continue_continue():
    state = {"current_score": 50.0, "target_ats_score": 80.0, "iteration": 1, "max_iterations": 3}
    assert should_continue(state) == "continue"


def test_optimization_output_schema():
    output = ResumeOptimizationOutput(
        optimized_blocks=[], final_ats_score=75.0, score_improvement=13.0,
        iterations_used=2, optimization_summary="improved",
    )
    assert output.final_ats_score == 75.0
