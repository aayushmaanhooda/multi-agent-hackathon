"""
Agent 4: Roster Validator
Validates the generated roster against all constraints, employee availability,
and compliance rules. Returns a list of violations if any are found.
"""

import json
from typing import Annotated, List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from dotenv import load_dotenv

# Import shared state
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_state import MultiAgentState

load_dotenv()


class Violation(BaseModel):
    """Represents a roster violation"""

    type: str = Field(
        description="Type of violation (availability, constraint, compliance, etc.)"
    )
    severity: str = Field(description="Severity: critical, warning, info")
    employee: str = Field(default="", description="Employee name if applicable")
    date: str = Field(default="", description="Date of violation")
    shift_code: str = Field(default="", description="Shift code if applicable")
    message: str = Field(description="Detailed violation message")
    recommendation: str = Field(default="", description="Recommended fix")


def _check_employee_availability(
    employee_name: str,
    date: str,
    shift_code: str,
    employees: List[Dict[str, Any]],
) -> Optional[Violation]:
    """Check if employee is available for the assigned shift"""
    for emp in employees:
        if emp.get("name") == employee_name:
            availability = emp.get("availability", {})

            # Find the day key for this date
            # IMPORTANT: Must match Agent 3's calculation exactly
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                # Calculate day offset (assuming roster starts from today)
                # Agent 3 uses: day_key = f"Day_{day_offset + 1}" where day_offset is 0-13
                # So Day_1 = today, Day_2 = today+1, etc.
                today = datetime.now().date()
                day_offset = (
                    date_obj.date() - today
                ).days  # 0 for today, 1 for tomorrow, etc.
                day_key = f"Day_{day_offset + 1}"  # Match Agent 3's calculation

                # Check availability
                available_shift = availability.get(day_key, "")

                # Also check day name matches
                day_names = [
                    "Monday",
                    "Tuesday",
                    "Wednesday",
                    "Thursday",
                    "Friday",
                    "Saturday",
                    "Sunday",
                ]
                day_name = day_names[date_obj.weekday()]

                if not available_shift or available_shift in ["/", "NA", ""]:
                    # Try to find by day name
                    for key, value in availability.items():
                        if (
                            day_name[:3] in str(key)
                            and value
                            and value not in ["/", "NA", ""]
                        ):
                            available_shift = value
                            break

                # Check if assigned shift matches availability
                if available_shift in ["/", "NA", ""]:
                    return Violation(
                        type="availability",
                        severity="critical",
                        employee=employee_name,
                        date=date,
                        shift_code=shift_code,
                        message=f"Employee {employee_name} is not available on {date} (marked as off/NA)",
                        recommendation=f"Remove {employee_name} from {date} or assign a different employee",
                    )

                if available_shift != shift_code and available_shift not in [
                    "1F",
                    "2F",
                    "3F",
                ]:
                    # Allow flexibility for 1F/2F/3F shifts
                    if shift_code not in ["1F", "2F", "3F"]:
                        return Violation(
                            type="availability",
                            severity="warning",
                            employee=employee_name,
                            date=date,
                            shift_code=shift_code,
                            message=f"Employee {employee_name} requested {available_shift} but assigned {shift_code} on {date}",
                            recommendation=f"Consider assigning {available_shift} shift or confirm with employee",
                        )
            except Exception as e:
                return Violation(
                    type="availability",
                    severity="warning",
                    employee=employee_name,
                    date=date,
                    shift_code=shift_code,
                    message=f"Could not verify availability for {employee_name} on {date}: {str(e)}",
                    recommendation="Verify employee availability manually",
                )
    return None


def _check_manager_coverage(
    roster_rows: List[Dict[str, Any]],
    managers: List[str],
) -> List[Violation]:
    """Check that each shift has at least one manager"""
    violations = []

    # Group by date and shift time
    shifts = {}
    for row in roster_rows:
        key = (row.get("Date"), row.get("Shift Time"))
        if key not in shifts:
            shifts[key] = []
        shifts[key].append(row)

    for (date, shift_time), rows in shifts.items():
        managers_in_shift = [
            r.get("Manager") for r in rows if r.get("Manager") in managers
        ]
        if not managers_in_shift:
            violations.append(
                Violation(
                    type="manager_coverage",
                    severity="critical",
                    date=date,
                    shift_code=rows[0].get("Shift Code", ""),
                    message=f"No manager assigned to shift on {date} at {shift_time}",
                    recommendation="Assign at least one manager to this shift",
                )
            )

    return violations


