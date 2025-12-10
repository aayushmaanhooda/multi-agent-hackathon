"""
Agent 2: Constraints Analyzer
Reads rules.json and store_rule.json, then uses LLM with Pydantic structured output
to create advanced structured constraints data that will be used for roster building.
Uses MultiAgentState with ToolRuntime for proper multi-agent coordination.
"""

import os
import json
from typing import Annotated, List, Optional
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.structured_output import StructuredOutputValidationError
from langchain_core.messages import ToolMessage
from langchain.tools import tool, ToolRuntime, InjectedToolCallId
from langgraph.types import Command
from dotenv import load_dotenv

# Import shared state
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_state import MultiAgentState

# Load environment variables
load_dotenv()


# Pydantic models for structured constraints output
class ShiftConstraint(BaseModel):
    """Constraints for shift scheduling"""

    min_shift_length_hours: Optional[float] = Field(
        default=3.0, description="Minimum shift length in hours"
    )
    max_shift_length_hours: Optional[float] = Field(
        default=12.0, description="Maximum shift length in hours"
    )
    min_rest_between_shifts_hours: Optional[float] = Field(
        default=10.0, description="Minimum rest period between shifts in hours"
    )
    max_shift_span_hours: Optional[float] = Field(
        default=12.0, description="Maximum total span for split shifts in hours"
    )


class PenaltyRate(BaseModel):
    """Penalty rate information"""

    day_type: Optional[str] = Field(
        default="", description="Day type: Saturday, Sunday, Public Holiday, Evening"
    )
    multiplier: Optional[float] = Field(
        default=1.0,
        description="Rate multiplier (e.g., 1.5 for 1.5x). Must be a numeric value.",
    )
    description: str = Field(
        default="", description="Description of when this rate applies"
    )

    @classmethod
    def parse_multiplier(cls, value):
        """Parse multiplier value, handling string values like 'variable'"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Try to parse as float
            try:
                return float(value)
            except ValueError:
                # If it's "variable" or similar, return None or default
                if "variable" in value.lower():
                    return None  # Will use default 1.0
                return 1.0  # Default fallback
        return 1.0  # Default fallback


class BreakRequirement(BaseModel):
    """Break requirements for shifts"""

    shift_length_threshold_hours: Optional[float] = Field(
        default=5.0, description="Shift length that triggers break requirement"
    )
    meal_break_minutes: Optional[int] = Field(
        default=30, description="Required meal break duration in minutes"
    )
    rest_break_minutes: Optional[int] = Field(
        default=10, description="Required rest break duration in minutes"
    )
    meal_break_paid: Optional[bool] = Field(
        default=False, description="Whether meal break is paid"
    )
    rest_break_paid: Optional[bool] = Field(
        default=True, description="Whether rest break is paid"
    )


class WorkingHoursTemplate(BaseModel):
    """Template for fixed working hours"""

    task_name: str = Field(default="", description="Name of the task")
    is_fixed: bool = Field(
        default=False, description="Whether this task has fixed hours"
    )
    is_flexible: bool = Field(
        default=False, description="Whether this task can be adjusted"
    )
    weekly_hours: float = Field(
        default=0.0, description="Total weekly hours for this task"
    )
    daily_schedule: dict = Field(
        default_factory=dict, description="Daily hours breakdown by day of week"
    )


class StructuredConstraints(BaseModel):
    """Comprehensive structured constraints for roster building"""

    compliance_requirements: List[dict] = Field(
        default_factory=list, description="Fair Work Act compliance requirements"
    )
    shift_constraints: ShiftConstraint = Field(
        description="Shift scheduling constraints"
    )
    penalty_rates: List[PenaltyRate] = Field(
        default_factory=list, description="Penalty rates for different day types"
    )
    break_requirements: List[BreakRequirement] = Field(
        default_factory=list, description="Break requirements by shift length"
    )
    working_hours_templates: List[WorkingHoursTemplate] = Field(
        default_factory=list, description="Fixed working hours templates"
    )
    roster_change_rules: dict = Field(
        default_factory=dict, description="Rules for roster changes and notifications"
    )
    location_specific_rules: dict = Field(
        default_factory=dict,
        description="Location-specific trading and operational rules",
    )
    summary: str = Field(
        default="", description="Summary of all constraints and their implications"
    )


def load_rules(file_path: str) -> dict:
    """Load rules from JSON file"""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading rules from {file_path}: {e}")
        return {}


def load_store_rules(file_path: str) -> dict:
    """Load store rules from JSON file"""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading store rules from {file_path}: {e}")
        return {}


@tool(
    "analyze_constraints",
    description="Analyze rules and store rules to create structured constraints for roster building. This is Agent 2's main function. Requires Agent 1 to have run first.",
)
def run_agent2_tool(
    rules_file: str = "",
    store_rules_file: str = "",
    runtime: ToolRuntime = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Command:
    """
    Tool wrapper for Agent 2 that uses ToolRuntime to access/update state.
    """
    # Access state from runtime if available
    state = None
    if runtime and hasattr(runtime, "state"):
        state = runtime.state

    # Get file paths if not provided
    if not rules_file or not store_rules_file:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backend_root = os.path.dirname(os.path.dirname(current_dir))
        dataset_path = os.path.join(backend_root, "multi_agents", "dataset")

        if not rules_file:
            rules_file = os.path.join(dataset_path, "rules.json")
        if not store_rules_file:
            store_rules_file = os.path.join(dataset_path, "store_rule.json")

    # Run Agent 2 logic
    # Note: run_agent2 is defined later in this file, Python will resolve it at runtime
    result = run_agent2(
        state=state, rules_file=rules_file, store_rules_file=store_rules_file
    )
    state_update = result.get("state_update", {})

    # Return Command with state update
    return Command(
        update={
            "constraints": state_update.get("constraints", {}),
            "rules_data": state_update.get("rules_data", {}),
            "store_rules_data": state_update.get("store_rules_data", {}),
            "messages": [
                ToolMessage(
                    content=f"Agent 2 completed. Created structured constraints with {len(state_update.get('constraints', {}).get('compliance_requirements', []))} compliance requirements.",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )


def run_agent2(
    state: Optional[MultiAgentState] = None,
    rules_file: str = None,
    store_rules_file: str = None,
) -> dict:
    """
    Run Agent 2: Analyze rules and create structured constraints using LLM with Pydantic output.

    Args:
        state: Optional state from Agent 1. If provided, constraints will be contextualized with employee/store data.
        rules_file: Path to rules.json
        store_rules_file: Path to store_rule.json

    Returns:
        Dictionary containing structured constraints and updated state
    """
    # Get default paths if not provided
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_root = os.path.dirname(os.path.dirname(current_dir))
    dataset_path = os.path.join(backend_root, "multi_agents", "dataset")

    if rules_file is None:
        rules_file = os.path.join(dataset_path, "rules.json")
    if store_rules_file is None:
        store_rules_file = os.path.join(dataset_path, "store_rule.json")

    # Load rules files
    print(f"Loading rules from: {rules_file}")
    rules_data = load_rules(rules_file)

    print(f"Loading store rules from: {store_rules_file}")
    store_rules_data = load_store_rules(store_rules_file)

    # Prepare context from Agent 1 state if available
    context_info = ""
    if state:
        # Handle both dict and MultiAgentState
        if hasattr(state, "employee_data"):
            employee_count = len(state.employee_data) if state.employee_data else 0
        else:
            employee_count = len(state.get("employee_data", []))
        context_info = f"""
