"""
Agent 1: Data Parser and Structurer
Reads employee.xlsx, store requirements, and management store data,
then structures them into a rich state using LangGraph v1 create_agent.
Uses MultiAgentState with ToolRuntime for proper multi-agent coordination.
"""

import os
import json
import pandas as pd
from typing import Annotated, Optional
from langchain.agents import create_agent
from langchain_core.messages import BaseMessage, ToolMessage
from langchain.tools import tool, ToolRuntime, InjectedToolCallId
from langgraph.types import Command
from dotenv import load_dotenv

# Import shared state
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_state import MultiAgentState

# Load environment variables
load_dotenv()


def load_employee_data(file_path: str) -> list:
    """Load employee data from Excel or CSV file"""
    try:
        # Detect file type and use appropriate reader
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == ".csv":
            # For CSV files, use read_csv
            df = pd.read_csv(file_path, skiprows=3, header=0)
        elif file_ext in [".xlsx", ".xls"]:
            # For Excel files, use read_excel
            df = pd.read_excel(file_path, skiprows=3, header=0)
        else:
            # Try Excel first, fallback to CSV
            try:
                df = pd.read_excel(file_path, skiprows=3, header=0)
            except:
                df = pd.read_csv(file_path, skiprows=3, header=0)

        # Clean up column names - remove newlines and extra spaces
        df.columns = df.columns.str.strip().str.replace("\n", " ", regex=False)

        # Remove rows where ID is NaN or empty, or is the header row
        id_col = df.columns[0] if len(df.columns) > 0 else None
        if id_col:
            # Remove header row if it exists in data
            df = df[df[id_col].astype(str).str.strip() != "ID"]
            df = df[
                df[id_col].astype(str).str.strip() != id_col
            ]  # Remove if ID column name appears as data

            # Remove rows where ID is NaN or empty
            df = df[df[id_col].notna()]
            # Convert ID to string and filter
            df[id_col] = df[id_col].astype(str).str.strip()
            df = df[df[id_col] != ""]
            df = df[df[id_col] != "nan"]
            df = df[df[id_col] != "ID"]

            # Also filter out rows where name is the header
            name_col = df.columns[1] if len(df.columns) > 1 else None
            if name_col:
                df = df[df[name_col].astype(str).str.strip() != "Employee Name"]
            df = df[df[id_col] != "ID"]

            # Also filter out rows where name is the header
            name_col = df.columns[1] if len(df.columns) > 1 else None
            if name_col:
                df = df[df[name_col].astype(str).str.strip() != "Employee Name"]

        # Convert DataFrame to list of dictionaries
        employees = df.to_dict("records")
        return employees
    except Exception as e:
        print(f"Error loading employee data: {e}")
        import traceback

        traceback.print_exc()
        return []


def load_store_requirements(file_path: str) -> dict:
    """Load store requirements from CSV or JSON"""
    try:
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
            return df.to_dict("records")
        elif file_path.endswith(".json"):
            with open(file_path, "r") as f:
                return json.load(f)
        else:
            return {}
    except Exception as e:
        print(f"Error loading store requirements: {e}")
        return {}


def load_management_store(file_path: str) -> dict:
    """Load management store data from JSON"""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading management store: {e}")
        return {}


def _structure_employee_data(employees: list) -> dict:
    """Structure employee data into a rich format with role summaries and availability"""
    structured = {
        "total_employees": len(employees),
        "employees": [],
        "employee_summary": {},
    }

    for emp in employees:
        # Handle different possible column name variations
        id_col = emp.get(
            "ID",
            emp.get("id", emp.get("Service Team - 2 Week Availability Schedule", "")),
        )
        name_col = emp.get(
            "Employee Name", emp.get("Name", emp.get("name", emp.get("Unnamed: 1", "")))
        )
        type_col = emp.get("Type", emp.get("type", emp.get("Unnamed: 2", "")))
        station_col = emp.get("Station", emp.get("station", emp.get("Unnamed: 3", "")))

        # Extract availability for all days (columns 4-17 are the days)
        availability = {}
        day_columns = [f"Unnamed: {i}" for i in range(4, 18)]
        for i, day_col in enumerate(day_columns):
            if day_col in emp:
                day_name = f"Day_{i+1}"
                availability[day_name] = (
                    str(emp[day_col]) if pd.notna(emp.get(day_col)) else ""
                )

        # Also try to get day names from column headers if available
        for key, value in emp.items():
            if (
                "Dec" in str(key)
                or "Mon" in str(key)
                or "Tue" in str(key)
                or "Wed" in str(key)
                or "Thu" in str(key)
                or "Fri" in str(key)
                or "Sat" in str(key)
                or "Sun" in str(key)
            ):
                availability[str(key).strip()] = str(value) if pd.notna(value) else ""

        structured_emp = {
            "id": str(id_col).strip() if pd.notna(id_col) else "",
            "name": str(name_col).strip() if pd.notna(name_col) else "",
            "type": str(type_col).strip() if pd.notna(type_col) else "",
            "station": str(station_col).strip() if pd.notna(station_col) else "",
            "availability": availability,
        }

        # Only add if we have at least an ID or name
        if structured_emp["id"] or structured_emp["name"]:
            structured["employees"].append(structured_emp)

    # Create summary by type/station
    type_counts = {}
    station_counts = {}
    for emp in structured["employees"]:
        emp_type = emp.get("type", "Unknown")
        emp_station = emp.get("station", "Unknown")
        type_counts[emp_type] = type_counts.get(emp_type, 0) + 1
        station_counts[emp_station] = station_counts.get(emp_station, 0) + 1

    structured["employee_summary"] = {
        "by_type": type_counts,
        "by_station": station_counts,
    }
    return structured


