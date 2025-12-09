"""
Agent 5: Final Roster Validator and Report Generator
Performs comprehensive final checks:
1. Confirms this is the final roster
2. Checks if all employee availability slots are filled
3. Verifies staffing requirements (e.g., 6 needed in kitchen, check if 6 are assigned)
4. Generates final roster and comprehensive check report
"""

import json
import os
import pandas as pd
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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_state import MultiAgentState

load_dotenv()


class AvailabilityCheck(BaseModel):
    """Represents an availability slot check"""

    employee_name: str = Field(description="Employee name")
    employee_id: str = Field(description="Employee ID")
    date: str = Field(description="Date of availability")
    day_key: str = Field(description="Day key (Day_1, Day_2, etc.)")
    available_shift: str = Field(description="Shift code employee is available for")
    assigned: bool = Field(description="Whether this availability slot is filled")
    assigned_shift: str = Field(
        default="", description="Assigned shift code if assigned"
    )
    status: str = Field(description="Status: filled, unfilled, mismatch")


class StaffingCheck(BaseModel):
    """Represents a staffing requirement check"""

    store: str = Field(description="Store name")
    date: str = Field(description="Date")
    station: str = Field(description="Station name (Kitchen, Counter, etc.)")
    required: int = Field(description="Required number of staff")
    assigned: int = Field(description="Number of staff assigned")
    status: str = Field(description="Status: met, understaffed, overstaffed")
    details: str = Field(default="", description="Additional details")


class FinalCheckReport(BaseModel):
    """Final comprehensive check report"""

    roster_status: str = Field(
        description="Overall roster status: approved, needs_review"
    )
    total_availability_slots: int = Field(
        description="Total employee availability slots"
    )
    filled_slots: int = Field(description="Number of filled slots")
    unfilled_slots: int = Field(description="Number of unfilled slots")
    availability_coverage_percent: float = Field(
        description="Percentage of availability covered"
    )
    staffing_checks: List[StaffingCheck] = Field(
        default_factory=list, description="Staffing requirement checks"
    )
    availability_checks: List[AvailabilityCheck] = Field(
        default_factory=list, description="Availability slot checks"
    )
    summary: str = Field(description="Summary of final checks")
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations"
    )


# Default staffing requirements per store per station
# These can be overridden by store config
DEFAULT_STAFFING_REQUIREMENTS = {
    "Store 1: CBD Core Area": {
        "Kitchen": 6,  # 6 people needed in kitchen
        "Counter": 4,
        "Multi-Station McCafe": 3,
        "Dessert Station": 2,
    },
    "Store 2: Suburban Residential": {
        "Kitchen": 4,
        "Counter": 3,
        "Multi-Station McCafe": 2,
        "Dessert Station": 0,  # No dessert station in Store 2
    },
}


def _get_staffing_requirements(
    store_config: Dict[str, Any],
) -> Dict[str, Dict[str, int]]:
    """Get staffing requirements from store config or use defaults"""
    requirements = DEFAULT_STAFFING_REQUIREMENTS.copy()

    # Try to extract from store config if available
    stores = store_config.get("stores", [])
    for store_info in stores:
        store_name = store_info.get("storeName", "")
        structure = store_info.get("storeStructure", {})

        if store_name not in requirements:
            requirements[store_name] = {}

        # Set requirements based on store structure
        if structure.get("kitchen"):
            requirements[store_name]["Kitchen"] = requirements[store_name].get(
                "Kitchen", 6
            )
        if structure.get("counter"):
            requirements[store_name]["Counter"] = requirements[store_name].get(
                "Counter", 4
            )
        if structure.get("multipleMcCafe"):
            requirements[store_name]["Multi-Station McCafe"] = requirements[
                store_name
            ].get("Multi-Station McCafe", 3)
        if structure.get("dessertStation"):
            requirements[store_name]["Dessert Station"] = requirements[store_name].get(
                "Dessert Station", 2
            )

    return requirements