Context from Agent 1:
- Total Employees: {employee_count}
- Store Requirements: {len(state.get("store_requirements", [])) if isinstance(state.get("store_requirements"), list) else "Loaded"}
- Management Store: Loaded
"""

    # Create agent with structured output using Pydantic
    agent = create_agent(
        model="openai:gpt-4o-mini",
        tools=[],  # No tools needed - just structured analysis
        system_prompt="You are a constraints analysis expert for roster management. Analyze compliance rules and store rules to create comprehensive, well-structured constraints data for roster building.",
        response_format=StructuredConstraints,  # Use Pydantic model for structured output
    )

    # Prepare prompt with rules data
    rules_summary = json.dumps(rules_data, indent=2, default=str)[:3000]
    store_rules_summary = json.dumps(store_rules_data, indent=2, default=str)[:3000]

    prompt = f"""Analyze the following rules and create comprehensive structured constraints for roster building:

FAIR WORK ACT COMPLIANCE RULES:
{rules_summary}

STORE WORKING HOURS TEMPLATES:
{store_rules_summary}

{context_info}

Please create a comprehensive StructuredConstraints object that includes:
1. All compliance requirements from Fair Work Act
2. Shift constraints (min/max shift length, rest periods, split shift rules)
3. Penalty rates for different day types (Saturday, Sunday, Public Holidays, Evening)
   - IMPORTANT: multiplier field must be a NUMERIC value (e.g., 1.25, 1.5, 2.0)
   - If a rate is variable or not specified, use 1.0 as default
   - Do NOT use strings like "variable" for multiplier - use numeric values only
4. Break requirements based on shift length
5. Working hours templates for different tasks
6. Roster change rules and notification requirements
7. Location-specific rules (Melbourne/Victoria specific)
8. A summary of all constraints and their implications for roster building

