"""
Main entry point to run the complete multi-agent roster generation pipeline.
This script runs Agent 1, Agent 2, Agent 3 (generator), Agent 4 (validator), and Agent 5 (final check) in sequence.
Agent 3 and Agent 4 loop until roster is valid or max 5 iterations reached.
Agent 5 performs final comprehensive checks and generates report.
"""

import os
import sys

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from agent_1.agent import run_agent1
from agent_2.agent import run_agent2
from agent_3.agent import run_agent3
from agent_4.agent import run_agent4
from agent_5.agent import run_agent5
from shared_state import MultiAgentState


def _update_state(state, key, value):
    """Helper function to update state (handles both dict and MultiAgentState object)"""
    if isinstance(state, dict):
        state[key] = value
    else:
        setattr(state, key, value)


def _get_state_value(state, key, default=None):
    """Helper function to get state value (handles both dict and MultiAgentState object)"""
    if isinstance(state, dict):
        return state.get(key, default)
    else:
        return getattr(state, key, default)


def main():
    """
    Run the complete pipeline:
    1. Agent 1: Parse and structure employee/store data
    2. Agent 2: Analyze constraints and rules
    3. Agent 3: Generate roster and export to Excel
    4. Agent 4: Validate roster
    5. Loop Agent 3-4 until no violations or max 5 iterations
    6. Agent 5: Final comprehensive check and report generation
    """
    print("=" * 60)
    print("ROSTER GENERATION & VALIDATION PIPELINE")
    print("=" * 60)

    # Step 1: Run Agent 1
    print("\n[Step 1/5] Running Agent 1: Data Parser...")
    print("-" * 60)
    result1 = run_agent1()
    state1 = result1.get("state_update", {})
    employee_count = result1.get("employee_count", 0)
    print(f"✅ Agent 1 completed: Processed {employee_count} employees")

    if employee_count == 0:
        print("❌ Error: No employees found. Cannot continue.")
        return

    # Step 2: Run Agent 2
    print("\n[Step 2/5] Running Agent 2: Constraints Analyzer...")
    print("-" * 60)
    result2 = run_agent2(state=state1)
    state2 = result2.get("state_update", {})
    constraints = result2.get("constraints", {})
    compliance_count = len(constraints.get("compliance_requirements", []))
    print(f"✅ Agent 2 completed: Extracted {compliance_count} compliance requirements")

    if compliance_count == 0:
        print("⚠️  Warning: No constraints found. Roster may not comply with rules.")

    # Step 3 & 4: Run Agent 3-4 loop
    print("\n[Step 3-4/5] Running Agent 3-4 Loop: Generate & Validate...")
    print("-" * 60)

    # Convert to MultiAgentState
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
        violations=[],
        iteration_count=0,
        validation_complete=False,
        final_check_report={},
        final_check_complete=False,
        messages=state2.get("messages", []),
    )

    # Run Agent 3-4 loop (max 5 iterations)
    max_iterations = 5
    iteration = 0
    accumulated_violations = (
        []
    )  # Track all violations across iterations to prevent reintroducing them

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration}/{max_iterations} ---")

        # Generate roster - pass accumulated violations so Agent 3 learns from ALL previous iterations
        print(f"  Generating roster (iteration {iteration})...")
        # Temporarily update state with accumulated violations so Agent 3 can use them
        _update_state(multi_state, "violations", accumulated_violations)
        result3 = run_agent3(state=multi_state, use_llm=False)
        updated_state = result3.get("state", {})
        roster_data = result3.get("roster", {})

        # Update state with roster
        roster_to_set = (
            roster_data
            if roster_data
            else (
                updated_state.get("roster", {})
                if isinstance(updated_state, dict)
                else getattr(updated_state, "roster", {})
            )
        )
        _update_state(multi_state, "roster", roster_to_set)

        # Validate roster
        print(f"  Validating roster (iteration {iteration})...")
        result4 = run_agent4(state=multi_state)
        new_violations = result4.get("violations", [])
        violation_count = result4.get("violation_count", 0)
        critical_count = result4.get("critical_count", 0)

        # Accumulate violations: add new violations to the list (avoid duplicates)
        # Use a set to track unique violations by (employee, date, type, shift_code)
        violation_keys = set()
        for v in accumulated_violations:
            key = (
                str(v.get("employee", "")).lower().strip(),
                str(v.get("date", "")).strip(),
                str(v.get("type", "")).strip(),
                str(v.get("shift_code", "")).upper().strip(),
            )
            violation_keys.add(key)

        # Add new violations that aren't already tracked
        for v in new_violations:
            key = (
                str(v.get("employee", "")).lower().strip(),
                str(v.get("date", "")).strip(),
                str(v.get("type", "")).strip(),
                str(v.get("shift_code", "")).upper().strip(),
            )
            if key not in violation_keys:
                accumulated_violations.append(v)
                violation_keys.add(key)

        # Update state with current iteration's violations (for reporting)
        _update_state(multi_state, "violations", new_violations)
        _update_state(multi_state, "iteration_count", iteration)
        _update_state(
            multi_state, "validation_complete", result4.get("is_compliant", False)
        )

        print(
            f"  ✅ Validation complete: {violation_count} violations ({critical_count} critical)"
        )

        # If no violations, break the loop
        if violation_count == 0:
            print(f"  ✅ No violations found! Roster is compliant.")
            break

        # If violations found and not last iteration, continue loop
        if iteration < max_iterations:
            print(f"  ⚠️  Regenerating roster to fix violations...")
        else:
            print(
                f"  ⚠️  Max iterations reached. Stopping with {violation_count} violations."
            )

    # Final results
    roster = _get_state_value(multi_state, "roster", {})
    final_violations = _get_state_value(multi_state, "violations", [])

    shifts = (
        roster.get("shifts", [])
        if isinstance(roster, dict)
        else getattr(roster, "shifts", [])
    )
    excel_path = (
        roster.get("excel_path")
        if isinstance(roster, dict)
        else getattr(roster, "excel_path", None)
    )

    print(f"\n✅ Agent 3-4 loop completed after {iteration} iteration(s)")
    print(f"   Generated {len(shifts)} shift assignments")
    print(f"   Found {len(final_violations)} violations")

    if excel_path and os.path.exists(excel_path):
        print(f"✅ Excel file created: {excel_path}")
        print(f"   - Total shifts: {len(shifts)}")
        print(f"   - Total hours: {roster.get('summary', {}).get('total_hours', 0)}")
        print(
            f"   - Employees scheduled: {roster.get('summary', {}).get('employees_scheduled', 0)}"
        )
    else:
        print("❌ Error: Excel file was not created")
        return

    # Summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED")
    print("=" * 60)
    print(f"📊 Employees processed: {employee_count}")
    print(f"📋 Compliance rules: {compliance_count}")
    print(f"📅 Shifts generated: {len(shifts)}")
    print(f"🔄 Iterations: {iteration}/{max_iterations}")
    print(f"⚠️  Violations: {len(final_violations)}")
    print(f"📁 Output file: {excel_path}")
    if len(final_violations) == 0:
        print("✅ Roster is fully compliant!")
    else:
        print("⚠️  Roster has violations (see details above)")

    # Step 5: Run Agent 5 - Final Check
    print("\n[Step 5/5] Running Agent 5: Final Comprehensive Check...")
    print("-" * 60)
    result5 = run_agent5(state=multi_state)

    final_check_status = result5.get("roster_status", "unknown")
    coverage_percent = result5.get("availability_coverage_percent", 0)
    filled_slots = result5.get("filled_slots", 0)
    total_slots = result5.get("total_slots", 0)
    report_path = result5.get("report_path")

    print(f"✅ Agent 5 completed: Final check status - {final_check_status.upper()}")
    print(
        f"   Availability Coverage: {coverage_percent}% ({filled_slots}/{total_slots} slots filled)"
    )

    if report_path and os.path.exists(report_path):
        print(f"✅ Final check report saved: {report_path}")
    else:
        print("⚠️  Warning: Final check report was not saved")

    # Final summary
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED WITH FINAL CHECK")
    print("=" * 60)
    print(f"📊 Employees processed: {employee_count}")
    print(f"📋 Compliance rules: {compliance_count}")
    print(f"📅 Shifts generated: {len(shifts)}")
    print(f"🔄 Iterations: {iteration}/{max_iterations}")
    print(f"⚠️  Violations: {len(final_violations)}")
    print(f"📈 Availability Coverage: {coverage_percent}%")
    print(f"📁 Roster file: {excel_path}")
    if report_path:
        print(f"📄 Check report: {report_path}")
    if len(final_violations) == 0 and final_check_status == "approved":
        print("✅ Roster is fully compliant and approved!")
    elif final_check_status == "needs_review":
        print("⚠️  Roster needs review (see check report for details)")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error running pipeline: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