def _check_availability_coverage(
    roster_rows: List[Dict[str, Any]], employees: List[Dict[str, Any]]
) -> List[AvailabilityCheck]:
    """Check if all employee availability slots are filled"""
    checks = []

    # Create a map of roster assignments by employee and date
    roster_map = {}
    for row in roster_rows:
        emp_name = row.get("Employee Name", "")
        date = row.get("Date", "")
        shift_code = row.get("Shift Code", "")
        key = (emp_name, date)
        roster_map[key] = shift_code

    # Check each employee's availability
    for emp in employees:
        emp_name = emp.get("name", "")
        emp_id = emp.get("id", "")
        availability = emp.get("availability", {})

        # Check each day in availability
        for day_key, available_shift in availability.items():
            if not available_shift or available_shift in ["/", "NA", ""]:
                continue  # Skip days off

            # Calculate date from day_key (Day_1, Day_2, etc.)
            # Match Agent 3's date calculation logic
            try:
                day_num = None
                if "_" in day_key:
                    try:
                        day_num = int(day_key.split("_")[1])
                    except ValueError:
                        pass

                if day_num:
                    # Use same logic as Agent 3: start_date = datetime.now().date()
                    start_date = datetime.now().date()
                    date = (start_date + timedelta(days=day_num - 1)).strftime(
                        "%Y-%m-%d"
                    )
                else:
                    # Try to parse from day name in availability keys
                    day_names = [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday",
                        "Sunday",
                    ]
                    date_found = False
                    for i, day_name in enumerate(day_names):
                        if (
                            day_name[:3].lower() in day_key.lower()
                            or day_name.lower() in day_key.lower()
                        ):
                            start_date = datetime.now().date()
                            # Find next occurrence of this weekday (matching Agent 3 logic)
                            days_ahead = (i - start_date.weekday()) % 7
                            if days_ahead == 0:
                                days_ahead = 7
                            date = (
                                start_date + timedelta(days=days_ahead - 1)
                            ).strftime("%Y-%m-%d")
                            date_found = True
                            break

                    if not date_found:
                        continue
            except Exception as e:
                # Skip if date calculation fails
                continue

            # Check if this availability slot is filled
            roster_key = (emp_name, date)
            assigned_shift = roster_map.get(roster_key, "")

            if assigned_shift:
                # Check if assigned shift matches available shift
                if assigned_shift == available_shift or assigned_shift in [
                    "1F",
                    "2F",
                    "3F",
                ]:
                    status = "filled"
                else:
                    status = "mismatch"
            else:
                status = "unfilled"

            checks.append(
                AvailabilityCheck(
                    employee_name=emp_name,
                    employee_id=emp_id,
                    date=date,
                    day_key=day_key,
                    available_shift=available_shift,
                    assigned=(status == "filled"),
                    assigned_shift=assigned_shift,
                    status=status,
                )
            )

    return checks


def _check_staffing_requirements(
    roster_rows: List[Dict[str, Any]], store_config: Dict[str, Any]
) -> List[StaffingCheck]:
    """Check if staffing requirements are met per store, per station, per day"""
    checks = []
    requirements = _get_staffing_requirements(store_config)

    # Group roster by store, date, and station
    staffing_map = {}
    for row in roster_rows:
        store = row.get("Store", "")
        date = row.get("Date", "")
        station = row.get("Station", "")
        key = (store, date, station)

        if key not in staffing_map:
            staffing_map[key] = 0
        staffing_map[key] += 1

    # Check each store's requirements
    for store_name, station_reqs in requirements.items():
        # Get all dates from roster
        dates = set(
            row.get("Date", "")
            for row in roster_rows
            if store_name in row.get("Store", "")
        )

        for date in dates:
            for station, required_count in station_reqs.items():
                key = (store_name, date, station)
                assigned_count = staffing_map.get(key, 0)

                if assigned_count >= required_count:
                    status = "met"
                elif assigned_count == 0:
                    status = "understaffed"
                else:
                    status = "understaffed"

                details = f"Required: {required_count}, Assigned: {assigned_count}"
                if status == "understaffed":
                    details += f" (Shortage: {required_count - assigned_count})"

                checks.append(
                    StaffingCheck(
                        store=store_name,
                        date=date,
                        station=station,
                        required=required_count,
                        assigned=assigned_count,
                        status=status,
                        details=details,
                    )
                )

    return checks


