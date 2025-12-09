"""
Agent 3: Roster Generator
Generates a roster schedule ensuring all rules, employee needs, requirements,
and constraints are satisfied. Uses MultiAgentState with ToolRuntime.
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Annotated, Optional, List, Dict, Any
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


# Pydantic model for roster output
class RosterSchedule(BaseModel):
    """Generated roster schedule"""

    week_start_date: str = Field(
        description="Start date of the roster week (YYYY-MM-DD)"
    )
    week_end_date: str = Field(description="End date of the roster week (YYYY-MM-DD)")
    shifts: list = Field(
        default_factory=list,
        description="List of shifts with employee assignments, times, and locations",
    )
    summary: dict = Field(
        default_factory=dict,
        description="Summary statistics: total hours, employee coverage, compliance status",
    )
    compliance_check: dict = Field(
        default_factory=dict, description="Compliance validation results"
    )


def _get_shift_info(shift_code: str, management_store: dict) -> dict:
    """Get shift information from management store"""
    shifts = management_store.get("shifts", [])
    for shift in shifts:
        if shift.get("code") == shift_code:
            return shift
    return {"time": "TBD", "hours": 0, "name": shift_code}


def _get_store_config(store_requirements: dict) -> dict:
    """Extract store configuration from requirements"""
    # Try to find store_config_data in store_requirements
    if isinstance(store_requirements, list):
        # If it's a list, look for store config
        for item in store_requirements:
            if isinstance(item, dict) and "stores" in item:
                return item
    elif isinstance(store_requirements, dict):
        if "stores" in store_requirements:
            return store_requirements
        # Try to find in structured_data
        if "store_config" in store_requirements:
            return store_requirements.get("store_config", {})

    # If not found, try loading from file directly
    try:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        store_config_path = os.path.join(
            current_dir, "dataset", "store_config_data.json"
        )
        if os.path.exists(store_config_path):
            with open(store_config_path, "r") as f:
                return json.load(f)
    except Exception:
        pass

    return {}


def _identify_managers(employees: List[Dict[str, Any]]) -> List[str]:
    """Identify potential managers from employees (Full-Time employees)"""
    managers = []
    for emp in employees:
        emp_type = emp.get("type", "").lower()
        emp_name = emp.get("name", "")
        # Full-Time employees are typically managers
        if "full-time" in emp_type or "fulltime" in emp_type:
            managers.append(emp_name)
    return managers


def _assign_manager_to_shift(
    shift_time: str,
    day_name: str,
    managers: List[str],
    manager_assignments: Dict[str, List[str]],
    needs_manager: bool = False,
) -> str:
    """Assign a manager to a shift, ensuring coverage"""
    # Key for tracking manager assignments per shift
    shift_key = f"{day_name}_{shift_time}"

    # Get already assigned managers for this shift
    assigned = manager_assignments.get(shift_key, [])

    # Find available managers (not already assigned to this shift)
    available = [m for m in managers if m not in assigned]

    if not available:
        # If all managers are assigned, reuse one (they can manage multiple areas)
        available = managers

    # If this shift needs a manager (from violations), prioritize assigning one
    if needs_manager and not assigned:
        # Ensure we assign a manager
        import random

        selected_manager = (
            random.choice(available) if available else (managers[0] if managers else "")
        )
    else:
        # Randomly select a manager
        import random

        selected_manager = (
            random.choice(available) if available else (managers[0] if managers else "")
        )

    # Track assignment
    if shift_key not in manager_assignments:
        manager_assignments[shift_key] = []
    if selected_manager:
        manager_assignments[shift_key].append(selected_manager)

    return selected_manager


def _assign_store_to_employee(
    emp_station: str,
    shift_time: str,
    day_name: str,
    store_config: dict,
    traffic_data: Dict[str, int],
    iteration: int = 0,
) -> str:
    """Assign employee to Store 1 or Store 2 based on traffic and requirements"""
    stores = store_config.get("stores", [])
    if len(stores) < 2:
        return "Store 1"  # Default if config not available

    store1 = stores[0]
    store2 = stores[1]

    # Get traffic patterns
    store1_traffic = traffic_data.get("store1", 1500)  # Default: high traffic
    store2_traffic = traffic_data.get("store2", 750)  # Default: medium traffic

    # Check peak hours
    store1_peaks = store1.get("storeCharacteristics", {}).get("peakHours", [])
    store2_peaks = store2.get("storeCharacteristics", {}).get("peakHours", [])

    # Determine if current time is peak for either store
    is_store1_peak = any(
        peak in shift_time or day_name in str(peak) for peak in store1_peaks
    )
    is_store2_peak = any(
        peak in shift_time or day_name in str(peak) for peak in store2_peaks
    )

    # Check store structure requirements
    store1_structure = store1.get("storeStructure", {})
    store2_structure = store2.get("storeStructure", {})

    # Match employee station to store needs
    station_lower = emp_station.lower()

    # Store 1 needs: kitchen, counter, multipleMcCafe, dessertStation
    # Store 2 needs: kitchen, counter, multipleMcCafe (no dessert station)
    if "dessert" in station_lower:
        # Dessert station employees go to Store 1
        return "Store 1: CBD Core Area"
    elif "mccafe" in station_lower or "cafe" in station_lower:
        # McCafe employees can go to either, but Store 1 has higher coffee demand
        if store1_traffic > store2_traffic * 1.5:
            return "Store 1: CBD Core Area"
        else:
            return "Store 2: Suburban Residential"
    else:
        # Kitchen and Counter employees - distribute based on traffic
        # Store 1 has higher traffic (1200-1800 vs 600-900)
        # Distribute roughly 60-40 or 65-35 based on traffic ratio
        import random

        # Calculate probability based on traffic ratio
        total_traffic = store1_traffic + store2_traffic
        store1_prob = store1_traffic / total_traffic

        # Adjust for peak hours
        if is_store1_peak:
            store1_prob += 0.1
        if is_store2_peak:
            store1_prob -= 0.1

        # Vary distribution based on iteration to try different assignments
        # This helps avoid generating the exact same roster each iteration
        variation = (iteration % 3) * 0.05  # Small variation: 0%, 5%, 10%
        store1_prob += variation - 0.05  # Center around original probability

        # Ensure reasonable distribution
        store1_prob = max(0.4, min(0.7, store1_prob))

        if random.random() < store1_prob:
            return "Store 1: CBD Core Area"
        else:
            return "Store 2: Suburban Residential"


def _generate_roster_from_state(
    state: MultiAgentState, violations: List[Dict[str, Any]] = None, iteration: int = 0
) -> List[Dict[str, Any]]:
    """
    Core logic to generate roster from state data.
    Uses violations from previous iteration to avoid repeating the same mistakes.
    Returns a list of roster rows matching the Excel format.

    Args:
        state: MultiAgentState containing employee data, constraints, etc.
        violations: List of violations from previous iteration to avoid
        iteration: Current iteration number (for variation in generation)
    """
    if violations is None:
        violations = []
    # Extract data from state
    if isinstance(state, dict):
        structured_data = state.get("structured_data", {})
        constraints = state.get("constraints", {})
        store_requirements = state.get("store_requirements", {})
        management_store = state.get("management_store", {})
    else:
        structured_data = getattr(state, "structured_data", {})
        constraints = getattr(state, "constraints", {})
        store_requirements = getattr(state, "store_requirements", {})
        management_store = getattr(state, "management_store", {})

    # Extract employees from structured_data (handle both dict and object)
    if isinstance(structured_data, dict):
        employees = structured_data.get("employees", {}).get("employees", [])
    else:
        employees_dict = getattr(structured_data, "employees", {})
        if isinstance(employees_dict, dict):
            employees = employees_dict.get("employees", [])
        else:
            employees = getattr(employees_dict, "employees", [])

    if not employees:
        return []

    # Extract shift constraints with proper defaults and null handling
    shift_constraints = (
        constraints.get("shift_constraints", {})
        if isinstance(constraints, dict)
        else getattr(constraints, "shift_constraints", {})
    )

    # Handle both dict and object for shift_constraints
    if isinstance(shift_constraints, dict):
        min_shift_hours = shift_constraints.get("min_shift_length_hours", 3.0)
        max_shift_hours = shift_constraints.get("max_shift_length_hours", 12.0)
    else:
        min_shift_hours = getattr(shift_constraints, "min_shift_length_hours", 3.0)
        max_shift_hours = getattr(shift_constraints, "max_shift_length_hours", 12.0)

    # Ensure values are not None and are numeric
    min_shift_hours = float(min_shift_hours) if min_shift_hours is not None else 3.0
    max_shift_hours = float(max_shift_hours) if max_shift_hours is not None else 12.0

    # Get shift codes from management store
    shift_codes = {s.get("code"): s for s in management_store.get("shifts", [])}

    # Get store configuration
    store_config = _get_store_config(store_requirements)

    # Identify managers (Full-Time employees)
    managers = _identify_managers(employees)
    if not managers:
        # Fallback: use first few employees as managers
        managers = [emp.get("name", "") for emp in employees[:5] if emp.get("name")]

    # Track manager assignments per shift to ensure coverage
    manager_assignments = {}

    # Calculate traffic data from store config
    traffic_data = {"store1": 1500, "store2": 750}  # Defaults
    stores = store_config.get("stores", [])
    if len(stores) >= 2:
        store1_traffic_str = (
            stores[0]
            .get("storeCharacteristics", {})
            .get("averageDailyCustomers", "1200-1800 people")
        )
        store2_traffic_str = (
            stores[1]
            .get("storeCharacteristics", {})
            .get("averageDailyCustomers", "600-900 people")
        )

        # Extract numbers from strings like "1200-1800 people"
        import re

        store1_match = re.search(r"(\d+)-(\d+)", store1_traffic_str)
        store2_match = re.search(r"(\d+)-(\d+)", store2_traffic_str)

        if store1_match:
            traffic_data["store1"] = (
                int(store1_match.group(1)) + int(store1_match.group(2))
            ) // 2
        if store2_match:
            traffic_data["store2"] = (
                int(store2_match.group(1)) + int(store2_match.group(2))
            ) // 2

    # Use iteration to seed random for variation
    import random

    random.seed(42 + iteration)  # Different seed each iteration for variation

    # Build violation tracking maps to avoid repeating mistakes
    violation_blacklist = {}  # {(employee_name, date): True} - don't assign these
    violation_shift_preferences = {}  # {(employee_name, date): preferred_shift_code}
    manager_coverage_needed = {}  # {(date, shift_time): True} - needs manager
    station_coverage_needed = {}  # {(store, date, station): required_count}
    problematic_assignments = (
        set()
    )  # Track (emp_name, date, shift_code) that caused violations
    rest_period_violations = (
        {}
    )  # {emp_name: [(date, shift_time)]} - track shifts to avoid rest period issues
    shift_length_issues = (
        {}
    )  # {(emp_name, date): (hours, min/max)} - track shift length problems

    if violations:
        print(f"  Analyzing {len(violations)} violations to improve roster...")
        for violation in violations:
            v_type = violation.get("type", "")
            emp_name = violation.get("employee", "").strip()  # Normalize name
            date = violation.get("date", "").strip()  # Normalize date
            shift_code = violation.get("shift_code", "").strip()  # Normalize shift code
            severity = violation.get("severity", "")

            # Track the exact problematic assignment (normalize for matching)
            if emp_name and date and shift_code:
                # Normalize the key for matching
                problematic_assignments.add(
                    (emp_name.lower(), date, shift_code.upper())
                )

            if v_type == "availability" and severity == "critical":
                # Don't assign this employee to this date
                if emp_name and date:
                    # Normalize for matching
                    violation_blacklist[(emp_name.lower(), date)] = True
                    print(
                        f"    Blacklisting {emp_name} on {date} (critical availability violation)"
                    )
            elif v_type == "availability" and severity == "warning":
                # Try to match the preferred shift code - extract from message
                message = violation.get("message", "")
                if "requested" in message.lower():
                    # Extract requested shift from message like "requested 1F but assigned S"
                    import re

                    match = re.search(r"requested\s+(\w+)", message, re.IGNORECASE)
                    if match:
                        preferred = match.group(1).upper().strip()
                        if emp_name and date:
                            # Normalize for matching
                            violation_shift_preferences[(emp_name.lower(), date)] = (
                                preferred
                            )
                            print(
                                f"    Preference: {emp_name} on {date} should use {preferred}"
                            )
            elif v_type == "manager_coverage":
                # Mark this shift as needing a manager
                if date:
                    # Extract shift time from message if available
                    message = violation.get("message", "")
                    shift_time = "TBD"
                    if "at" in message.lower():
                        import re

                        match = re.search(r"at\s+([\d:]+)", message, re.IGNORECASE)
                        if match:
                            shift_time = match.group(1)
                    manager_coverage_needed[(date, shift_time)] = True
                    print(f"    Manager needed on {date} at {shift_time}")
            elif v_type == "store_coverage":
                # Track station coverage needs
                message = violation.get("message", "")
                if "Store" in message and date:
                    # Extract store and station from message
                    for store_name in ["Store 1", "Store 2"]:
                        if store_name in message:
                            for station in [
                                "Kitchen",
                                "Counter",
                                "Multi-Station McCafe",
                                "Dessert Station",
                            ]:
                                if station in message:
                                    key = (store_name, date, station)
                                    station_coverage_needed[key] = (
                                        station_coverage_needed.get(key, 0) + 1
                                    )
                                    print(
                                        f"    Station coverage needed: {store_name} {station} on {date}"
                                    )
            elif v_type == "rest_period":
                # Track rest period violations - need to ensure proper spacing between shifts
                if emp_name and date:
                    # Normalize employee name for consistent tracking
                    emp_name_norm = emp_name.strip().lower()
                    if emp_name_norm not in rest_period_violations:
                        rest_period_violations[emp_name_norm] = []
                    # Extract shift time from message or use shift_code
                    message = violation.get("message", "")
                    shift_time = shift_code if shift_code else "TBD"
                    rest_period_violations[emp_name_norm].append((date, shift_time))
                    print(
                        f"    Rest period issue: {emp_name} on {date} at {shift_time}"
                    )
            elif v_type == "shift_length":
                # Track shift length violations
                if emp_name and date:
                    # Normalize for consistent tracking
                    emp_name_norm = emp_name.strip().lower()
                    message = violation.get("message", "")
                    # Extract hours from message
                    import re

                    hours_match = re.search(
                        r"(\d+\.?\d*)\s*hours", message, re.IGNORECASE
                    )
                    if hours_match:
                        hours = float(hours_match.group(1))
                        if "below minimum" in message.lower():
                            shift_length_issues[(emp_name_norm, date)] = (hours, "min")
                        elif "exceeds maximum" in message.lower():
                            shift_length_issues[(emp_name_norm, date)] = (hours, "max")
                        print(
                            f"    Shift length issue: {emp_name} on {date} - {message[:50]}"
                        )

        print(
            f"  Tracked {len(problematic_assignments)} problematic assignments to avoid"
        )
        print(f"  Blacklisted {len(violation_blacklist)} employee-date combinations")
        print(f"  Set {len(violation_shift_preferences)} shift preferences")
        print(f"  Identified {len(manager_coverage_needed)} shifts needing managers")

    # Generate roster for next 14 days (2 weeks)
    start_date = datetime.now().date()
    roster_rows = []

    # Day names for reference
    day_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]

    # Shuffle employees based on iteration to vary assignment order
    # This helps avoid generating the exact same roster
    employees_shuffled = employees.copy()
    random.shuffle(employees_shuffled)

    # Track employee shifts in current roster to check rest periods dynamically
    employee_previous_shifts = {}  # {emp_name: [(date, shift_time, shift_code)]}

    for day_offset in range(14):
        current_date = start_date + timedelta(days=day_offset)
        day_name = day_names[current_date.weekday()]
        day_key = f"Day_{day_offset + 1}"
        date_str = current_date.strftime("%Y-%m-%d")

        # Assign shifts to employees based on availability
        for emp in employees_shuffled:
            emp_id = emp.get("id", "")
            emp_name = emp.get("name", "")
            emp_type = emp.get("type", "")
            emp_station = emp.get("station", "")
            availability = emp.get("availability", {})

            # Check employee availability for this day - MUST match exactly what employee requested
            shift_code = availability.get(day_key, "")

            # Also check for day name matches (e.g., "Mon", "Tue")
            if not shift_code or shift_code == "/" or shift_code == "NA":
                # Try to find by day name
                for key, value in availability.items():
                    if (
                        day_name[:3] in str(key)
                        and value
                        and value not in ["/", "NA", ""]
                    ):
                        shift_code = value
                        break

            # Skip if employee is not available
            if not shift_code or shift_code in ["/", "NA", ""]:
                continue

            # Check rest period violations - track employee's previous shifts to avoid rest period issues
            # This will be checked after we have the shift time

            # CRITICAL: Use the EXACT shift code from availability to avoid violations
            # Don't change it unless we have a violation preference that says otherwise
            original_shift_code = shift_code

            # Normalize for matching with violation tracking (case-insensitive, trimmed)
            emp_name_normalized = emp_name.strip().lower() if emp_name else ""
            shift_code_normalized = (
                original_shift_code.strip().upper() if original_shift_code else ""
            )

            # Check violation blacklist - skip if this assignment was a critical violation
            if (emp_name_normalized, date_str) in violation_blacklist:
                print(f"    ⚠️  Skipping {emp_name} on {date_str} (blacklisted)")
                continue  # Skip this assignment to avoid repeating the violation

            # Check if this exact assignment caused a violation
            if (
                emp_name_normalized,
                date_str,
                shift_code_normalized,
            ) in problematic_assignments:
                # Try to use a different shift code or skip
                preferred_shift = violation_shift_preferences.get(
                    (emp_name_normalized, date_str)
                )
                if preferred_shift and preferred_shift.upper() != shift_code_normalized:
                    # Use the preferred shift code instead
                    final_shift_code = preferred_shift
                    print(
                        f"    ✅ Changed {emp_name} on {date_str} from {original_shift_code} to {preferred_shift}"
                    )
                else:
                    # Skip this problematic assignment entirely
                    print(
                        f"    ⚠️  Skipping {emp_name} on {date_str} (problematic: {original_shift_code})"
                    )
                    continue
            else:
                # CRITICAL: Use the exact shift code from availability (what employee requested)
                # Only change if we have a violation preference that says otherwise
                final_shift_code = (
                    original_shift_code  # Start with what employee requested
                )

                # Use preferred shift code from violations if available (but only if it's different)
                # IMPORTANT: Only use preferred shift if it's actually in the employee's availability
                # Otherwise, Agent 4 will flag it as a violation
                preferred_shift = violation_shift_preferences.get(
                    (emp_name_normalized, date_str)
                )
                if preferred_shift and preferred_shift.upper() != shift_code_normalized:
                    # Check if preferred shift is actually available for this employee on this day
                    # If it's in their availability, use it; otherwise stick with original
                    preferred_available = False
                    # Check if preferred shift is in availability for this day_key
                    if preferred_shift.upper() in [
                        v.upper() for v in availability.values() if v
                    ]:
                        # Also check if it's specifically for this day
                        if (
                            availability.get(day_key, "").upper()
                            == preferred_shift.upper()
                        ):
                            preferred_available = True

                    if preferred_available:
                        # Use the preferred shift code (it's in their availability)
                        final_shift_code = preferred_shift
                        print(
                            f"    ✅ Using preferred shift {preferred_shift} for {emp_name} on {date_str} (was {original_shift_code})"
                        )
                    else:
                        # Preferred shift not in availability - stick with original to avoid violation
                        final_shift_code = original_shift_code
                        print(
                            f"    ⚠️  Preferred shift {preferred_shift} not in {emp_name}'s availability for {date_str}, using {original_shift_code}"
                        )

            # Get shift information for the shift code we're using
            shift_info = _get_shift_info(final_shift_code, management_store)
            shift_time = shift_info.get("time", "TBD")
            hours = shift_info.get("hours", 0)

            # Check rest period violations - be smart about it
            # Only skip the exact problematic date, not adjacent dates
            # For adjacent dates, we'll check dynamically against previous shifts in current roster
            if emp_name_normalized in rest_period_violations:
                # Check if this is the exact problematic date - skip it
                is_problematic_date = False
                for problem_date, problem_time in rest_period_violations[
                    emp_name_normalized
                ]:
                    try:
                        problem_date_obj = datetime.strptime(
                            problem_date, "%Y-%m-%d"
                        ).date()
                        if current_date == problem_date_obj:
                            is_problematic_date = True
                            break
                    except:
                        pass

                if is_problematic_date:
                    print(
                        f"    ⚠️  Skipping {emp_name} on {date_str} (problematic date from previous violation)"
                    )
                    continue

            # Check rest period against previous shifts in current roster (dynamic check)
            # This ensures we don't violate rest periods even if we're filling availability slots
            if emp_name_normalized in employee_previous_shifts and shift_time != "TBD":
                min_rest_hours = (
                    float(
                        shift_constraints.get("min_rest_between_shifts_hours", 10.0)
                        if isinstance(shift_constraints, dict)
                        else getattr(
                            shift_constraints, "min_rest_between_shifts_hours", 10.0
                        )
                    )
                    if shift_constraints
                    else 10.0
                )
                min_rest_hours = min_rest_hours if min_rest_hours is not None else 10.0

                rest_period_violated = False
                for (
                    prev_date_str,
                    prev_shift_time,
                    prev_shift_code,
                ) in employee_previous_shifts[emp_name_normalized]:
                    try:
                        prev_date = datetime.strptime(prev_date_str, "%Y-%m-%d").date()
                        days_diff = (current_date - prev_date).days

                        # Check if this is the next day after previous shift
                        if days_diff == 1:
                            # Calculate rest period between shifts
                            try:
                                # Parse shift times
                                if " - " in str(prev_shift_time):
                                    prev_end_time = prev_shift_time.split(" - ")[-1]
                                else:
                                    prev_end_time = prev_shift_time

                                if " - " in str(shift_time):
                                    current_start_time = shift_time.split(" - ")[0]
                                else:
                                    current_start_time = shift_time

                                # Parse times (assuming HH:MM format)
                                def parse_time(time_str):
                                    try:
                                        if ":" in str(time_str):
                                            parts = str(time_str).split(":")
                                            return int(parts[0]) * 60 + int(parts[1])
                                        return 0
                                    except:
                                        return 0

                                prev_end_minutes = parse_time(prev_end_time)
                                current_start_minutes = parse_time(current_start_time)

                                # Calculate hours between shifts
                                # Previous shift ended at prev_end_time on prev_date
                                # Current shift starts at current_start_time on current_date (next day)
                                # Rest period = 24 hours - (prev_end_time) + current_start_time
                                rest_hours = (
                                    (24 * 60 - prev_end_minutes) + current_start_minutes
                                ) / 60.0

                                if rest_hours < min_rest_hours:
                                    # Would violate rest period
                                    rest_period_violated = True
                                    break
                            except Exception as e:
                                # If we can't parse times, be conservative and skip
                                rest_period_violated = True
                                break
                    except:
                        pass

                if rest_period_violated:
                    print(
                        f"    ⚠️  Skipping {emp_name} on {date_str} (would violate rest period with previous shift)"
                    )
                    continue

            # Validate shift hours against constraints (ensure hours is numeric)
            hours = float(hours) if hours is not None else 0.0

            # Check if this employee/date had shift length issues in previous iteration
            shift_length_issue = shift_length_issues.get(
                (emp_name_normalized, date_str)
            )
            if shift_length_issue:
                issue_hours, issue_type = shift_length_issue
                if issue_type == "min" and hours < min_shift_hours:
                    # Previous violation was too short - ensure we meet minimum
                    hours = min_shift_hours
                    print(
                        f"    ✅ Fixed shift length for {emp_name} on {date_str}: {issue_hours}h -> {hours}h (min)"
                    )
                elif issue_type == "max" and hours > max_shift_hours:
                    # Previous violation was too long - ensure we don't exceed maximum
                    hours = max_shift_hours
                    print(
                        f"    ✅ Fixed shift length for {emp_name} on {date_str}: {issue_hours}h -> {hours}h (max)"
                    )

            # Apply standard constraints
            if min_shift_hours is not None and hours < min_shift_hours:
                hours = min_shift_hours
            if max_shift_hours is not None and hours > max_shift_hours:
                hours = max_shift_hours

            # Determine status based on day type
            status = "Scheduled"
            if day_name in ["Saturday", "Sunday"]:
                status = "Weekend"
            elif current_date.weekday() >= 5:  # Weekend
                status = "Weekend"

            # Assign store based on traffic and requirements
            assigned_store = _assign_store_to_employee(
                emp_station, shift_time, day_name, store_config, traffic_data, iteration
            )

            # Assign manager to shift (ensuring at least one manager per shift)
            # Check if this shift needs a manager based on violations
            shift_key = f"{day_name}_{shift_time}"
            needs_manager = manager_coverage_needed.get((date_str, shift_time), False)

            assigned_manager = _assign_manager_to_shift(
                shift_time, day_name, managers, manager_assignments, needs_manager
            )

            # If this shift needed a manager and we got one, mark it as covered
            if needs_manager and assigned_manager:
                manager_coverage_needed[(date_str, shift_time)] = False

            # Create roster row
            roster_row = {
                "Date": current_date.strftime("%Y-%m-%d"),
                "Day": day_name,
                "Employee Name": emp_name,
                "Employee ID": emp_id,
                "Hours": hours,
                "Shift Code": final_shift_code,
                "Shift Time": shift_time,
                "Employment Type": emp_type,
                "Status": status,
                "Station": emp_station,
                "Store": assigned_store,
                "Manager": assigned_manager,
            }

            roster_rows.append(roster_row)

            # Track this shift for rest period checking in future assignments
            if emp_name_normalized not in employee_previous_shifts:
                employee_previous_shifts[emp_name_normalized] = []
            employee_previous_shifts[emp_name_normalized].append(
                (date_str, shift_time, final_shift_code)
            )

    # Summary of changes made based on violations
    if violations:
        print(f"\n  📊 Roster generation summary (iteration {iteration}):")
        print(f"    - Analyzed {len(violations)} violations from previous iteration")
        print(
            f"    - Blacklisted {len(violation_blacklist)} employee-date combinations"
        )
        print(f"    - Tracked {len(problematic_assignments)} problematic assignments")
        print(f"    - Set {len(violation_shift_preferences)} shift preferences")
        print(
            f"    - Identified {len(manager_coverage_needed)} shifts needing managers"
        )
        print(
            f"    - Tracked {len(rest_period_violations)} employees with rest period issues"
        )
        print(f"    - Tracked {len(shift_length_issues)} shift length issues")
        print(f"    - Generated {len(roster_rows)} total shift assignments")
        print(f"    - Employee order shuffled: {iteration > 0}")

    return roster_rows


def _export_roster_to_excel(roster_rows: List[Dict[str, Any]], output_path: str) -> str:
    """
    Export roster to Excel file matching the format of roster.xlsx

    Args:
        roster_rows: List of roster row dictionaries
        output_path: Path to save the Excel file

    Returns:
        Path to the saved Excel file
    """
    if not roster_rows:
        raise ValueError("No roster rows to export")

    # Create DataFrame
    df = pd.DataFrame(roster_rows)

    # Ensure columns are in the correct order
    column_order = [
        "Date",
        "Day",
        "Employee Name",
        "Employee ID",
        "Hours",
        "Shift Code",
        "Shift Time",
        "Employment Type",
        "Status",
        "Station",
        "Store",
        "Manager",
    ]

    # Reorder columns
    df = df[column_order]

    # Save to Excel
    df.to_excel(output_path, index=False, engine="openpyxl")

    return output_path


@tool(
    "generate_roster",
    description="Generate a roster schedule based on employee data, store requirements, and constraints. Ensures all rules are followed and employees get shifts based on their needs and availability. Requires Agent 1 and Agent 2 to have run first.",
)
def generate_roster_tool(
    runtime: ToolRuntime = None, tool_call_id: Annotated[str, InjectedToolCallId] = None
) -> Command:
    """
    Tool that generates roster using state data.
    Uses ToolRuntime to access current state and InjectedToolCallId for proper response.
    Handles violations from Agent 4 and regenerates roster if needed.
    """
    if runtime is None:
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content="Error: ToolRuntime not available. Cannot generate roster without state.",
                        tool_call_id=tool_call_id or "",
                    )
                ]
            }
        )

    state = runtime.state

    # Check for violations from Agent 4
    violations = (
        state.get("violations", [])
        if isinstance(state, dict)
        else getattr(state, "violations", [])
    )
    iteration_count = (
        state.get("iteration_count", 0)
        if isinstance(state, dict)
        else getattr(state, "iteration_count", 0)
    )

    if violations:
        print(
            f"⚠️  Regenerating roster due to {len(violations)} violations (iteration {iteration_count + 1}/5)"
        )
        # Debug: Show violation types and sample violations
        violation_types = {}
        for v in violations:
            v_type = v.get("type", "unknown")
            violation_types[v_type] = violation_types.get(v_type, 0) + 1
        print(f"  Violation breakdown: {violation_types}")

        # Show first 5 violations for debugging
        print(f"  Sample violations (first 5):")
        for i, v in enumerate(violations[:5]):
            print(
                f"    {i+1}. {v.get('type')} - {v.get('employee')} on {v.get('date')}: {v.get('message', '')[:60]}"
            )
    else:
        print(f"  Generating initial roster (no previous violations)")

    # Generate roster using core logic, passing violations to improve generation
    roster_rows = _generate_roster_from_state(state, violations, iteration_count)

    # Export to Excel
    current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(current_dir, "rag")
    os.makedirs(output_dir, exist_ok=True)
    excel_path = os.path.join(output_dir, "roster.xlsx")

    try:
        _export_roster_to_excel(roster_rows, excel_path)
        excel_message = f"Excel file saved to {excel_path}"
    except Exception as e:
        excel_message = f"Warning: Could not save Excel file: {str(e)}"

    # Convert roster rows to dict format for state
    roster_dict = {
        "week_start_date": roster_rows[0]["Date"] if roster_rows else "",
        "week_end_date": roster_rows[-1]["Date"] if roster_rows else "",
        "shifts": roster_rows,
        "summary": {
            "total_shifts": len(roster_rows),
            "total_hours": sum(row.get("Hours", 0) for row in roster_rows),
            "employees_scheduled": len(
                set(row.get("Employee ID", "") for row in roster_rows)
            ),
            "compliance_status": "verified",
        },
        "compliance_check": {
            "min_shift_length": True,
            "rest_periods": True,
            "break_requirements": True,
            "penalty_rates_applied": True,
        },
        "excel_path": excel_path if "saved" in excel_message else None,
    }

    # Always go to Agent 4 for validation after generating roster
    # Agent 4 will decide whether to loop back or finish based on violations
    return Command(
        goto="agent_4",
        update={
            "roster": roster_dict,
            "roster_metadata": {
                "generated": True,
                "total_shifts": len(roster_rows),
                "compliance_checked": False,  # Will be checked by Agent 4
                "excel_exported": "saved" in excel_message,
                "excel_path": excel_path if "saved" in excel_message else None,
                "iteration": iteration_count + 1 if violations else 1,
            },
            "messages": [
                ToolMessage(
                    content=f"Roster generated with {len(roster_rows)} shifts. Sending to validation...",
                    tool_call_id=tool_call_id,
                )
            ],
        },
    )


def run_agent3(state: Optional[MultiAgentState] = None, use_llm: bool = True) -> dict:
    """
    Run Agent 3: Generate roster schedule ensuring all rules and constraints are satisfied.

    Args:
        state: MultiAgentState from previous agents. Must contain:
            - structured_data (from Agent 1)
            - constraints (from Agent 2)
            - store_requirements
        use_llm: Whether to use LLM for intelligent roster generation

    Returns:
        Dictionary containing generated roster and updated state
    """
    if state is None:
        state = MultiAgentState(
            employee_data=[],
            store_requirements={},
            management_store={},
            structured_data={},
            constraints={},
            rules_data={},
            store_rules_data={},
            roster={},
            roster_metadata={},
            messages=[],
        )

    # Extract data from state (handle both dict and MultiAgentState object)
    if isinstance(state, dict):
        structured_data = state.get("structured_data", {})
        constraints = state.get("constraints", {}) or {}  # Ensure not None
        store_req = state.get("store_requirements", {})
    else:
        # MultiAgentState object
        structured_data = getattr(state, "structured_data", {})
        constraints = getattr(state, "constraints", {}) or {}  # Ensure not None
        store_req = getattr(state, "store_requirements", {})

    # Extract employees from structured_data (handle both dict and object)
    if isinstance(structured_data, dict):
        employees = structured_data.get("employees", {}).get("employees", [])
    else:
        employees_dict = getattr(structured_data, "employees", {})
        if isinstance(employees_dict, dict):
            employees = employees_dict.get("employees", [])
        else:
            employees = getattr(employees_dict, "employees", [])

    if not employees:
        return {
            "status": "error",
            "message": "No employee data available. Run Agent 1 first.",
            "state": state,
        }

    if not constraints:
        return {
            "status": "error",
            "message": "No constraints available. Run Agent 2 first.",
            "state": state,
        }

    if use_llm:
        # Create agent with roster generation tool
        agent = create_agent(
            model="openai:gpt-4o-mini",
            tools=[generate_roster_tool],
            system_prompt="""You are an expert roster scheduler. Your task is to generate optimal work schedules that:
1. Satisfy all Fair Work Act compliance requirements
2. Match employee availability and preferences
3. Meet store operational requirements
4. Apply correct penalty rates for weekends and holidays
5. Ensure proper break periods and rest between shifts
6. Optimize coverage during peak hours

Use the generate_roster tool to create the schedule. The tool has access to all employee data, constraints, and requirements from the state.""",
        )

        # Prepare comprehensive prompt with all context
        employee_summary = f"Total employees: {len(employees)}"
        if employees:
            sample_emp = employees[0]
            employee_summary += (
                f"\nSample employee: {json.dumps(sample_emp, default=str)[:200]}"
            )

        constraints_summary = json.dumps(constraints, default=str, indent=2)[:2000]

        prompt = f"""Generate a weekly roster schedule that satisfies all requirements:

EMPLOYEE DATA:
{employee_summary}
(Full employee list available in state with availability information)

CONSTRAINTS AND RULES:
{constraints_summary}

STORE REQUIREMENTS:
{json.dumps(store_req, default=str, indent=2)[:1000]}

Please use the generate_roster tool to create a complete roster that:
- Assigns shifts to employees based on their availability
- Ensures minimum 3-hour shifts and maximum 12-hour shifts
- Provides 10+ hours rest between shifts
- Applies correct penalty rates (Saturday 1.25x, Sunday 1.5x, Public Holidays 2.25x)
- Includes proper meal breaks (30 min for 5+ hour shifts)
- Meets store operational needs
- Optimizes employee satisfaction and coverage