def _structure_store_data(store_req: dict, mgmt_store: dict) -> dict:
    """Structure store requirements and management data into a comprehensive format"""
    structured = {
        "store_config": store_req,
        "management_rules": mgmt_store,
        "requirements": {
            "staffing_levels": mgmt_store.get("staffing_levels", {}),
            "operating_hours": mgmt_store.get("operating_hours", {}),
            "rules": mgmt_store.get("rules", []),
            "shift_codes": mgmt_store.get("shifts", []),
        },
    }
    return structured


def _analyze_data_relationships(employee_data: dict, store_data: dict) -> dict:
    """Analyze relationships between employees and store requirements"""
    analysis = {
        "matching_skills": {},
        "availability_coverage": {},
        "recommendations": [],
    }

    # Analyze employee skills vs store requirements
    if "employees" in employee_data and "requirements" in store_data:
        for emp in employee_data.get("employees", []):
            emp_role = emp.get("role", "")
            if emp_role:
                analysis["matching_skills"][emp_role] = (
                    analysis["matching_skills"].get(emp_role, 0) + 1
                )

    return analysis


# Create tools from helper functions for use with create_agent
@tool
def structure_employee_data(employees: list) -> dict:
    """Structure employee data into a rich format with role summaries and availability"""
    return _structure_employee_data(employees)


@tool
def structure_store_data(store_req: dict, mgmt_store: dict) -> dict:
    """Structure store requirements and management data into a comprehensive format"""
    return _structure_store_data(store_req, mgmt_store)


@tool
def analyze_data_relationships(employee_data: dict, store_data: dict) -> dict:
    """Analyze relationships between employees and store requirements"""
    return _analyze_data_relationships(employee_data, store_data)


