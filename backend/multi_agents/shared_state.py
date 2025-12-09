"""
Shared MultiAgentState for all agents in the roster generation system.
Uses AgentState from LangChain v1 for proper state management.
"""

from typing import Annotated, Sequence, List, Dict, Any, Optional
from langchain.agents import AgentState
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MultiAgentState(AgentState):
    """Shared state for all agents in the multi-agent roster system"""

    # Employee and store data (from Agent 1)
    employee_data: Annotated[
        List[Dict[str, Any]], "List of employee information dictionaries"
    ]
    store_requirements: Annotated[
        Dict[str, Any], "Store requirements and configurations"
    ]
    management_store: Annotated[Dict[str, Any], "Management store data and rules"]
    structured_data: Annotated[
        Dict[str, Any], "Final structured and enriched data from Agent 1"
    ]

    # Constraints (from Agent 2)
    constraints: Annotated[Dict[str, Any], "Structured constraints from Agent 2"]
    rules_data: Annotated[Dict[str, Any], "Raw rules data"]
    store_rules_data: Annotated[Dict[str, Any], "Raw store rules data"]

    # Roster (from Agent 3)
    roster: Annotated[Dict[str, Any], "Generated roster schedule"]
    roster_metadata: Annotated[Dict[str, Any], "Metadata about the roster generation"]

    # Validation (from Agent 4)
    violations: Annotated[List[Dict[str, Any]], "List of roster violations"]
    iteration_count: Annotated[int, "Number of iterations in Agent 3-4 loop"]
    validation_complete: Annotated[bool, "Whether validation is complete"]

    # Final Check (from Agent 5)
    final_check_report: Annotated[
        Dict[str, Any], "Final comprehensive check report from Agent 5"
    ]
    final_check_complete: Annotated[bool, "Whether final check is complete"]

    # Messages for conversation flow
    messages: Annotated[Sequence[BaseMessage], add_messages]