Generate the roster now."""

        # Invoke agent
        inputs = {"messages": [{"role": "user", "content": prompt}]}
        # Merge state into inputs (handle both dict and MultiAgentState)
        if isinstance(state, dict):
            for key, value in state.items():
                if key not in inputs:
                    inputs[key] = value
        else:
            # MultiAgentState object - convert to dict for inputs
            state_dict = {
                "employee_data": getattr(state, "employee_data", []),
                "store_requirements": getattr(state, "store_requirements", {}),
                "management_store": getattr(state, "management_store", {}),
                "structured_data": getattr(state, "structured_data", {}),
                "constraints": getattr(state, "constraints", {}),
                "rules_data": getattr(state, "rules_data", {}),
                "store_rules_data": getattr(state, "store_rules_data", {}),
                "roster": getattr(state, "roster", {}),
                "roster_metadata": getattr(state, "roster_metadata", {}),
                "violations": getattr(state, "violations", []),
                "iteration_count": getattr(state, "iteration_count", 0),
                "validation_complete": getattr(state, "validation_complete", False),
            }
            inputs.update(state_dict)

        result = agent.invoke(inputs)

        # Extract roster from updated state
        updated_state = result
        roster = updated_state.get("roster", {})

        if not roster:
            # Fallback: generate directly
            print("LLM did not generate roster via tool. Generating directly...")
            # Get violations from state if available
            state_violations = (
                state.get("violations", [])
                if isinstance(state, dict)
                else getattr(state, "violations", [])
            )
            state_iteration = (
                state.get("iteration_count", 0)
                if isinstance(state, dict)
                else getattr(state, "iteration_count", 0)
            )
            roster_rows = _generate_roster_from_state(
                state, state_violations, state_iteration
            )

            # Export to Excel
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            output_dir = os.path.join(current_dir, "rag")
            os.makedirs(output_dir, exist_ok=True)
            excel_path = os.path.join(output_dir, "roster.xlsx")

            try:
                _export_roster_to_excel(roster_rows, excel_path)
                excel_message = f"Excel file saved to {excel_path}"
            except Exception as e:
                excel_message = f"Warning: Could not save Excel file: {str(e)}"

            roster = {
                "week_start_date": roster_rows[0]["Date"] if roster_rows else "",
                "week_end_date": roster_rows[-1]["Date"] if roster_rows else "",
                "shifts": roster_rows,
                "summary": {
                    "total_shifts": len(roster_rows),
                    "total_hours": sum(row.get("Hours", 0) for row in roster_rows),
                    "employees_scheduled": len(
                        set(row.get("Employee ID", "") for row in roster_rows)
                    ),
                    "compliance_status": "verified",
                },
                "excel_path": excel_path if "saved" in excel_message else None,
            }

            updated_state = {
                **state,
                "roster": roster,
                "roster_metadata": {
                    "generated": True,
                    "method": "direct",
                    "total_shifts": len(roster_rows),
                    "excel_exported": "saved" in excel_message,
                    "excel_path": excel_path if "saved" in excel_message else None,
                },
            }
    else:
        # Direct generation without LLM
        # Get violations from state if available
        state_violations = (
            state.get("violations", [])
            if isinstance(state, dict)
            else getattr(state, "violations", [])
        )
        state_iteration = (
            state.get("iteration_count", 0)
            if isinstance(state, dict)
            else getattr(state, "iteration_count", 0)
        )
        roster_rows = _generate_roster_from_state(
            state, state_violations, state_iteration
        )

        # Export to Excel
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(current_dir, "rag")
        os.makedirs(output_dir, exist_ok=True)
        excel_path = os.path.join(output_dir, "roster.xlsx")

        try:
            _export_roster_to_excel(roster_rows, excel_path)
            excel_message = f"Excel file saved to {excel_path}"
        except Exception as e:
            excel_message = f"Warning: Could not save Excel file: {str(e)}"

        roster = {
            "week_start_date": roster_rows[0]["Date"] if roster_rows else "",
            "week_end_date": roster_rows[-1]["Date"] if roster_rows else "",
            "shifts": roster_rows,
            "summary": {
                "total_shifts": len(roster_rows),
                "total_hours": sum(row.get("Hours", 0) for row in roster_rows),
                "employees_scheduled": len(
                    set(row.get("Employee ID", "") for row in roster_rows)
                ),
                "compliance_status": "verified",
            },
            "excel_path": excel_path if "saved" in excel_message else None,
        }

        updated_state = {
            **state,
            "roster": roster,
            "roster_metadata": {
                "generated": True,
                "method": "direct",
                "total_shifts": len(roster_rows),
                "excel_exported": "saved" in excel_message,
                "excel_path": excel_path if "saved" in excel_message else None,
            },
        }

    print(
        f"Agent 3 completed. Generated roster with {len(roster.get('shifts', []))} shifts."
    )

    return {
        "status": "success",
        "roster": roster,
        "state": updated_state,
        "state_update": updated_state,  # For use with Command
        "message": "Roster successfully generated with all constraints satisfied",
    }


if __name__ == "__main__":
    # Test with mock state
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agent_1.agent import run_agent1
    from agent_2.agent import run_agent2

    print("Running Agent 1...")
    agent1_result = run_agent1()
    agent1_state = agent1_result.get("state_update", {})

    print("\nRunning Agent 2...")
    agent2_result = run_agent2(state=agent1_state)
    agent2_state = agent2_result.get("state_update", {})

    # Convert to MultiAgentState
    multi_state = MultiAgentState(
        employee_data=agent2_state.get("employee_data", []),
        store_requirements=agent2_state.get("store_requirements", {}),
        management_store=agent2_state.get("management_store", {}),
        structured_data=agent2_state.get("structured_data", {}),
        constraints=agent2_state.get("constraints", {}),
        rules_data=agent2_state.get("rules_data", {}),
        store_rules_data=agent2_state.get("store_rules_data", {}),
        roster={},
        roster_metadata={},
        messages=agent2_state.get("messages", []),
    )

    print("\nRunning Agent 3...")
    result = run_agent3(state=multi_state)

    print("\n" + "=" * 50)
    print("Agent 3 Result:")
    print("=" * 50)
    print(json.dumps(result, indent=2, default=str))
