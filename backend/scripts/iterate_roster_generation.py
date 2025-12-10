#!/usr/bin/env python3
"""
Script to iteratively generate roster until coverage is 80-90% and shortages are minimized.
This script calls the generate-roster API repeatedly until the agents achieve the target coverage.
"""

import requests
import time
import json
import os
from typing import Dict, Any, Tuple

# API Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust if your API runs on different port
API_USERNAME = "admin"  # Adjust based on your auth setup
API_PASSWORD = "admin"  # Adjust based on your auth setup

# Target metrics
MIN_COVERAGE_PERCENT = 80
TARGET_COVERAGE_PERCENT = 90
MAX_ITERATIONS = 10  # Maximum iterations to prevent infinite loops
MIN_IMPROVEMENT_THRESHOLD = 0.01  # Minimum improvement (1%) to continue iterating


def get_auth_token() -> str:
    """Get authentication token from login endpoint."""
    login_url = f"{API_BASE_URL}/login"
    response = requests.post(
        login_url,
        data={"username": API_USERNAME, "password": API_PASSWORD},
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Failed to authenticate: {response.text}")


def generate_roster(token: str) -> Dict[str, Any]:
    """Call the generate-roster API endpoint."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{API_BASE_URL}/generate-roster"
    
    print(f"\n{'='*60}")
    print(f"Calling {url}...")
    print(f"{'='*60}")
    
    response = requests.post(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API call failed: {response.status_code} - {response.text}")


def check_coverage_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and return coverage metrics from API response."""
    coverage_percent = result.get("coverage_percent", 0)
    filled_slots = result.get("filled_slots", 0)
    total_slots = result.get("total_slots", 0)
    violation_count = result.get("violation_count", 0)
    critical_violations = result.get("critical_violations", 0)
    iterations = result.get("iterations", 0)
    roster_status = result.get("roster_status", "unknown")
    
    return {
        "coverage_percent": coverage_percent,
        "filled_slots": filled_slots,
        "total_slots": total_slots,
        "violation_count": violation_count,
        "critical_violations": critical_violations,
        "iterations": iterations,
        "roster_status": roster_status,
        "shortage": total_slots - filled_slots if total_slots > 0 else 0,
    }


def print_metrics(metrics: Dict[str, Any], iteration: int):
    """Print current metrics in a readable format."""
    print(f"\n📊 Iteration {iteration} Metrics:")
    print(f"   Coverage: {metrics['coverage_percent']:.2f}%")
    print(f"   Filled Slots: {metrics['filled_slots']}/{metrics['total_slots']}")
    print(f"   Shortage: {metrics['shortage']} slots")
    print(f"   Violations: {metrics['violation_count']} (Critical: {metrics['critical_violations']})")
    print(f"   Roster Status: {metrics['roster_status']}")
    print(f"   Internal Iterations: {metrics['iterations']}")


def should_continue_iterating(metrics: Dict[str, Any], previous_metrics: Dict[str, Any] = None) -> Tuple[bool, str]:
    """Determine if we should continue iterating based on metrics."""
    coverage = metrics["coverage_percent"]
    shortage = metrics["shortage"]
    
    # Check if we've reached target coverage
    if coverage >= TARGET_COVERAGE_PERCENT and shortage == 0:
        return False, f"✅ Target achieved: {coverage:.2f}% coverage with no shortages!"
    
    # Check if we've reached minimum coverage
    if coverage >= MIN_COVERAGE_PERCENT and shortage == 0:
        return False, f"✅ Minimum coverage achieved: {coverage:.2f}% with no shortages!"
    
    # Check if we're improving
    if previous_metrics:
        coverage_improvement = coverage - previous_metrics["coverage_percent"]
        shortage_improvement = previous_metrics["shortage"] - shortage
        
        # If coverage is improving or shortage is decreasing, continue
        if coverage_improvement >= MIN_IMPROVEMENT_THRESHOLD or shortage_improvement > 0:
            return True, f"Improving: coverage +{coverage_improvement:.2f}%, shortage -{shortage_improvement}"
        
        # If we're not improving significantly, stop
        if coverage_improvement < MIN_IMPROVEMENT_THRESHOLD and shortage_improvement <= 0:
            return False, f"No significant improvement. Coverage: {coverage:.2f}%, Shortage: {shortage}"
    
    # If we haven't reached minimum coverage yet, continue
    if coverage < MIN_COVERAGE_PERCENT:
        return True, f"Coverage {coverage:.2f}% below minimum {MIN_COVERAGE_PERCENT}%"
    
    # If we have shortages, continue
    if shortage > 0:
        return True, f"Still have {shortage} shortages to fill"
    
    return False, "Unknown condition"


def main():
    """Main iteration loop."""
    print("🚀 Starting iterative roster generation...")
    print(f"Target: {MIN_COVERAGE_PERCENT}-{TARGET_COVERAGE_PERCENT}% coverage with minimal shortages")
    print(f"Max iterations: {MAX_ITERATIONS}\n")
    
    try:
        # Authenticate
        print("🔐 Authenticating...")
        token = get_auth_token()
        print("✅ Authentication successful\n")
        
        previous_metrics = None
        best_result = None
        best_coverage = 0
        
        for iteration in range(1, MAX_ITERATIONS + 1):
            print(f"\n{'='*60}")
            print(f"ITERATION {iteration}/{MAX_ITERATIONS}")
            print(f"{'='*60}")
            
            # Generate roster
            try:
                result = generate_roster(token)
                metrics = check_coverage_metrics(result)
                print_metrics(metrics, iteration)
                
                # Track best result
                if metrics["coverage_percent"] > best_coverage:
                    best_coverage = metrics["coverage_percent"]
                    best_result = result
                
                # Check if we should continue
                should_continue, reason = should_continue_iterating(metrics, previous_metrics)
                
                print(f"\n📈 Status: {reason}")
                
                if not should_continue:
                    print(f"\n🎉 Stopping: {reason}")
                    print(f"\n✅ Final Result:")
                    print_metrics(metrics, iteration)
                    if best_result:
                        print(f"\n📁 Best Result Files:")
                        print(f"   Roster: {best_result.get('roster_file', 'N/A')}")
                        print(f"   Report: {best_result.get('report_file', 'N/A')}")
                        print(f"   JSON Report: {best_result.get('report_json_file', 'N/A')}")
                    return
                
                previous_metrics = metrics
                
                # Wait a bit before next iteration
                if iteration < MAX_ITERATIONS:
                    print(f"\n⏳ Waiting 2 seconds before next iteration...")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"❌ Error in iteration {iteration}: {e}")
                if iteration < MAX_ITERATIONS:
                    print("Retrying...")
                    time.sleep(5)
                else:
                    raise
        
        # If we've exhausted iterations
        print(f"\n⚠️  Reached maximum iterations ({MAX_ITERATIONS})")
        if best_result:
            print(f"\n📊 Best Result Achieved:")
            best_metrics = check_coverage_metrics(best_result)
            print_metrics(best_metrics, "best")
            print(f"\n📁 Best Result Files:")
            print(f"   Roster: {best_result.get('roster_file', 'N/A')}")
            print(f"   Report: {best_result.get('report_file', 'N/A')}")
            print(f"   JSON Report: {best_result.get('report_json_file', 'N/A')}")
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