def _check_shift_length_constraints(
    roster_rows: List[Dict[str, Any]],
    constraints: Dict[str, Any],
) -> List[Violation]:
    """Check shift length against constraints"""
    violations = []
    shift_constraints = (
        constraints.get("shift_constraints", {})
        if isinstance(constraints, dict)
        else getattr(constraints, "shift_constraints", {})
    )

    # Handle both dict and object for shift_constraints
    if isinstance(shift_constraints, dict):
        min_hours = shift_constraints.get("min_shift_length_hours", 3.0)
        max_hours = shift_constraints.get("max_shift_length_hours", 12.0)
    else:
        min_hours = getattr(shift_constraints, "min_shift_length_hours", 3.0)
        max_hours = getattr(shift_constraints, "max_shift_length_hours", 12.0)

    # Ensure values are not None and are numeric
    min_hours = float(min_hours) if min_hours is not None else 3.0
    max_hours = float(max_hours) if max_hours is not None else 12.0

    for row in roster_rows:
        hours = row.get("Hours", 0)
        hours = float(hours) if hours is not None else 0.0

        if min_hours is not None and hours < min_hours:
            violations.append(
                Violation(
                    type="shift_length",
                    severity="critical",
                    employee=row.get("Employee Name", ""),
                    date=row.get("Date", ""),
                    shift_code=row.get("Shift Code", ""),
                    message=f"Shift length {hours} hours is below minimum {min_hours} hours",
                    recommendation=f"Increase shift length to at least {min_hours} hours",
                )
            )
        if max_hours is not None and hours > max_hours:
            violations.append(
                Violation(
                    type="shift_length",
                    severity="critical",
                    employee=row.get("Employee Name", ""),
                    date=row.get("Date", ""),
                    shift_code=row.get("Shift Code", ""),
                    message=f"Shift length {hours} hours exceeds maximum {max_hours} hours",
                    recommendation=f"Reduce shift length to maximum {max_hours} hours",
                )
            )

    return violations


def _check_rest_periods(
    roster_rows: List[Dict[str, Any]],
    constraints: Dict[str, Any],
) -> List[Violation]:
    """Check minimum rest periods between shifts (10 hours)"""
    violations = []
    shift_constraints = (
        constraints.get("shift_constraints", {})
        if isinstance(constraints, dict)
        else getattr(constraints, "shift_constraints", {})
    )

    # Handle both dict and object for shift_constraints
    if isinstance(shift_constraints, dict):
        min_rest_hours = shift_constraints.get("min_rest_between_shifts_hours", 10.0)
    else:
        min_rest_hours = getattr(
            shift_constraints, "min_rest_between_shifts_hours", 10.0
        )

    # Ensure value is not None and is numeric
    min_rest_hours = float(min_rest_hours) if min_rest_hours is not None else 10.0

    # Group by employee
    employee_shifts = {}
    for row in roster_rows:
        emp_name = row.get("Employee Name", "")
        if emp_name not in employee_shifts:
            employee_shifts[emp_name] = []
        employee_shifts[emp_name].append(row)

    for emp_name, shifts in employee_shifts.items():
        # Sort by date and time
        shifts.sort(key=lambda x: (x.get("Date", ""), x.get("Shift Time", "")))

        for i in range(len(shifts) - 1):
            current = shifts[i]
            next_shift = shifts[i + 1]

            try:
                current_date = datetime.strptime(current.get("Date", ""), "%Y-%m-%d")
                next_date = datetime.strptime(next_shift.get("Date", ""), "%Y-%m-%d")

                # Parse shift times
                current_time_str = current.get("Shift Time", "").split(" - ")[
                    -1
                ]  # End time
                next_time_str = next_shift.get("Shift Time", "").split(" - ")[
                    0
                ]  # Start time

                # Calculate time difference
                if current_time_str and next_time_str:
                    try:
                        current_end = datetime.strptime(
                            current_time_str, "%H:%M"
                        ).time()
                        next_start = datetime.strptime(next_time_str, "%H:%M").time()

                        current_datetime = datetime.combine(
                            current_date.date(), current_end
                        )
                        next_datetime = datetime.combine(next_date.date(), next_start)

                        rest_hours = (
                            next_datetime - current_datetime
                        ).total_seconds() / 3600

                        if min_rest_hours is not None and rest_hours < min_rest_hours:
                            violations.append(
                                Violation(
                                    type="rest_period",
                                    severity="critical",
                                    employee=emp_name,
                                    date=next_shift.get("Date", ""),
                                    shift_code=next_shift.get("Shift Code", ""),
                                    message=f"Employee {emp_name} has only {rest_hours:.1f} hours rest between shifts (minimum {min_rest_hours} required)",
                                    recommendation=f"Ensure at least {min_rest_hours} hours rest between shifts",
                                )
                            )
                    except Exception:
                        pass  # Skip if time parsing fails
            except Exception:
                pass  # Skip if date parsing fails

    return violations


