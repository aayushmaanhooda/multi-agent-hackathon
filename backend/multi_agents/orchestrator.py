"""
Main Orchestrator for Multi-Agent Roster Generation System
Coordinates Agent 1, Agent 2, Agent 3 (Roster Generator), Agent 4 (Validator), and Agent 5 (Final Check)
using LangChain v1 multi-agent patterns with ToolRuntime and InjectedToolCallId.
Uses Command with goto to create a loop between Agent 3 and Agent 4 until roster is valid.
Agent 5 performs final comprehensive checks and generates report.
"""

import os
import sys
from langchain.agents import create_agent
from dotenv import load_dotenv

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import agents as tools
from agent_1.agent import run_agent1_tool
from agent_2.agent import run_agent2_tool
from agent_3.agent import generate_roster_tool
from agent_4.agent import validate_roster_tool
from agent_5.agent import final_roster_check_tool
from shared_state import MultiAgentState

load_dotenv()


def create_orchestrator():
    """
    Create the main orchestrator agent that coordinates all agents.
    The orchestrator uses Agent 1, Agent 2, Agent 3, and Agent 4 as tools.
    It intelligently decides when to loop between Agent 3 and Agent 4.
    """
    orchestrator = create_agent(
        model="openai:gpt-4o-mini",
        tools=[
            run_agent1_tool,
            run_agent2_tool,
            generate_roster_tool,
            validate_roster_tool,
            final_roster_check_tool,
        ],
        system_prompt="""You are the Roster Generation Orchestrator. Your task is to coordinate specialized agents to generate a complete, validated work roster:

1. Agent 1 (parse_and_structure_data): Parses employee data, store requirements, and management store files
2. Agent 2 (analyze_constraints): Analyzes rules and creates structured constraints
3. Agent 3 (generate_roster): Generates the roster schedule
4. Agent 4 (validate_roster): Validates the roster against all constraints and returns violations
5. Agent 5 (final_roster_check): Performs final comprehensive checks (availability coverage, staffing requirements) and generates final report

Workflow:
- First, call parse_and_structure_data to load and structure all input data
- Then, call analyze_constraints to extract and structure all rules and constraints
- Call generate_roster to create the roster schedule
- Call validate_roster to check for violations
- If violations are found and iteration_count < 5, call generate_roster again to fix them
- Repeat validation and regeneration until no violations are found or max 5 iterations reached
- Finally, call final_roster_check to perform comprehensive final validation and generate report

The tools will automatically use Command with goto to loop between Agent 3 and Agent 4 when needed.
Always follow this sequence and let the tools handle the looping logic.""",
    )
    return orchestrator


def run_full_pipeline(
    employee_file: str = None,
    store_requirement_file: str = None,
    management_store_file: str = None,
    rules_file: str = None,
    store_rules_file: str = None,
) -> dict:
    """
    Run the complete multi-agent pipeline:
    1. Agent 1: Parse and structure data
    2. Agent 2: Analyze constraints
    3. Agent 3: Generate roster
    4. Agent 4: Validate roster
    5. Loop Agent 3-4 until no violations or max 5 iterations
    6. Agent 5: Final comprehensive check and report generation

    Args:
        employee_file: Path to employee.xlsx
        store_requirement_file: Path to store requirements file
        management_store_file: Path to management store JSON
        rules_file: Path to rules.json
        store_rules_file: Path to store_rule.json

    Returns:
        Dictionary with final validated roster and complete state
    """
    # Initialize state
    initial_state = MultiAgentState(
        employee_data=[],
        store_requirements={},
        management_store={},
        structured_data={},
        constraints={},
        rules_data={},
        store_rules_data={},
        roster={},
        roster_metadata={},
        violations=[],
        iteration_count=0,
        validation_complete=False,
        final_check_report={},
        final_check_complete=False,
        messages=[],
    )

    # Create orchestrator
    orchestrator = create_orchestrator()

    # Prepare prompt for orchestrator
    prompt = """Generate a complete, validated roster by following these steps:

1. First, parse and structure the data files (employee data, store requirements, management store)
2. Then, analyze the rules and constraints (rules.json and store_rule.json)
3. Generate the roster schedule that satisfies all requirements
4. Validate the roster to check for any violations
5. If violations are found, regenerate the roster to fix them (up to 5 iterations)
6. Continue until the roster is fully compliant with no violations
7. Finally, perform final comprehensive check to verify availability coverage and staffing requirements, and generate final report

The tools will automatically loop between generation and validation when needed."""

    # Invoke orchestrator with initial state
    inputs = {
        "messages": [{"role": "user", "content": prompt}],
        **{k: v for k, v in initial_state.items() if k != "messages"},
    }

    result = orchestrator.invoke(inputs)

    # Extract final state
    final_state = result

    violations = final_state.get("violations", [])
    iteration_count = final_state.get("iteration_count", 0)

    return {
        "status": "success",
        "roster": final_state.get("roster", {}),
        "state": final_state,
        "violations": violations,
        "violation_count": len(violations),
        "iterations": iteration_count,
        "is_compliant": len(violations) == 0,
        "message": (
            f"Complete roster generation pipeline executed. {len(violations)} violations found after {iteration_count} iterations."
            if violations
            else "Complete roster generation pipeline executed successfully with no violations."
        ),
    }


if __name__ == "__main__":
    # Run the full pipeline
    result = run_full_pipeline()

    print("\n" + "=" * 50)
    print("Orchestrator Result:")
    print("=" * 50)
    import json

    print(json.dumps(result, indent=2, default=str))
