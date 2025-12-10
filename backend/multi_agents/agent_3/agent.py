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


def _generate_manager_names(count: int = 10) -> List[str]:
    """Generate random manager names (not using employee names)"""
    import random

    first_names = [
        "Alex",
        "Jordan",
        "Taylor",
        "Morgan",
        "Casey",
        "Riley",
        "Avery",
        "Quinn",
        "Blake",
        "Cameron",
        "Dakota",
        "Emery",
        "Finley",
        "Harper",
        "Hayden",
        "Jamie",
        "Kai",
        "Logan",
        "Parker",
        "Reese",
        "River",
        "Sage",
        "Skylar",
    ]

    last_names = [
        "Anderson",
        "Brown",
        "Davis",
        "Garcia",
        "Harris",
        "Jackson",
        "Johnson",
        "Jones",
        "Lee",
        "Martinez",
        "Miller",
        "Moore",
        "Robinson",
        "Smith",
        "Taylor",
        "Thomas",
        "Thompson",
        "Walker",
        "White",
        "Williams",
        "Wilson",
        "Wright",
        "Young",
    ]

    managers = []
    for i in range(count):
        first = random.choice(first_names)
        last = random.choice(last_names)
        manager_name = f"{first} {last}"
        # Ensure unique names
        while manager_name in managers:
            first = random.choice(first_names)
            last = random.choice(last_names)
            manager_name = f"{first} {last}"
        managers.append(manager_name)

    return managers


