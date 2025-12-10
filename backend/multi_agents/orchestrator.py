"""
Main Orchestrator for Multi-Agent Roster Generation System
Uses LangGraph with Command and goto for proper supervisor-based multi-agent orchestration.

This orchestrator uses a LangGraph state machine where:
- Each agent is a node in the graph
- Agents return Command objects with goto to control flow
- The graph routes between nodes based on Command goto
- Agent 3 and Agent 4 loop using Command(goto="agent_3") or Command(goto="agent_4")
"""

import os
import sys
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import agents as functions (not tools - tools are for LangChain agents)
from agent_1.agent import run_agent1
from agent_2.agent import run_agent2
from agent_3.agent import run_agent3
from agent_4.agent import run_agent4
from agent_5.agent import run_agent5
from shared_state import MultiAgentState

load_dotenv()

# Module-level progress tracker (thread-safe for single-threaded execution)
_progress_tracker = []


# Note: Supervisor agent is not used - we use direct graph nodes with Command goto instead


def create_orchestrator_graph():
    """
    Create a LangGraph state machine that coordinates all agents using Command and goto.
    Each agent node directly calls its tool and returns a Command with goto for routing.
    """
    import uuid

    # Create the graph
    workflow = StateGraph(MultiAgentState)

    def agent_1_node(state: MultiAgentState):
        """Agent 1: Parse and structure data - goes to agent_2"""
        print("🔄 Running Agent 1: Parsing and structuring data...")

        # Add progress message
        start_msg = "🔄 Agent 1: Parsing and structuring data..."
        _progress_tracker.append(start_msg)
        print(start_msg)

        # Call the underlying function directly
        result = run_agent1()
        state_update = result.get("state_update", {})
        employee_count = result.get("employee_count", 0)

        # Return state update and route to agent_2
        update = {
            "employee_data": state_update.get("employee_data", []),
            "store_requirements": state_update.get("store_requirements", {}),
            "management_store": state_update.get("management_store", {}),
            "structured_data": state_update.get("structured_data", {}),
        }

        result_dict = {**update}
        # Store progress in module-level tracker
        progress_msg = f"✅ Agent 1 completed: Processed {employee_count} employees and structured all data"
        _progress_tracker.append(progress_msg)
        print(progress_msg)
        return result_dict

    def agent_2_node(state: MultiAgentState):
        """Agent 2: Analyze constraints - goes to agent_3"""
        print("🔄 Running Agent 2: Analyzing constraints and rules...")

        # Call the underlying function directly with state
        result = run_agent2(state=state)
        state_update = result.get("state_update", {})

        update = {
            "constraints": state_update.get("constraints", {}),
            "rules_data": state_update.get("rules_data", {}),
            "store_rules_data": state_update.get("store_rules_data", {}),
        }

        result_dict = {**update}
        constraints_count = len(
            state_update.get("constraints", {}).get("compliance_requirements", [])
        )
        progress_msg = f"Agent 2 completed: Created structured constraints with {constraints_count} compliance requirements"
        _progress_tracker.append(progress_msg)
        print(f"✅ {progress_msg}")
        return result_dict

    def agent_3_node(state: MultiAgentState):
        """Agent 3: Generate roster - always goes to agent_4 for validation"""
        # Handle both dict and MultiAgentState
        if isinstance(state, dict):
            iteration = state.get("iteration_count", 0) + 1
        else:
            iteration = getattr(state, "iteration_count", 0) + 1

        print(f"🔄 Running Agent 3: Generating roster (iteration {iteration})...")

        # Add progress message
        start_msg = f"🔄 Agent 3: Generating roster (iteration {iteration})..."
        _progress_tracker.append(start_msg)
        print(start_msg)

        # Call the underlying function directly with state
        result = run_agent3(state=state, use_llm=True)  # Enable LLM intelligence
        roster_data = result.get("roster", {})
        updated_state = result.get("state", {})

        roster_to_set = (
            roster_data
            if roster_data
            else (
                updated_state.get("roster", {})
                if isinstance(updated_state, dict)
                else getattr(updated_state, "roster", {})
            )
        )

        update = {
            "roster": roster_to_set,
            "roster_metadata": {
                "generated": True,
                "total_shifts": (
                    len(roster_to_set.get("shifts", []))
                    if isinstance(roster_to_set, dict)
                    else 0
                ),
                "compliance_checked": False,  # Will be checked by Agent 4
                "excel_exported": (
                    "excel_path" in roster_to_set
                    if isinstance(roster_to_set, dict)
                    else False
                ),
                "excel_path": (
                    roster_to_set.get("excel_path")
                    if isinstance(roster_to_set, dict)
                    else None
                ),
                "iteration": iteration,
            },
        }

        result_dict = {**update}
        shifts_count = (
            len(roster_to_set.get("shifts", []))
            if isinstance(roster_to_set, dict)
            else 0
        )
        progress_msg = f"✅ Agent 3 completed: Roster generated with {shifts_count} shifts (iteration {iteration})"
        _progress_tracker.append(progress_msg)
        print(progress_msg)
        return result_dict

    def agent_4_node(state: MultiAgentState):
        """Agent 4: Validate roster - returns Command with goto to loop or finish"""
        # Handle both dict and MultiAgentState
        if isinstance(state, dict):
            current_iteration = state.get("iteration_count", 0)
        else:
            current_iteration = getattr(state, "iteration_count", 0)
        iteration = current_iteration + 1

        print(f"🔄 Running Agent 4: Validating roster (iteration {iteration})...")

        # Add progress message
        start_msg = f"🔄 Agent 4: Validating roster (iteration {iteration})..."
        _progress_tracker.append(start_msg)
        print(start_msg)

        # Call the underlying function directly with state
        result = run_agent4(state=state)
        new_violations = result.get("violations", [])
        violation_count = result.get("violation_count", 0)
        critical_count = result.get("critical_count", 0)
        is_compliant = result.get("is_compliant", False)

        # Update state with violations and iteration count
        update = {
            "violations": new_violations,
            "iteration_count": iteration,
            "validation_complete": is_compliant,
        }

        result_dict = {**update}

        # Determine progress message based on violations and iteration count
        max_iterations = 4
        if violation_count == 0:
            # No violations - move to agent_5
            progress_msg = (
                f"✅ Agent 4 completed: No violations found (iteration {iteration})"
            )
            _progress_tracker.append(progress_msg)
            print(progress_msg)
        elif iteration < max_iterations:
            # Violations found and haven't reached max - loop back to agent_3
            progress_msg = f"✅ Agent 4 completed: Found {violation_count} violations ({critical_count} critical) - regenerating (iteration {iteration})"
            _progress_tracker.append(progress_msg)
            print(progress_msg)
        else:
            # Max iterations reached - move to agent_5 anyway
            progress_msg = f"✅ Agent 4 completed: Max iterations reached. Found {violation_count} violations (iteration {iteration})"
            _progress_tracker.append(progress_msg)
            print(progress_msg)

        return result_dict

    def agent_5_node(state: MultiAgentState):
        """Agent 5: Final check - finishes the pipeline"""
        print("🔄 Running Agent 5: Performing final comprehensive check...")

        # Add progress message
        start_msg = "🔄 Agent 5: Performing final comprehensive check..."
        _progress_tracker.append(start_msg)
        print(start_msg)

        # Call the underlying function directly with state
        result = run_agent5(state=state)

        # Extract report data
        report_path = result.get("report_path", "")
        roster_status = result.get("roster_status", "unknown")
        coverage_percent = result.get("availability_coverage_percent", 0)
        filled_slots = result.get("filled_slots", 0)
        total_slots = result.get("total_slots", 0)
        summary = result.get("summary", "")
        recommendations = result.get("recommendations", [])

        # Preserve iteration_count from state
        if isinstance(state, dict):
            current_iteration = state.get("iteration_count", 0)
        else:
            current_iteration = getattr(state, "iteration_count", 0)

        update = {
            "final_check_report": {
                "roster_status": roster_status,
                "availability_coverage_percent": coverage_percent,
                "filled_slots": filled_slots,
                "total_slots": total_slots,
                "report_path": report_path,
                "summary": summary,
                "recommendations": recommendations,
            },
            "final_check_complete": True,
            "iteration_count": current_iteration,  # Preserve iteration count
        }

        result_dict = {**update}
        progress_msg = f"✅ Agent 5 completed: Final check complete - Status: {roster_status.upper()}, Coverage: {coverage_percent}%"
        _progress_tracker.append(progress_msg)
        print(progress_msg)
        return result_dict

    # Add nodes
    workflow.add_node("agent_1", agent_1_node)
    workflow.add_node("agent_2", agent_2_node)
    workflow.add_node("agent_3", agent_3_node)
    workflow.add_node("agent_4", agent_4_node)
    workflow.add_node("agent_5", agent_5_node)

    # Set entry point
    workflow.set_entry_point("agent_1")

    # Route functions based on state values (not _goto field)
    def route_from_agent_1(state: MultiAgentState):
        """Route from agent_1 - always goes to agent_2"""
        return "agent_2"

    def route_from_agent_2(state: MultiAgentState):
        """Route from agent_2 - always goes to agent_3"""
        return "agent_3"

    def route_from_agent_3(state: MultiAgentState):
        """Route from agent_3 - always goes to agent_4"""
        return "agent_4"

    def route_from_agent_4(state: MultiAgentState):
        """Route from agent_4 - loops to agent_3 if violations, else goes to agent_5"""
        # Handle both dict and MultiAgentState
        if isinstance(state, dict):
            violations = state.get("violations", [])
            iteration_count = state.get("iteration_count", 0)
            validation_complete = state.get("validation_complete", False)
        else:
            violations = getattr(state, "violations", [])
            iteration_count = getattr(state, "iteration_count", 0)
            validation_complete = getattr(state, "validation_complete", False)

        max_iterations = 4
        violation_count = len(violations) if violations else 0

        if violation_count == 0 or validation_complete:
            # No violations or validation complete - go to agent_5
            return "agent_5"
        elif iteration_count < max_iterations:
            # Violations found and haven't reached max - loop back to agent_3
            return "agent_3"
        else:
            # Max iterations reached - go to agent_5 anyway
            return "agent_5"

    def route_from_agent_5(state: MultiAgentState):
        """Route from agent_5 - always finishes"""
        return END

    # Add conditional edges based on state values
    workflow.add_conditional_edges(
        "agent_1", route_from_agent_1, {"agent_2": "agent_2"}
    )
    workflow.add_conditional_edges(
        "agent_2", route_from_agent_2, {"agent_3": "agent_3"}
    )
    workflow.add_conditional_edges(
        "agent_3", route_from_agent_3, {"agent_4": "agent_4"}
    )
    workflow.add_conditional_edges(
        "agent_4",
        route_from_agent_4,
        {
            "agent_3": "agent_3",  # Loop back if violations found
            "agent_5": "agent_5",  # Continue to final check
        },
    )
    workflow.add_conditional_edges("agent_5", route_from_agent_5, {END: END})

    # Compile graph
    app = workflow.compile()

    return app