def _generate_final_report(
    availability_checks: List[AvailabilityCheck],
    staffing_checks: List[StaffingCheck],
    roster_rows: List[Dict[str, Any]],
) -> FinalCheckReport:
    """Generate comprehensive final check report"""
    total_slots = len(availability_checks)
    filled_slots = sum(1 for check in availability_checks if check.status == "filled")
    unfilled_slots = sum(
        1 for check in availability_checks if check.status == "unfilled"
    )
    mismatch_slots = sum(
        1 for check in availability_checks if check.status == "mismatch"
    )

    coverage_percent = (filled_slots / total_slots * 100) if total_slots > 0 else 0

    # Check staffing status
    understaffed = sum(1 for check in staffing_checks if check.status == "understaffed")
    staffing_met = sum(1 for check in staffing_checks if check.status == "met")

    # Determine overall status
    if unfilled_slots == 0 and mismatch_slots == 0 and understaffed == 0:
        roster_status = "approved"
        summary = "✅ Roster is complete and meets all requirements."
    elif unfilled_slots <= 5 and understaffed <= 3:
        roster_status = "needs_review"
        summary = "⚠️ Roster is mostly complete but has minor issues that need review."
    else:
        roster_status = "needs_review"
        summary = "❌ Roster has significant gaps that need attention."

    # Generate recommendations
    recommendations = []
    if unfilled_slots > 0:
        recommendations.append(
            f"Fill {unfilled_slots} unfilled availability slots to maximize employee utilization."
        )
    if mismatch_slots > 0:
        recommendations.append(
            f"Review {mismatch_slots} shift assignments that don't match employee availability preferences."
        )
    if understaffed > 0:
        recommendations.append(
            f"Address {understaffed} understaffed stations to meet operational requirements."
        )
    if not recommendations:
        recommendations.append("Roster is optimal. No changes needed.")

    return FinalCheckReport(
        roster_status=roster_status,
        total_availability_slots=total_slots,
        filled_slots=filled_slots,
        unfilled_slots=unfilled_slots,
        availability_coverage_percent=round(coverage_percent, 2),
        staffing_checks=staffing_checks,
        availability_checks=availability_checks,
        summary=summary,
        recommendations=recommendations,
    )