@tool(
    "parse_and_structure_data",
    description="Parse employee data, store requirements, and management store files, then structure them into a rich state. This is Agent 1's main function.",
)
def run_agent1_tool(
    employee_file: str = "",
    store_requirement_file: str = "",
    management_store_file: str = "",
    runtime: ToolRuntime = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Command:
    """
    Tool wrapper for Agent 1 that uses ToolRuntime to access/update state.
    """
    # Get file paths from state if not provided, or use defaults
    # Note: ToolRuntime provides state access, but we use file paths directly here
    if not employee_file or not store_requirement_file or not management_store_file:
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        backend_root = os.path.dirname(os.path.dirname(current_dir))
        dataset_path = os.path.join(backend_root, "multi_agents", "dataset")

        if not employee_file:
            employee_file = os.path.join(dataset_path, "employee.xlsx")
        if not store_requirement_file:
            csv_path = os.path.join(dataset_path, "stores.csv")
            json_path = os.path.join(dataset_path, "store_config_data.json")
            store_requirement_file = csv_path if os.path.exists(csv_path) else json_path
        if not management_store_file:
            management_store_file = os.path.join(dataset_path, "managment_store.json")

    # Run Agent 1 logic
    result = run_agent1(employee_file, store_requirement_file, management_store_file)
    state_update = result.get("state_update", {})

    # Return Command with state update
    return Command(
        update={
            "employee_data": state_update.get("employee_data", []),
            "store_requirements": state_update.get("store_requirements", {}),
            "management_store": state_update.get("management_store", {}),
            "structured_data": state_update.get("structured_data", {}),
            "messages": [
                ToolMessage(
                    content=f"Agent 1 completed. Processed {result.get('employee_count', 0)} employees and structured all data.",
                    tool_call_id=tool_call_id,
                )
            ],
        }
    )


def run_agent1(
    employee_file: str = None,
    store_requirement_file: str = None,
    management_store_file: str = None,
) -> dict:
    """
    Run Agent 1: Parse and structure input files into a rich state using LangGraph v1 create_agent.

    Args:
        employee_file: Path to employee.xlsx
        store_requirement_file: Path to store requirements file (CSV or JSON)
        management_store_file: Path to management store JSON file

    Returns:
        Dictionary containing structured data state
    """
    # Get default paths if not provided
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_root = os.path.dirname(os.path.dirname(current_dir))
    dataset_path = os.path.join(backend_root, "multi_agents", "dataset")

    if employee_file is None:
        employee_file = os.path.join(dataset_path, "employee.xlsx")
    if store_requirement_file is None:
        # Try CSV first, then JSON
        csv_path = os.path.join(dataset_path, "stores.csv")
        json_path = os.path.join(dataset_path, "store_config_data.json")
        store_requirement_file = csv_path if os.path.exists(csv_path) else json_path
    if management_store_file is None:
        management_store_file = os.path.join(dataset_path, "managment_store.json")

    # Load data files
    print(f"Loading employee data from: {employee_file}")
    employee_data = load_employee_data(employee_file)

    print(f"Loading store requirements from: {store_requirement_file}")
    store_requirements = load_store_requirements(store_requirement_file)

    print(f"Loading management store from: {management_store_file}")
    management_store = load_management_store(management_store_file)

    # Structure the data using helper functions directly
    structured_employees = _structure_employee_data(employee_data)
    structured_stores = _structure_store_data(store_requirements, management_store)

    # Prepare data summary for LLM (limit size to avoid token limits)
    # Show summary stats instead of full data to save tokens
    employee_summary = f"""
Total Employees: {structured_employees['total_employees']}
Employee Summary: {json.dumps(structured_employees.get('employee_summary', {}), indent=2)}
Sample Employees (first 3): {json.dumps(structured_employees.get('employees', [])[:3], indent=2, default=str)}
"""

    store_summary = f"""
Store Configurations: {len(structured_stores.get('store_config', []))} configurations
Shift Codes Available: {len(structured_stores.get('requirements', {}).get('shift_codes', []))} shift types
Management Rules: {len(structured_stores.get('management_rules', {}).get('keyPoints', []))} key points
"""

    # Create agent with LLM intelligence for data analysis
    print("  Using LLM to analyze and structure data intelligently...")

    agent = create_agent(
        model="openai:gpt-4o-mini",
        tools=[],  # No tools needed - data is already structured
        system_prompt="You are a data analysis assistant for roster management. Analyze the provided structured data and provide insights and recommendations for roster building.",
    )

    # Prepare prompt with actual structured data
    prompt = f"""I have loaded and structured the following data:

EMPLOYEE DATA (Total: {len(employee_data)} employees):
{employee_summary}

STORE REQUIREMENTS:
{store_summary}

Please analyze this structured data and provide:
1. Summary of employee distribution by type and station
2. Key insights about availability patterns
3. Store requirements analysis
4. Recommendations for roster building based on the data
5. Any potential issues or constraints to consider

The data has already been structured, so focus on analysis and insights rather than restructuring.
"""

    # Invoke the agent with messages in the correct format
    inputs = {"messages": [{"role": "user", "content": prompt}]}
    result = agent.invoke(inputs)

    # Extract structured data from agent response
    # In LangChain v1, result contains messages list
    final_messages = result.get("messages", [])
    llm_analysis = ""
    if final_messages:
        last_message = final_messages[-1]
        # Handle both message objects and dicts
        if hasattr(last_message, "content"):
            llm_analysis = last_message.content
        elif isinstance(last_message, dict):
            if "content" in last_message:
                llm_analysis = last_message["content"]
            elif "text" in last_message:
                llm_analysis = last_message["text"]
        else:
            llm_analysis = str(last_message)

    # Build final structured state
    structured_data = {
        "employees": structured_employees,
        "stores": structured_stores,
        "llm_analysis": llm_analysis,
        "metadata": {
            "total_employees": len(employee_data),
            "data_loaded": True,
            "files_processed": {
                "employee_file": employee_file,
                "store_requirement_file": store_requirement_file,
                "management_store_file": management_store_file,
            },
        },
    }

    # Prepare state update for potential handoff to next agent using Command
    # This can be used with Command(goto="agent_2", update=state_update) for multi-agent flow
    state_update = {
        "employee_data": employee_data,
        "store_requirements": store_requirements,
        "management_store": management_store,
        "structured_data": structured_data,
        "messages": final_messages if final_messages else [],
    }

    print(f"Agent 1 completed. Processed {len(employee_data)} employees.")

    # Return state that can be used with Command for multi-agent handoff
    # Example usage in a graph: return Command(goto="agent_2", update=state_update)
    return {
        "status": "success",
        "state": structured_data,
        "state_update": state_update,  # For use with Command(goto="agent_2", update=state_update)
        "employee_count": len(employee_data),
        "message": "Data successfully structured and enriched using LangGraph agent",
    }


if __name__ == "__main__":
    # Test the agent
    result = run_agent1()
    print("\n" + "=" * 50)
    print("Agent 1 Result:")
    print("=" * 50)
    print(json.dumps(result, indent=2, default=str))