def run_full_pipeline(
    employee_file: str = None,
    store_requirement_file: str = None,
    management_store_file: str = None,
    rules_file: str = None,
    store_rules_file: str = None,
) -> dict:
    """
    Run the complete multi-agent pipeline using LangGraph with Command and goto.

    The pipeline uses a supervisor agent that coordinates:
    1. Agent 1: Parse and structure data
    2. Agent 2: Analyze constraints
    3. Agent 3: Generate roster
    4. Agent 4: Validate roster
    5. Loop Agent 3-4 until no violations or max 7 iterations (via Command goto)
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

    # Create graph
    app = create_orchestrator_graph()

    # Prepare initial prompt for supervisor
    prompt = """Generate a complete, validated roster by following these steps:

1. First, parse and structure the data files (employee data, store requirements, management store)
2. Then, analyze the rules and constraints (rules.json and store_rule.json)
3. Generate the roster schedule that satisfies all requirements
4. Validate the roster to check for any violations
5. If violations are found, regenerate the roster to fix them (up to 7 iterations)
6. Continue until the roster is fully compliant with no violations
7. Finally, perform final comprehensive check to verify availability coverage and staffing requirements, and generate final report

The tools will automatically loop between generation and validation when needed using Command goto."""

    # Create initial config with thread_id for checkpointing
    config = {"configurable": {"thread_id": "roster_generation_1"}}

    # Invoke graph with initial state
    # Convert MultiAgentState to dict for inputs (handle both dict and object)
    if isinstance(initial_state, dict):
        state_dict = initial_state.copy()
    else:
        state_dict = {
            "employee_data": getattr(initial_state, "employee_data", []),
            "store_requirements": getattr(initial_state, "store_requirements", {}),
            "management_store": getattr(initial_state, "management_store", {}),
            "structured_data": getattr(initial_state, "structured_data", {}),
            "constraints": getattr(initial_state, "constraints", {}),
            "rules_data": getattr(initial_state, "rules_data", {}),
            "store_rules_data": getattr(initial_state, "store_rules_data", {}),
            "roster": getattr(initial_state, "roster", {}),
            "roster_metadata": getattr(initial_state, "roster_metadata", {}),
            "violations": getattr(initial_state, "violations", []),
            "iteration_count": getattr(initial_state, "iteration_count", 0),
            "validation_complete": getattr(initial_state, "validation_complete", False),
            "final_check_report": getattr(initial_state, "final_check_report", {}),
            "final_check_complete": getattr(
                initial_state, "final_check_complete", False
            ),
            "messages": getattr(initial_state, "messages", []),
        }

    inputs = {
        "messages": [{"role": "user", "content": prompt}],
        **{k: v for k, v in state_dict.items() if k != "messages"},
    }

    # Clear progress tracker before starting
    global _progress_tracker
    _progress_tracker.clear()

    # Add initial workflow message
    _progress_tracker.append("🔄 Running multi-agent workflow...")

    # Run the graph
    final_state = None
    for state in app.stream(inputs, config):
        final_state = state

    # Collect progress from module-level tracker
    progress_messages = _progress_tracker.copy()

    # Extract final state from last step
    extracted_state = None
    if final_state:
        # LangGraph stream returns dict like: {node_name: state_after_node}
        # Get the state from the last executed node (should be agent_5)
        if isinstance(final_state, dict):
            # Get all node states and merge them, or use the last one
            # The last key should be agent_5 which has the final merged state
            if final_state:
                last_key = list(final_state.keys())[-1]
                extracted_state = final_state[last_key]
        else:
            extracted_state = final_state

        # Convert MultiAgentState to dict if needed
        if not isinstance(extracted_state, dict):
            extracted_state = {
                "employee_data": getattr(extracted_state, "employee_data", []),
                "store_requirements": getattr(
                    extracted_state, "store_requirements", {}
                ),
                "management_store": getattr(extracted_state, "management_store", {}),
                "structured_data": getattr(extracted_state, "structured_data", {}),
                "constraints": getattr(extracted_state, "constraints", {}),
                "rules_data": getattr(extracted_state, "rules_data", {}),
                "store_rules_data": getattr(extracted_state, "store_rules_data", {}),
                "roster": getattr(extracted_state, "roster", {}),
                "roster_metadata": getattr(extracted_state, "roster_metadata", {}),
                "violations": getattr(extracted_state, "violations", []),
                "iteration_count": getattr(extracted_state, "iteration_count", 0),
                "validation_complete": getattr(
                    extracted_state, "validation_complete", False
                ),
                "final_check_report": getattr(
                    extracted_state, "final_check_report", {}
                ),
                "final_check_complete": getattr(
                    extracted_state, "final_check_complete", False
                ),
            }

        # Remove _progress from final state (it's just for progress tracking)
        if isinstance(extracted_state, dict):
            if "_progress" in extracted_state:
                del extracted_state["_progress"]

    violations = extracted_state.get("violations", []) if extracted_state else []
    iteration_count = (
        extracted_state.get("iteration_count", 0) if extracted_state else 0
    )

    return {
        "status": "success",
        "roster": extracted_state.get("roster", {}) if extracted_state else {},
        "state": extracted_state if extracted_state else {},
        "violations": violations,
        "violation_count": len(violations),
        "iterations": iteration_count,
        "is_compliant": len(violations) == 0,
        "progress": progress_messages,  # Include progress messages for UI
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