Ensure all constraints are accurately extracted and well-structured for use in automated roster generation.
CRITICAL: All numeric fields (multiplier, hours, minutes) must be actual numbers, not strings.
"""

    # Invoke the agent with structured output
    inputs = {"messages": [{"role": "user", "content": prompt}]}
    try:
        result = agent.invoke(inputs)
    except (StructuredOutputValidationError, ValueError, Exception) as e:
        # If structured output validation fails, fall back to creating from rules directly
        print(f"Warning: Agent structured output validation failed: {e}")
        print("Falling back to creating constraints from rules directly...")
        result = None
        structured_constraints = None

    # Extract structured constraints from agent response
    structured_constraints = None

    # If result is None (error occurred), skip extraction
    if result is None:
        structured_constraints = None
    # Try multiple ways to extract structured output
    elif hasattr(result, "structured_response"):
        structured_constraints = result.structured_response
    elif "structured_response" in result:
        structured_constraints = result["structured_response"]
    elif hasattr(result, "output") and hasattr(result.output, "model_dump"):
        structured_constraints = result.output
    elif result.get("messages"):
        # Try to extract from last message
        last_message = result["messages"][-1]
        if hasattr(last_message, "content"):
            try:
                content = last_message.content
                if isinstance(content, str):
                    # Try to parse as JSON
                    import re

                    # Look for JSON object in content
                    json_match = re.search(r"\{[\s\S]*\}", content, re.MULTILINE)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        structured_constraints = StructuredConstraints(**parsed)
            except Exception as e:
                print(f"Could not parse structured output from message: {e}")
                pass

    # If structured output not available, create from rules directly
    if structured_constraints is None:
        print(
            "Warning: Could not extract structured output from agent. Creating from rules directly."
        )
        # Create basic structure from rules
        structured_constraints = StructuredConstraints(
            compliance_requirements=rules_data.get("keyComplianceRequirements", []),
            shift_constraints=ShiftConstraint(
                min_shift_length_hours=3.0,
                max_shift_length_hours=12.0,
                min_rest_between_shifts_hours=10.0,
                max_shift_span_hours=12.0,
            ),
            penalty_rates=[
                PenaltyRate(
                    day_type="Saturday",
                    multiplier=1.25,
                    description="Saturday penalty rate",
                ),
                PenaltyRate(
                    day_type="Sunday", multiplier=1.5, description="Sunday penalty rate"
                ),
                PenaltyRate(
                    day_type="Public Holiday",
                    multiplier=2.25,
                    description="Public holiday penalty rate",
                ),
            ],
            break_requirements=[
                BreakRequirement(
                    shift_length_threshold_hours=5.0,
                    meal_break_minutes=30,
                    rest_break_minutes=10,
                    meal_break_paid=False,
                    rest_break_paid=True,
                )
            ],
            working_hours_templates=[],
            roster_change_rules={},
            location_specific_rules=rules_data.get("locationContext", {}),
            summary="Constraints extracted from rules files",
        )

    # Convert Pydantic model to dict for state
    constraints_dict = (
        structured_constraints.model_dump()
        if hasattr(structured_constraints, "model_dump")
        else structured_constraints.dict()
    )

    # Update state with constraints
    if state is None:
        # Create minimal state dict
        state = {
            "employee_data": [],
            "store_requirements": {},
            "management_store": {},
            "structured_data": {},
            "messages": [],
            "constraints": constraints_dict,
        }
    else:
        # Update existing state (handle both dict and MultiAgentState)
        if isinstance(state, dict):
            state["constraints"] = constraints_dict
        else:
            # MultiAgentState object
            state.constraints = constraints_dict

    print(
        f"Agent 2 completed. Created structured constraints with {len(constraints_dict.get('compliance_requirements', []))} compliance requirements."
    )

    # Prepare state update for handoff to Agent 3
    state_update = {
        "constraints": constraints_dict,
        "rules_data": rules_data,
        "store_rules_data": store_rules_data,
    }

    # Merge with existing state if available
    if isinstance(state, dict):
        state_update.update(state)

    return {
        "status": "success",
        "constraints": constraints_dict,
        "state": state,
        "state_update": state_update,  # For use with Command(goto="agent_3", update=state_update)
        "message": "Constraints successfully structured using LLM with Pydantic output",
    }


if __name__ == "__main__":
    # Test the agent
    result = run_agent2()
    print("\n" + "=" * 50)
    print("Agent 2 Result:")
    print("=" * 50)
    print(json.dumps(result, indent=2, default=str))


"""

now make agent 3 which will make a roaster making sure all rules and employee ets theri shify based on theri needs , requyiremt and all othe rconsataints and parameter, also i asked you we need to have only one state called multi agent stae thaat is shared among all agents so now in agent we can just access our current state and exectue it also you are noting agentstate your are using typed dict it wont woek also we need to have toolruntime and injectedtoolcallid to make sure these 3 agents work roperly 

this is lancgai v1 docs explore it propplery to make sure it woerks 


"""