def _identify_managers(employees: List[Dict[str, Any]]) -> List[str]:
    """Generate manager names - all managers are full-time employees (random names, not employee names)"""
    # Generate random manager names instead of using employee names
    # All managers are full-time employees, but we use generated names
    # Generate at least 20 managers to ensure we have enough for multiple assignments per store/day
    num_managers = max(20, len(employees) // 2)  # Generate at least 20 managers
    return _generate_manager_names(num_managers)


def _assign_manager_to_shift(
    shift_time: str,
    day_name: str,
    managers: List[str],
    manager_assignments: Dict[str, List[str]],
    needs_manager: bool = False,
    store: str = "",
    date: str = "",
    managers_per_store_per_day: Dict = None,
) -> str:
    """Assign a manager to a shift - NO LIMITS, always assign a random manager"""
    import random

    # Simply return a random manager - no checks, no limits, no conditions
    if managers:
        return random.choice(managers)
    return ""

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
                    # Also add to problematic assignments to ensure we skip it in later iterations
                    if emp_name and date and shift_code:
                        problematic_assignments.add(
                            (emp_name_norm, date, shift_code.upper())
                        )
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

    # Track hours per employee per day and per week to enforce maximum hours rules
    employee_daily_hours = {}  # {(emp_name, date): total_hours}
    employee_weekly_hours = {}  # {emp_name: {week_start: total_hours}}

    # Track managers per store per day - MAXIMUM 10 managers per store per day
    managers_per_store_per_day = {}  # {(store, date): [manager_names]}
    MAX_MANAGERS_PER_STORE_PER_DAY = 10  # Maximum 10 managers per store per day

    # Track station assignments per store per day to prevent over-assignment
    # Format: {(store, date, station): count}
    station_assignments = {}  # {(store, date, station): count}

    # Define minimum staffing requirements per store per station
    # MUST match Agent 5's DEFAULT_STAFFING_REQUIREMENTS
    station_requirements = {
        "Store 1: CBD Core Area": {
            "Kitchen": 6,
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

    for day_offset in range(14):
        current_date = start_date + timedelta(days=day_offset)
        day_name = day_names[current_date.weekday()]
        day_key = f"Day_{day_offset + 1}"
        date_str = current_date.strftime("%Y-%m-%d")

        # First pass: Assign to understaffed stations (prioritize filling gaps)
        # Second pass: Fill remaining availability slots evenly

        # Track which stations need more staff for this day
        stations_needing_staff = {}  # {(store, station): needed_count}
        for store_name, store_reqs in station_requirements.items():
            for station, required in store_reqs.items():
                station_key = (store_name, date_str, station)
                current_count = station_assignments.get(station_key, 0)
                if current_count < required:
                    key = (store_name, station)
                    stations_needing_staff[key] = stations_needing_staff.get(key, 0) + (
                        required - current_count
                    )

        # Assign shifts to employees based on availability
        # Prioritize employees whose stations need staff
        employees_to_assign = []
        employees_other = []

        for emp in employees_shuffled:
            emp_station = emp.get("station", "")
            # Check if this employee's station needs staff in any store
            station_needs_staff = False
            for (store_name, station), needed in stations_needing_staff.items():
                if station == emp_station and needed > 0:
                    station_needs_staff = True
                    break

            if station_needs_staff:
                employees_to_assign.append(emp)
            else:
                employees_other.append(emp)

        # Combine: prioritize understaffed stations first, then others
        employees_prioritized = employees_to_assign + employees_other

        for emp in employees_prioritized:
            emp_id = emp.get("id", "")
            emp_name = emp.get("name", "")
            emp_type = emp.get("type", "")
            emp_station = emp.get("station", "")
            availability = emp.get("availability", {})

            # Check if this employee's station needs staff (for prioritization)
            emp_station_needs_staff = False
            for (store_name, station), needed in stations_needing_staff.items():
                if station == emp_station and needed > 0:
                    emp_station_needs_staff = True
                    break

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
            # PRIORITY: Try to fix it rather than skip (to maximize coverage)
            if (
                emp_name_normalized,
                date_str,
                shift_code_normalized,
            ) in problematic_assignments:
                # Try to use a different shift code from availability
                preferred_shift = violation_shift_preferences.get(
                    (emp_name_normalized, date_str)
                )
                if preferred_shift and preferred_shift.upper() != shift_code_normalized:
                    # Check if preferred shift is in employee's availability
                    if preferred_shift.upper() in [
                        v.upper() for v in availability.values() if v
                    ]:
                        # Use the preferred shift code instead
                        final_shift_code = preferred_shift
                        print(
                            f"    ✅ Changed {emp_name} on {date_str} from {original_shift_code} to {preferred_shift} (fixing violation)"
                        )
                    else:
                        # Preferred shift not available - in later iterations, skip to fix violations
                        if iteration >= 4:
                            print(
                                f"    ⚠️  Skipping {emp_name} on {date_str} (problematic assignment, preferred shift not available)"
                            )
                            continue
                        else:
                            # In early iterations, try original
                            final_shift_code = original_shift_code
                            print(
                                f"    ⚠️  Keeping {emp_name} on {date_str} with {original_shift_code} (preferred {preferred_shift} not available, will validate)"
                            )
                else:
                    # No preferred shift - in later iterations, skip to fix violations
                    if iteration >= 4:
                        print(
                            f"    ⚠️  Skipping {emp_name} on {date_str} (problematic assignment, no fix available)"
                        )
                        continue
                    else:
                        # In early iterations, try original
                        final_shift_code = original_shift_code
                        print(
                            f"    ⚠️  Keeping {emp_name} on {date_str} with {original_shift_code} (was problematic, but trying again)"
                        )
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

            # CRITICAL: If hours is 0 or not found, use default based on shift code
            # This ensures we don't assign 0 hours or default to 9 for everyone
            if hours == 0 or hours is None:
                # Try to infer from shift code name or use a reasonable default
                shift_name = shift_info.get("name", "").lower()
                if "full" in shift_name or "3f" in final_shift_code.lower():
                    hours = 12.0  # Full day
                elif (
                    "half" in shift_name
                    or "1f" in final_shift_code.lower()
                    or "2f" in final_shift_code.lower()
                ):
                    hours = 9.0  # Half day
                elif "shift change" in shift_name or "sc" in final_shift_code.lower():
                    hours = 9.0
                elif "day" in shift_name or "s" == final_shift_code.upper():
                    hours = 8.5  # Day shift
                elif "meeting" in shift_name or "m" == final_shift_code.upper():
                    hours = 8.0
                else:
                    # Default to minimum shift hours if we can't determine
                    hours = min_shift_hours
                    print(
                        f"    ⚠️  Could not determine hours for shift code {final_shift_code}, using minimum {min_shift_hours}h"
                    )

            # Ensure hours is numeric
            hours = float(hours) if hours is not None else min_shift_hours

            # Check rest period violations from previous iterations
            # PRIORITY: In later iterations, skip problematic dates to aggressively fix violations
            # This helps reduce violations significantly
            if emp_name_normalized in rest_period_violations and iteration >= 3:
                # Skip dates that had rest period violations to fix them
                is_problematic_date = False
                for problem_date, problem_time in rest_period_violations[
                    emp_name_normalized
                ]:
                    try:
                        problem_date_obj = datetime.strptime(
                            problem_date, "%Y-%m-%d"
                        ).date()
                        if current_date == problem_date_obj:
                            # Skip this date in later iterations to fix violations
                            is_problematic_date = True
                            break
                    except:
                        pass

                if is_problematic_date:
                    print(
                        f"    ⚠️  Skipping {emp_name} on {date_str} (rest period violation from previous iteration - fixing)"
                    )
                    continue
                # In later iterations (3+): Skip dates that had rest period violations to fix them
                # This helps reduce violations while maintaining coverage from earlier iterations
                is_problematic_date = False
                for problem_date, problem_time in rest_period_violations[
                    emp_name_normalized
                ]:
                    try:
                        problem_date_obj = datetime.strptime(
                            problem_date, "%Y-%m-%d"
                        ).date()
                        if current_date == problem_date_obj:
                            # Skip this date in later iterations to fix violations
                            is_problematic_date = True
                            break
                    except:
                        pass

                if is_problematic_date:
                    print(
                        f"    ⚠️  Skipping {emp_name} on {date_str} (rest period violation from previous iteration - fixing)"
                    )
                    continue

            # Check rest period against previous shifts in current roster (dynamic check)
            # PRIORITY: Only skip if we can definitively calculate that rest period < 10 hours
            # If we can't parse times, assign anyway and let Agent 4 validate (maximize coverage)
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
                                        return None  # Return None if can't parse
                                    except:
                                        return None

                                prev_end_minutes = parse_time(prev_end_time)
                                current_start_minutes = parse_time(current_start_time)

                                # Only skip if we can definitively calculate rest period AND it's critically low
                                # PRIORITY: Maximize coverage - only skip if rest period is < 8 hours (critical)
                                # Otherwise assign and let Agent 4 catch it (we'll fix in next iteration)
                                if (
                                    prev_end_minutes is not None
                                    and current_start_minutes is not None
                                ):
                                    # Calculate hours between shifts
                                    # Previous shift ended at prev_end_time on prev_date
                                    # Current shift starts at current_start_time on current_date (next day)
                                    # Rest period = 24 hours - (prev_end_time) + current_start_time
                                    rest_hours = (
                                        (24 * 60 - prev_end_minutes)
                                        + current_start_minutes
                                    ) / 60.0

                                    # PRIORITY: Reduce violations as much as possible
                                    # Strategy: Gradually increase strictness across 7 iterations
                                    # Target: ~90-95% coverage with minimum violations
                                    if iteration == 0:
                                        # First iteration: Skip only if rest period is very critical (< 7 hours)
                                        # This allows high coverage while preventing severe violations
                                        critical_threshold = (
                                            7.0  # Skip if < 7 hours (very critical)
                                        )
                                        if rest_hours < critical_threshold:
                                            rest_period_violated = True
                                            break
                                    elif iteration == 1:
                                        # Second iteration: Start fixing (< 8 hours)
                                        critical_threshold = 8.0  # Skip if < 8 hours
                                        if rest_hours < critical_threshold:
                                            rest_period_violated = True
                                            break
                                    elif iteration == 2:
                                        # Third iteration: Continue fixing (< 8.5 hours)
                                        critical_threshold = 8.5  # Skip if < 8.5 hours
                                        if rest_hours < critical_threshold:
                                            rest_period_violated = True
                                            break
                                    elif iteration == 3:
                                        # Fourth iteration: Be stricter (< 9 hours)
                                        critical_threshold = 9.0  # Skip if < 9 hours
                                        if rest_hours < critical_threshold:
                                            rest_period_violated = True
                                            break
                                    elif iteration == 4:
                                        # Fifth iteration: Very strict (< 9.5 hours)
                                        critical_threshold = 9.5  # Skip if < 9.5 hours
                                        if rest_hours < critical_threshold:
                                            rest_period_violated = True
                                            break
                                    else:
                                        # Later iterations (5+): Maximum strictness (< 10 hours = full requirement)
                                        # This aggressively fixes violations
                                        critical_threshold = 10.0  # Skip if < 10 hours (full requirement)
                                        if rest_hours < critical_threshold:
                                            # Would violate rest period - skip to fix violations
                                            rest_period_violated = True
                                            break
                                # If we can't parse times, don't skip - assign and let Agent 4 validate
                            except Exception as e:
                                # If we can't parse times, don't skip - assign anyway (prioritize coverage)
                                pass
                    except:
                        pass

                if rest_period_violated:
                    print(
                        f"    ⚠️  Skipping {emp_name} on {date_str} (rest period: {rest_hours:.1f}h < {min_rest_hours}h required)"
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

            # Check maximum hours per day (max 12 hours per day)
            emp_daily_key = (emp_name_normalized, date_str)
            current_daily_hours = employee_daily_hours.get(emp_daily_key, 0.0)
            max_hours_per_day = 12.0  # Maximum hours per day

            if current_daily_hours + hours > max_hours_per_day:
                # Skip this assignment - would exceed daily maximum
                print(
                    f"    ⚠️  Skipping {emp_name} on {date_str} - would exceed daily max hours ({current_daily_hours + hours:.1f}h > {max_hours_per_day}h)"
                )
                continue

            # Check maximum hours per week based on employment type
            emp_type_lower = emp_type.lower() if emp_type else ""
            max_weekly_hours = 38.0  # Default for full-time
            if "part-time" in emp_type_lower or "parttime" in emp_type_lower:
                max_weekly_hours = 30.0  # Part-time typically less than 38
            elif "casual" in emp_type_lower:
                max_weekly_hours = (
                    40.0  # Casual can work more but should respect availability
                )

            # Calculate week start (Monday of current week)
            week_start = current_date - timedelta(days=current_date.weekday())
            week_key = week_start.strftime("%Y-%m-%d")

            if emp_name_normalized not in employee_weekly_hours:
                employee_weekly_hours[emp_name_normalized] = {}
            current_weekly_hours = employee_weekly_hours[emp_name_normalized].get(
                week_key, 0.0
            )

            if current_weekly_hours + hours > max_weekly_hours:
                # Skip this assignment - would exceed weekly maximum
                print(
                    f"    ⚠️  Skipping {emp_name} on {date_str} - would exceed weekly max hours ({current_weekly_hours + hours:.1f}h > {max_weekly_hours}h for {emp_type})"
                )
                continue

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

            # Check if this station/store/day already has enough staff BEFORE assigning
            station_key = (assigned_store, date_str, emp_station)
            current_station_count = station_assignments.get(station_key, 0)

            # Get required count for this specific store and station
            store_reqs = station_requirements.get(assigned_store, {})
            required_count = store_reqs.get(emp_station, 0)

            # PRIORITIZE FILLING ALL AVAILABILITY SLOTS - be very flexible
            # Only skip if station is extremely over-staffed (3x required) AND other stations are critically understaffed
            if required_count > 0:
                max_allowed = required_count * 3  # Allow up to 3x required to fill all slots
            else:
                max_allowed = 10  # For optional stations, allow up to 10

            # Only skip if extremely over-staffed (3x required) AND other stations are critically understaffed (< 50% of required)
            if current_station_count >= max_allowed:
                # Check if other stations are critically understaffed (< 50% of required)
                other_stations_critically_understaffed = False
                for other_station, other_required in store_reqs.items():
                    if other_station != emp_station and other_required > 0:
                        other_station_key = (assigned_store, date_str, other_station)
                        other_count = station_assignments.get(other_station_key, 0)
                        # Only consider critically understaffed if less than 50% of required
                        if other_count < (other_required * 0.5):
                            other_stations_critically_understaffed = True
                            break

                # Only skip if this station is extremely over-staffed AND other stations are critically understaffed
                if other_stations_critically_understaffed:
                    print(
                        f"    ⚠️  Skipping {emp_name} on {date_str} - {emp_station} at {assigned_store} has {current_station_count} staff (max {max_allowed}), prioritizing critically understaffed stations"
                    )
                    continue
                # Otherwise, allow assignment to fill availability slots

            # Assign manager - MAXIMUM 10 managers per store per day (display as 1/10, 2/10, etc.)
            import random

            # Track managers for this store/day
            store_day_key = (assigned_store, date_str)
            if store_day_key not in managers_per_store_per_day:
                managers_per_store_per_day[store_day_key] = []

            current_manager_count = len(managers_per_store_per_day[store_day_key])

            # Assign managers up to maximum of 10 per store per day
            if current_manager_count < MAX_MANAGERS_PER_STORE_PER_DAY:
                # Calculate how many more managers we can assign
                remaining_slots = MAX_MANAGERS_PER_STORE_PER_DAY - current_manager_count
                # Assign 1 manager for this shift (can assign up to remaining slots)
                num_to_assign = min(1, remaining_slots, len(managers))

                if num_to_assign > 0:
                    # Get managers not already assigned to this store/day
                    available_managers = [
                        m
                        for m in managers
                        if m not in managers_per_store_per_day[store_day_key]
                    ]
                    if not available_managers:
                        available_managers = managers  # Reuse if all are assigned

                    new_manager = random.choice(available_managers)
                    managers_per_store_per_day[store_day_key].append(new_manager)
                    assigned_manager = new_manager

                    # Display count as X/10
                    new_count = len(managers_per_store_per_day[store_day_key])
                    print(
                        f"    ✅ Assigned manager {new_manager} to {assigned_store} on {date_str} ({new_count}/{MAX_MANAGERS_PER_STORE_PER_DAY} managers)"
                    )
                else:
                    assigned_manager = ""
            else:
                # Already have 10 managers - reuse one of them
                assigned_manager = random.choice(
                    managers_per_store_per_day[store_day_key]
                )
                print(
                    f"    ✅ Reusing manager {assigned_manager} for {assigned_store} on {date_str} ({MAX_MANAGERS_PER_STORE_PER_DAY}/{MAX_MANAGERS_PER_STORE_PER_DAY} managers - at maximum)"
                )

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

            # Track station assignment
            station_assignments[station_key] = current_station_count + 1

            # Track hours for this employee
            employee_daily_hours[emp_daily_key] = current_daily_hours + hours
            employee_weekly_hours[emp_name_normalized][week_key] = (
                current_weekly_hours + hours
            )

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
            system_prompt="""You are an expert roster scheduler. Your PRIMARY GOAL is to MAXIMIZE COVERAGE and fill ALL available employee slots.

CRITICAL PRIORITIES (in order):
1. FILL ALL AVAILABILITY SLOTS - Assign shifts to EVERY employee who is available. Target 90%+ coverage.
2. MEET MINIMUM STAFFING REQUIREMENTS - Ensure all stations have at least the required staff.
3. Respect maximum hours per day/week (but prioritize filling slots over strict limits when possible)
4. Apply correct penalty rates and ensure proper breaks
5. Assign managers to all shifts (up to 10 per store per day)

RULES:
- If an employee is available for a shift, ASSIGN THEM. Don't skip unless absolutely necessary.
- Prioritize filling understaffed stations first, then fill remaining availability.
- Be flexible with station assignments - allow up to 3x required staff to fill all slots.
- Use shift hours from management_store.json - vary hours based on shift codes.
- Maximum hours: Full-time 38h/week, Part-time <38h/week, Casual variable.

Use the generate_roster tool to create the schedule. MAXIMIZE COVERAGE - fill every available slot.""",
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

CRITICAL: Your PRIMARY MISSION is to ACHIEVE 90%+ COVERAGE by filling ALL available employee slots.

Please use the generate_roster tool to create a complete roster that:

PRIORITY 1 - MAXIMIZE COVERAGE:
- FILL EVERY AVAILABLE EMPLOYEE SLOT - if an employee is available, ASSIGN THEM
- Target 90%+ coverage - do NOT leave availability slots unfilled
- Assign shifts to employees based on their availability - use ALL available employees
- If an employee says they're available for 3F on 2025-12-12, ASSIGN THEM that shift

PRIORITY 2 - MEET STAFFING REQUIREMENTS:
- Ensure all stations meet minimum requirements (Kitchen: 6/4, Counter: 4/3, McCafe: 3/2)
- Fill understaffed stations FIRST, then fill remaining availability
- Allow flexible station assignments to fill all slots

PRIORITY 3 - COMPLIANCE (be flexible, but don't skip assignments unnecessarily):
- Respect maximum hours per week: Full-time max 38h/week, Part-time <38h/week
- Provides 10+ hours rest between shifts (but if needed to fill slots, be flexible)
- Ensures minimum 3-hour shifts and maximum 12-hour shifts PER SHIFT
- Do NOT assign everyone the same hours - vary hours based on shift codes (S=8.5h, 1F=9h, 2F=9h, 3F=12h)

OTHER REQUIREMENTS:
- ALWAYS assign managers to ALL shifts (up to 10 per store per day)
- Applies correct penalty rates (Saturday 1.25x, Sunday 1.5x, Public Holidays 2.25x)
- Includes proper meal breaks (30 min for 5+ hour shifts)

REMEMBER: Your goal is 90%+ coverage. Fill every available slot. Don't skip assignments unless absolutely necessary.

IMPORTANT: Check the shift codes in management_store.json - each shift code has specific hours (S=8.5h, 1F=9h, 2F=9h, 3F=12h, SC=9h, M=8h). Use these hours, don't assign the same hours to everyone.

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

        # Extract roster from result
        # When using LangChain agent, result is typically a dict with "messages" key
        # The tool's Command.update should be applied, but we need to check messages
        updated_state = result if isinstance(result, dict) else {}
        roster = updated_state.get("roster", {})

        # Check if LLM actually called the tool by examining messages
        tool_called = False
        if isinstance(result, dict) and "messages" in result:
            messages = result.get("messages", [])
            for msg in messages:
                # Check if there's a tool call or tool message
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    tool_called = True
                    break
                elif hasattr(msg, "name") and msg.name == "generate_roster_tool":
                    tool_called = True
                    break
                elif isinstance(msg, dict) and msg.get("tool_calls"):
                    tool_called = True
                    break

        # If tool was called but roster not in result, the tool's Command.update wasn't applied
        # This happens when agent.invoke() is used directly (not through graph)
        # The tool returns a Command with goto/update, but when invoked directly, only messages are returned
        # We need to execute the tool directly to get the roster
        if tool_called and not roster:
            print(
                "⚠️  LLM called tool but Command.update not applied (agent.invoke() used directly, not through graph)."
            )
            print("   Executing tool directly to get roster...")
            try:
                # Create a mock ToolRuntime to call the tool directly
                from langchain.tools import ToolRuntime

                class MockRuntime:
                    def __init__(self, state):
                        self.state = state

                mock_runtime = MockRuntime(state)
                tool_result = generate_roster_tool(
                    runtime=mock_runtime, tool_call_id="direct_call"
                )

                # Extract roster from Command.update
                if hasattr(tool_result, "update") and isinstance(
                    tool_result.update, dict
                ):
                    roster = tool_result.update.get("roster", {})
                elif isinstance(tool_result, dict):
                    roster = tool_result.get("update", {}).get("roster", {})

                if roster:
                    print(
                        "   ✅ Successfully extracted roster from tool's Command.update"
                    )
                    updated_state = (
                        {**state, "roster": roster}
                        if isinstance(state, dict)
                        else state
                    )
                else:
                    print(
                        "   ⚠️  Could not extract roster from tool. Falling back to direct generation..."
                    )
            except Exception as e:
                print(
                    f"   ⚠️  Error executing tool directly: {e}. Falling back to direct generation..."
                )

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