def _export_check_report(report: FinalCheckReport, output_path: str) -> str:
    """Export check report to JSON and text file"""
    # Export as JSON
    json_path = output_path.replace(".txt", ".json")
    with open(json_path, "w") as f:
        json.dump(
            {
                "roster_status": report.roster_status,
                "total_availability_slots": report.total_availability_slots,
                "filled_slots": report.filled_slots,
                "unfilled_slots": report.unfilled_slots,
                "availability_coverage_percent": report.availability_coverage_percent,
                "staffing_checks": [
                    {
                        "store": check.store,
                        "date": check.date,
                        "station": check.station,
                        "required": check.required,
                        "assigned": check.assigned,
                        "status": check.status,
                        "details": check.details,
                    }
                    for check in report.staffing_checks
                ],
                "availability_checks": [
                    {
                        "employee_name": check.employee_name,
                        "employee_id": check.employee_id,
                        "date": check.date,
                        "day_key": check.day_key,
                        "available_shift": check.available_shift,
                        "assigned": check.assigned,
                        "assigned_shift": check.assigned_shift,
                        "status": check.status,
                    }
                    for check in report.availability_checks
                ],
                "summary": report.summary,
                "recommendations": report.recommendations,
            },
            f,
            indent=2,
            default=str,
        )

    # Export as readable text file
    with open(output_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("FINAL ROSTER CHECK REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write(f"ROSTER STATUS: {report.roster_status.upper()}\n")
        f.write(f"{report.summary}\n\n")

        f.write("-" * 80 + "\n")
        f.write("AVAILABILITY COVERAGE\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Availability Slots: {report.total_availability_slots}\n")
        f.write(f"Filled Slots: {report.filled_slots}\n")
        f.write(f"Unfilled Slots: {report.unfilled_slots}\n")
        f.write(f"Coverage: {report.availability_coverage_percent}%\n\n")

        if report.unfilled_slots > 0:
            f.write("UNFILLED AVAILABILITY SLOTS:\n")
            for check in report.availability_checks:
                if check.status == "unfilled":
                    f.write(
                        f"  - {check.employee_name} ({check.employee_id}) on {check.date}: "
                        f"Available for {check.available_shift}, but not assigned\n"
                    )
            f.write("\n")

        f.write("-" * 80 + "\n")
        f.write("STAFFING REQUIREMENTS CHECK\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total Staffing Checks: {len(report.staffing_checks)}\n")
        f.write(
            f"Requirements Met: {sum(1 for c in report.staffing_checks if c.status == 'met')}\n"
        )
        f.write(
            f"Understaffed: {sum(1 for c in report.staffing_checks if c.status == 'understaffed')}\n\n"
        )

        # Group by store and date
        by_store_date = {}
        for check in report.staffing_checks:
            key = (check.store, check.date)
            if key not in by_store_date:
                by_store_date[key] = []
            by_store_date[key].append(check)

        for (store, date), checks in sorted(by_store_date.items()):
            f.write(f"\n{store} - {date}:\n")
            for check in checks:
                status_icon = "✅" if check.status == "met" else "❌"
                f.write(
                    f"  {status_icon} {check.station}: {check.assigned}/{check.required} "
                    f"({check.status})\n"
                )
                if check.status == "understaffed":
                    f.write(f"     ⚠️  {check.details}\n")

        f.write("\n" + "-" * 80 + "\n")
        f.write("RECOMMENDATIONS\n")
        f.write("-" * 80 + "\n")
        for i, rec in enumerate(report.recommendations, 1):
            f.write(f"{i}. {rec}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")

    return output_path


@tool(
    "final_roster_check",
    description="Perform final comprehensive check on the roster: verify all availability slots are filled, check staffing requirements (e.g., 6 needed in kitchen), and generate final roster and check report. This confirms the roster is final and ready.",
)
def final_roster_check_tool(
    runtime: ToolRuntime = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Command:
    """
    Tool that performs final roster validation and generates comprehensive report.
    Uses ToolRuntime to access current state and InjectedToolCallId for proper response.
    """
    if runtime is None:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="Error: ToolRuntime not available. Cannot perform final check without state.",
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
        store_requirements = state.get("store_requirements", {})
    else:
        roster = getattr(state, "roster", {})
        structured_data = getattr(state, "structured_data", {})
        store_requirements = getattr(state, "store_requirements", {})

    roster_rows = roster.get("shifts", [])
    employees = structured_data.get("employees", {}).get("employees", [])

    if not roster_rows:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="Error: No roster found in state. Cannot perform final check.",
                        tool_call_id=tool_call_id or "",
                    )
                ]
            }
        )

    # Get store config
    from agent_3.agent import _get_store_config

    store_config = _get_store_config(store_requirements)

    # Perform checks
    print("Performing availability coverage check...")
    availability_checks = _check_availability_coverage(roster_rows, employees)

    print("Performing staffing requirements check...")
    staffing_checks = _check_staffing_requirements(roster_rows, store_config)

    # Generate final report
    print("Generating final check report...")
    report = _generate_final_report(availability_checks, staffing_checks, roster_rows)

    # Export report
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(current_dir, "rag")
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "final_roster_check_report.txt")

    try:
        _export_check_report(report, report_path)
        report_message = f"Final check report saved to {report_path}"
    except Exception as e:
        report_message = f"Warning: Could not save check report: {str(e)}"

    # Prepare final summary
    summary_message = f"""
FINAL ROSTER CHECK COMPLETE

Status: {report.roster_status.upper()}
{report.summary}

Availability Coverage: {report.availability_coverage_percent}% ({report.filled_slots}/{report.total_availability_slots} slots filled)
Staffing Requirements: {sum(1 for c in report.staffing_checks if c.status == 'met')}/{len(report.staffing_checks)} met

{report_message}
"""

    return Command(
        update={
            "final_check_report": {
                "roster_status": report.roster_status,
                "availability_coverage_percent": report.availability_coverage_percent,
                "filled_slots": report.filled_slots,
                "total_slots": report.total_availability_slots,
                "staffing_checks_passed": sum(
                    1 for c in report.staffing_checks if c.status == "met"
                ),
                "total_staffing_checks": len(report.staffing_checks),
                "report_path": report_path if "saved" in report_message else None,
                "summary": report.summary,
                "recommendations": report.recommendations,
            },
            "final_check_complete": True,
            "messages": [
                ToolMessage(
                    content=summary_message,
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )


def run_agent5(state: Optional[MultiAgentState] = None) -> dict:
    """
    Run Agent 5: Final roster validation and report generation.

    Args:
        state: MultiAgentState containing final roster

    Returns:
        Dictionary containing final check results and report
    """
    if state is None:
        return {
            "status": "error",
            "message": "No state provided. Cannot perform final check.",
            "report": None,
        }

    # Extract data
    if isinstance(state, dict):
        roster = state.get("roster", {})
        structured_data = state.get("structured_data", {})
        store_requirements = state.get("store_requirements", {})
    else:
        roster = getattr(state, "roster", {})
        structured_data = getattr(state, "structured_data", {})
        store_requirements = getattr(state, "store_requirements", {})

    roster_rows = roster.get("shifts", [])
    employees = structured_data.get("employees", {}).get("employees", [])

    if not roster_rows:
        return {
            "status": "error",
            "message": "No roster found in state. Run Agent 3 first.",
            "report": None,
        }

    # Get store config
    from agent_3.agent import _get_store_config

    store_config = _get_store_config(store_requirements)

    # Perform checks
    print("Performing availability coverage check...")
    availability_checks = _check_availability_coverage(roster_rows, employees)

    print("Performing staffing requirements check...")
    staffing_checks = _check_staffing_requirements(roster_rows, store_config)

    # Generate final report
    print("Generating final check report...")
    report = _generate_final_report(availability_checks, staffing_checks, roster_rows)

    # Export report
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(current_dir, "rag")
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, "final_roster_check_report.txt")

    try:
        _export_check_report(report, report_path)
        report_saved = True
    except Exception as e:
        print(f"Warning: Could not save check report: {e}")
        report_saved = False

    return {
        "status": "success",
        "roster_status": report.roster_status,
        "availability_coverage_percent": report.availability_coverage_percent,
        "filled_slots": report.filled_slots,
        "total_slots": report.total_availability_slots,
        "unfilled_slots": report.unfilled_slots,
        "staffing_checks": [
            {
                "store": check.store,
                "date": check.date,
                "station": check.station,
                "required": check.required,
                "assigned": check.assigned,
                "status": check.status,
                "details": check.details,
            }
            for check in report.staffing_checks
        ],
        "availability_checks": [
            {
                "employee_name": check.employee_name,
                "employee_id": check.employee_id,
                "date": check.date,
                "available_shift": check.available_shift,
                "assigned": check.assigned,
                "status": check.status,
            }
            for check in report.availability_checks
        ],
        "summary": report.summary,
        "recommendations": report.recommendations,
        "report_path": report_path if report_saved else None,
        "message": "Final roster check completed successfully",
    }


if __name__ == "__main__":
    # Test with mock state
    from agent_1.agent import run_agent1
    from agent_2.agent import run_agent2
    from agent_3.agent import run_agent3
    from agent_4.agent import run_agent4

    print("Running full pipeline to test Agent 5...")
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

    if isinstance(updated_state, dict):
        multi_state.roster = updated_state.get("roster", {})
    else:
        multi_state.roster = (
            updated_state.roster if hasattr(updated_state, "roster") else {}
        )

    result4 = run_agent4(state=multi_state)
    violations = result4.get("violations", [])

    print("\nRunning Agent 5...")
    result5 = run_agent5(state=multi_state)

    print("\n" + "=" * 50)
    print("Agent 5 Final Check Result:")
    print("=" * 50)
    print(json.dumps(result5, indent=2, default=str))