def _check_store_requirements(
    roster_rows: List[Dict[str, Any]],
    store_config: Dict[str, Any],
) -> List[Violation]:
    """Check if store requirements are met"""
    violations = []

    # Group by store and date
    store_shifts = {}
    for row in roster_rows:
        store = row.get("Store", "")
        date = row.get("Date", "")
        key = (store, date)
        if key not in store_shifts:
            store_shifts[key] = []
        store_shifts[key].append(row)

    stores = store_config.get("stores", [])
    for store_info in stores:
        store_name = store_info.get("storeName", "")
        structure = store_info.get("storeStructure", {})

        # Check if store has required stations
        required_stations = []
        if structure.get("kitchen"):
            required_stations.append("Kitchen")
        if structure.get("counter"):
            required_stations.append("Counter")
        if structure.get("multipleMcCafe"):
            required_stations.append("Multi-Station McCafe")
        if structure.get("dessertStation"):
            required_stations.append("Dessert Station")

        # Check coverage for each day
        for (store, date), rows in store_shifts.items():
            if store_name in store:
                stations_covered = set(r.get("Station", "") for r in rows)
                missing_stations = set(required_stations) - stations_covered

                if missing_stations:
                    violations.append(
                        Violation(
                            type="store_coverage",
                            severity="warning",
                            date=date,
                            message=f"Store {store_name} missing coverage for stations: {', '.join(missing_stations)} on {date}",
                            recommendation=f"Assign employees to cover {', '.join(missing_stations)} stations",
                        )
                    )

    return violations


def validate_roster(
    roster_rows: List[Dict[str, Any]],
    employees: List[Dict[str, Any]],
    constraints: Dict[str, Any],
    store_config: Dict[str, Any],
    managers: List[str],
) -> List[Violation]:
    """
    Validate roster against all constraints and return list of violations.

    Args:
        roster_rows: List of roster row dictionaries
        employees: List of employee dictionaries with availability
        constraints: Constraints from Agent 2
        store_config: Store configuration
        managers: List of manager names

    Returns:
        List of Violation objects
    """
    violations = []

    # 1. Check employee availability
    for row in roster_rows:
        violation = _check_employee_availability(
            row.get("Employee Name", ""),
            row.get("Date", ""),
            row.get("Shift Code", ""),
            employees,
        )
        if violation:
            violations.append(violation)

    # 2. Check manager coverage
    violations.extend(_check_manager_coverage(roster_rows, managers))

    # 3. Check shift length constraints
    violations.extend(_check_shift_length_constraints(roster_rows, constraints))

    # 4. Check rest periods
    violations.extend(_check_rest_periods(roster_rows, constraints))

    # 5. Check store requirements
    violations.extend(_check_store_requirements(roster_rows, store_config))

    return violations


@tool(
    "validate_roster",
    description="Validate the generated roster against all constraints, employee availability, and compliance rules. Returns a list of violations if any are found.",
)
def validate_roster_tool(
    runtime: ToolRuntime = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Command:
    """
    Tool that validates roster using state data.
    Uses ToolRuntime to access current state and InjectedToolCallId for proper response.
    """
    if runtime is None:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="Error: ToolRuntime not available. Cannot validate roster without state.",
                        tool_call_id=tool_call_id or "",
                    )
                ]
            }
        )

    state = runtime.state

    # Extract data from state
    if isinstance(state, dict):
        roster = state.get("roster", {})
        structured_data = state.get("structured_data", {})
        constraints = state.get("constraints", {})
        store_requirements = state.get("store_requirements", {})
    else:
        roster = getattr(state, "roster", {})
        structured_data = getattr(state, "structured_data", {})
        constraints = getattr(state, "constraints", {})
        store_requirements = getattr(state, "store_requirements", {})

    roster_rows = roster.get("shifts", [])
    employees = structured_data.get("employees", {}).get("employees", [])

    # Get managers
    from agent_3.agent import _identify_managers

    managers = _identify_managers(employees)

    # Get store config
    from agent_3.agent import _get_store_config

    store_config = _get_store_config(store_requirements)

    # Validate roster
    violations = validate_roster(
        roster_rows, employees, constraints, store_config, managers
    )

    # Convert violations to dict for state
    violations_list = [
        {
            "type": v.type,
            "severity": v.severity,
            "employee": v.employee,
            "date": v.date,
            "shift_code": v.shift_code,
            "message": v.message,
            "recommendation": v.recommendation,
        }
        for v in violations
    ]

    # Determine next action based on violations
    iteration_count = (
        state.get("iteration_count", 0)
        if isinstance(state, dict)
        else getattr(state, "iteration_count", 0)
    )
    max_iterations = 4

    if violations and iteration_count < max_iterations:
        # Return Command to go back to Agent 3 for regeneration
        critical_count = sum(1 for v in violations if v.severity == "critical")
        return Command(
            goto="agent_3",
            update={
                "violations": violations_list,
                "iteration_count": iteration_count + 1,
                "messages": [
                    ToolMessage(
                        content=f"Found {len(violations)} violations ({critical_count} critical). Regenerating roster (iteration {iteration_count + 1}/5)...",
                        tool_call_id=tool_call_id,
                    )
                ],
            },
        )
    else:
        # No violations or max iterations reached - finish
        status_message = (
            f"Validation complete. {len(violations)} violations found after {iteration_count} iterations."
            if violations
            else f"Validation complete. No violations found. Roster is compliant after {iteration_count} iterations."
        )

        return Command(
            update={
                "violations": violations_list,
                "validation_complete": True,
                "iteration_count": iteration_count,
                "messages": [
                    ToolMessage(
                        content=status_message,
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )


def run_agent4(
    state: Optional[MultiAgentState] = None,
) -> dict:
    """
    Run Agent 4: Validate roster against all constraints.

    Args:
        state: MultiAgentState containing roster and constraints

    Returns:
        Dictionary containing validation results and violations
    """
    if state is None:
        return {
            "status": "error",
            "message": "No state provided. Cannot validate roster.",
            "violations": [],
        }

    # Extract data
    if isinstance(state, dict):
        roster = state.get("roster", {})
        structured_data = state.get("structured_data", {})
        constraints = state.get("constraints", {}) or {}  # Ensure not None
        store_requirements = state.get("store_requirements", {})
    else:
        roster = getattr(state, "roster", {})
        structured_data = getattr(state, "structured_data", {})
        constraints = getattr(state, "constraints", {}) or {}  # Ensure not None
        store_requirements = getattr(state, "store_requirements", {})

    roster_rows = roster.get("shifts", [])
    employees = structured_data.get("employees", {}).get("employees", [])

    if not roster_rows:
        return {
            "status": "error",
            "message": "No roster found in state. Run Agent 3 first.",
            "violations": [],
        }

    # Get managers and store config
    from agent_3.agent import _identify_managers, _get_store_config

    managers = _identify_managers(employees)
    store_config = _get_store_config(store_requirements)

    # Validate roster
    violations = validate_roster(
        roster_rows, employees, constraints, store_config, managers
    )

    # Convert to dict
    violations_list = [
        {
            "type": v.type,
            "severity": v.severity,
            "employee": v.employee,
            "date": v.date,
            "shift_code": v.shift_code,
            "message": v.message,
            "recommendation": v.recommendation,
        }
        for v in violations
    ]

    return {
        "status": "success",
        "violations": violations_list,
        "violation_count": len(violations),
        "critical_count": sum(1 for v in violations if v.severity == "critical"),
        "warning_count": sum(1 for v in violations if v.severity == "warning"),
        "is_compliant": len(violations) == 0,
        "message": (
            f"Found {len(violations)} violations"
            if violations
            else "No violations found. Roster is compliant."
        ),
    }


if __name__ == "__main__":
    # Test with mock state
    from agent_1.agent import run_agent1
    from agent_2.agent import run_agent2
    from agent_3.agent import run_agent3

    print("Running full pipeline to test Agent 4...")
    result1 = run_agent1()
    state1 = result1.get("state_update", {})
    result2 = run_agent2(state=state1)
    state2 = result2.get("state_update", {})

    multi_state = MultiAgentState(
        employee_data=state2.get("employee_data", []),
        store_requirements=state2.get("store_requirements", {}),
        management_store=state2.get("management_store", {}),
        structured_data=state2.get("structured_data", {}),
        constraints=state2.get("constraints", {}),
        rules_data=state2.get("rules_data", {}),
        store_rules_data=state2.get("store_rules_data", {}),
        roster={},
        roster_metadata={},
        messages=state2.get("messages", []),
    )

    result3 = run_agent3(state=multi_state, use_llm=False)
    updated_state = result3.get("state", {})

    # Update state with roster
    if isinstance(updated_state, dict):
        multi_state.roster = updated_state.get("roster", {})
    else:
        multi_state.roster = (
            updated_state.roster if hasattr(updated_state, "roster") else {}
        )

    print("\nRunning Agent 4...")
    result4 = run_agent4(state=multi_state)

    print("\n" + "=" * 50)
    print("Agent 4 Validation Result:")
    print("=" * 50)
    print(json.dumps(result4, indent=2, default=str))
