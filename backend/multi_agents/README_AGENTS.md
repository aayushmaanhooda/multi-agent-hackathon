# Multi-Agent Roster Generation System

> **📖 For comprehensive architecture documentation, see [ARCHITECTURE.md](./ARCHITECTURE.md)**

## Overview

This system uses a multi-agent architecture to generate and validate work rosters. The system consists of **5 specialized agents** coordinated by an **Orchestrator** (optional) that manages the workflow and decision-making process. The main execution flow is handled by `run_pipeline.py` which runs agents sequentially.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                              │
│  (Decides which agent to call and when)                     │
│  - Uses LangChain create_agent                              │
│  - Has access to all 5 agents as tools                      │
│  - Manages the workflow sequence                            │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
   ┌─────────┐      ┌─────────┐      ┌─────────┐
   │ Agent 1 │ ───► │ Agent 2 │ ───► │ Agent 3 │◄───┐
   │  Parser │      │Analyzer │      │Generator│    │
   └─────────┘      └─────────┘      └─────────┘    │
                                              │      │
                                              ▼      │
                                         ┌─────────┐│
                                         │ Agent 4 ││
                                         │Validator││
                                         └─────────┘│
                                              │      │
                                              └──────┘
                                         (Loop until valid)
                                              │
                                              ▼
                                         ┌─────────┐
                                         │ Agent 5 │
                                         │Final Chk│
                                         └─────────┘
```

## Shared State

All agents share a single `MultiAgentState` object that contains:

- **Employee Data**: Raw and structured employee information
- **Store Requirements**: Store configurations and needs
- **Management Store**: Shift codes, operating hours, rules
- **Structured Data**: Enriched data from Agent 1
- **Constraints**: Structured rules and compliance requirements
- **Rules Data**: Raw rules from JSON files
- **Roster**: Generated schedule (from Agent 3)
- **Violations**: Validation results (from Agent 4)
- **Iteration Count**: Number of generation-validation cycles
- **Final Check Report**: Comprehensive report (from Agent 5)
- **Final Check Complete**: Flag indicating final check status
- **Messages**: Conversation history for agent coordination

## Agent Details

### Agent 1: Data Parser and Structurer

**Purpose**: Loads and structures input data files into a rich, analyzable format.

**Input**:
- `employee_file`: Path to `employee.xlsx` (employee data with availability)
- `store_requirement_file`: Path to store requirements (CSV or JSON)
- `management_store_file`: Path to `managment_store.json` (shift codes, rules)

**Output**:
- **State Updates**:
  - `employee_data`: List of employee dictionaries
  - `store_requirements`: Store configuration data
  - `management_store`: Management rules and shift codes
  - `structured_data`: Enriched data with:
    - Employee summaries (by type, station)
    - Store configurations
    - LLM analysis and insights

**Key Functions**:
- Parses Excel files (skips metadata rows)
- Structures employee availability by day
- Analyzes employee distribution by type and station
- Provides data insights and recommendations

**Tool**: `parse_and_structure_data`

---

### Agent 2: Constraints Analyzer

**Purpose**: Analyzes compliance rules and store rules to create structured constraints for roster building.

**Input**:
- `rules_file`: Path to `rules.json` (Fair Work Act compliance rules)
- `store_rules_file`: Path to `store_rule.json` (store-specific working hours templates)
- **State from Agent 1**: Uses employee/store data for context

**Output**:
- **State Updates**:
  - `constraints`: Structured constraints object with:
    - `compliance_requirements`: Fair Work Act requirements
    - `shift_constraints`: Min/max shift length, rest periods
    - `penalty_rates`: Saturday (1.25x), Sunday (1.5x), Public Holidays (2.25x)
    - `break_requirements`: Meal breaks (30 min for 5+ hour shifts)
    - `working_hours_templates`: Fixed working hours by task
    - `roster_change_rules`: Notification requirements
    - `location_specific_rules`: Melbourne/Victoria specific rules
  - `rules_data`: Raw rules JSON
  - `store_rules_data`: Raw store rules JSON

**Key Functions**:
- Uses LLM with Pydantic structured output to extract constraints
- Creates comprehensive constraint structure for automated roster generation
- Contextualizes rules with employee/store data from Agent 1

**Tool**: `analyze_constraints`

---

### Agent 3: Roster Generator

**Purpose**: Generates a roster schedule ensuring all rules, employee needs, and constraints are satisfied.

**Input**:
- **State from Agent 1 & 2**: 
  - Employee data with availability
  - Store requirements
  - Constraints and rules
  - Management store (shift codes)
- **Violations (optional)**: If regenerating due to validation failures

**Output**:
- **State Updates**:
  - `roster`: Generated roster dictionary with:
    - `week_start_date` / `week_end_date`: Date range
    - `shifts`: List of shift assignments (14 days, 2 weeks)
      - Date, Day, Employee Name/ID
      - Hours, Shift Code, Shift Time
      - Employment Type, Status, Station
      - Store assignment (Store 1 or Store 2)
      - Manager assignment
    - `summary`: Total shifts, hours, employees scheduled
    - `compliance_check`: Initial compliance status
    - `excel_path`: Path to exported Excel file
  - `roster_metadata`: Generation metadata

**Key Functions**:
- Assigns shifts based on employee availability
- Distributes employees across Store 1 and Store 2 based on:
  - Traffic patterns (Store 1: 1200-1800 customers, Store 2: 600-900)
  - Peak hours
  - Station requirements (dessert station only in Store 1)
- Ensures manager coverage for each shift
- Validates shift hours against constraints (3-12 hours)
- Exports roster to Excel file (`rag/roster.xlsx`)

**Logic**:
- Generates roster for next 14 days
- Matches employee availability from Excel
- Assigns stores based on traffic and station needs
- Tracks manager assignments to ensure coverage

**Tool**: `generate_roster`

**After Generation**: Automatically routes to Agent 4 for validation using `Command(goto="agent_4")`

---

### Agent 4: Roster Validator

**Purpose**: Validates the generated roster against all constraints, employee availability, and compliance rules.

**Input**:
- **State from Agent 3**:
  - Generated roster
  - Employee data
  - Constraints
  - Store requirements

**Output**:
- **State Updates**:
  - `violations`: List of violation objects with:
    - `type`: availability, shift_length, rest_period, manager_coverage, store_coverage
    - `severity`: critical, warning, info
    - `employee`: Employee name (if applicable)
    - `date`: Date of violation
    - `shift_code`: Shift code (if applicable)
    - `message`: Detailed violation description
    - `recommendation`: Suggested fix
  - `validation_complete`: Boolean flag
  - `iteration_count`: Updated iteration count

**Validation Checks**:
1. **Employee Availability**: Ensures employees are available for assigned shifts
2. **Manager Coverage**: Verifies at least one manager per shift
3. **Shift Length**: Validates min (3h) and max (12h) shift lengths
4. **Rest Periods**: Checks minimum 10 hours rest between shifts
5. **Store Requirements**: Ensures all required stations are covered

**Decision Logic**:
- **If violations found AND iteration_count < 5**:
  - Returns `Command(goto="agent_3")` to regenerate roster
- **If no violations OR max iterations reached**:
  - Returns `Command(update=...)` to complete validation

**Tool**: `validate_roster`

---

### Agent 5: Final Comprehensive Check and Report Generator

**Purpose**: Performs final validation checks and generates comprehensive reports on roster quality.

**Input**:
- **State from Agents 1-4**:
  - Final roster
  - Employee data
  - Store requirements
  - Violations

**Output**:
- **State Updates**:
  - `final_check_report`: Comprehensive report dictionary with:
    - `roster_status`: approved, needs_review
    - `total_availability_slots`: Total employee availability slots
    - `filled_slots`: Number of filled slots
    - `unfilled_slots`: Number of unfilled slots
    - `availability_coverage_percent`: Coverage percentage
    - `staffing_checks`: List of staffing requirement checks
    - `availability_checks`: List of availability slot checks
    - `summary`: Overall summary
    - `recommendations`: List of recommendations
  - `final_check_complete`: Boolean flag

**Checks Performed**:
1. **Availability Coverage**: 
   - Checks if all employee availability slots are filled
   - Calculates coverage percentage
   - Lists unfilled slots
2. **Staffing Requirements**:
   - Verifies staffing levels per store, per station, per day
   - Checks if required staff counts are met (e.g., 6 needed in kitchen)
   - Identifies understaffed stations

**Output Files**:
- `rag/final_roster_check_report.json`: Machine-readable report
- `rag/final_roster_check_report.txt`: Human-readable report

**Tool**: `final_roster_check`

---

## Orchestrator

**Purpose**: Coordinates all agents and decides which agent to call and when.

**How It Works**:
- Uses LangChain's `create_agent` with all 5 agents as tools
- Has a system prompt that defines the workflow sequence
- Intelligently decides when to loop between Agent 3 and Agent 4
- Uses `ToolRuntime` and `InjectedToolCallId` for proper state management

**Workflow Decision**:
1. **First**: Calls `parse_and_structure_data` (Agent 1)
2. **Then**: Calls `analyze_constraints` (Agent 2)
3. **Next**: Calls `generate_roster` (Agent 3)
4. **Then**: Calls `validate_roster` (Agent 4)
5. **If violations**: Loops back to `generate_roster` (up to 7 iterations)
6. **When done**: Calls `final_roster_check` (Agent 5)
7. **Returns**: Final validated roster and comprehensive report

**Key Features**:
- Automatic looping between Agent 3 and Agent 4
- Maximum 7 iterations to allow more attempts to fix violations
- State persistence across all agent calls
- Tool-based coordination using LangChain v1 patterns
- Final comprehensive check by Agent 5 after loop completes

---

## Complete Flow

### Step-by-Step Execution

```
1. INITIALIZATION
   ├─ Orchestrator creates initial MultiAgentState
   └─ All fields initialized to empty/default values

2. AGENT 1: Data Parsing
   ├─ Orchestrator calls parse_and_structure_data tool
   ├─ Agent 1 loads:
   │  ├─ employee.xlsx
   │  ├─ stores.csv / store_config_data.json
   │  └─ managment_store.json
   ├─ Structures data into rich format
   ├─ Updates state: employee_data, store_requirements, management_store, structured_data
   └─ Returns Command with state update

3. AGENT 2: Constraints Analysis
   ├─ Orchestrator calls analyze_constraints tool
   ├─ Agent 2 loads:
   │  ├─ rules.json
   │  └─ store_rule.json
   ├─ Uses LLM to extract structured constraints
   ├─ Updates state: constraints, rules_data, store_rules_data
   └─ Returns Command with state update

4. AGENT 3: Roster Generation
   ├─ Orchestrator calls generate_roster tool
   ├─ Agent 3:
   │  ├─ Reads employee availability from state
   │  ├─ Applies constraints and rules
   │  ├─ Assigns shifts for 14 days
   │  ├─ Distributes employees across stores
   │  ├─ Ensures manager coverage
   │  └─ Exports to Excel (rag/roster.xlsx)
   ├─ Updates state: roster, roster_metadata
   └─ Returns Command(goto="agent_4") to route to validation

5. AGENT 4: Roster Validation
   ├─ Agent 4 receives roster from state
   ├─ Validates against:
   │  ├─ Employee availability
   │  ├─ Shift length constraints
   │  ├─ Rest period requirements
   │  ├─ Manager coverage
   │  └─ Store requirements
   ├─ Updates state: violations, iteration_count
   └─ Decision:
      ├─ IF violations AND iteration_count < 7:
      │  └─ Returns Command(goto="agent_3") to regenerate
      └─ ELSE:
         └─ Returns Command(update=...) to complete

6. LOOP (if violations found)
   ├─ Agent 3 regenerates roster (with violation context)
   ├─ Agent 4 validates again
   └─ Repeats until no violations OR max 7 iterations

7. AGENT 5: Final Comprehensive Check
   ├─ Agent 5 receives final roster from state
   ├─ Checks availability coverage (filled vs unfilled slots)
   ├─ Verifies staffing requirements (per store, per station, per day)
   ├─ Generates comprehensive report (JSON + text)
   ├─ Updates state: final_check_report, final_check_complete
   └─ Returns final report and status

7. COMPLETION
   ├─ Final roster in state.roster
   ├─ Violations list in state.violations
   ├─ Excel file at rag/roster.xlsx
   └─ Orchestrator returns complete result
```

### State Flow Diagram

```
Initial State (empty)
    │
    ▼
Agent 1 ──► [employee_data, store_requirements, management_store, structured_data]
    │
    ▼
Agent 2 ──► [constraints, rules_data, store_rules_data]
    │
    ▼
Agent 3 ──► [roster, roster_metadata]
    │
    ▼
Agent 4 ──► [violations, iteration_count, validation_complete]
   │
   └─► (After loop completes)
       │
       └─► Agent 5 ──► [final_check_report, final_check_complete]
    │
    ├─► IF violations: ──► Agent 3 (loop)
    │
    └─► IF no violations: ──► Complete
```

---

## Key Technologies

- **LangChain v1**: Agent framework with `create_agent`
- **LangGraph**: State management with `Command` and `goto` for agent routing
- **ToolRuntime**: Provides state access to tools
- **InjectedToolCallId**: Ensures proper tool response handling
- **Pydantic**: Structured output models for constraints and violations
- **Pandas**: Excel file processing
- **OpenAI GPT-4o-mini**: LLM for intelligent analysis and generation

---

## Usage

### Via Orchestrator (Recommended)

```python
from multi_agents.orchestrator import run_full_pipeline

result = run_full_pipeline(
    employee_file="path/to/employee.xlsx",
    store_requirement_file="path/to/stores.csv",
    management_store_file="path/to/managment_store.json",
    rules_file="path/to/rules.json",
    store_rules_file="path/to/store_rule.json"
)

print(f"Status: {result['status']}")
print(f"Violations: {result['violation_count']}")
print(f"Roster: {result['roster']}")
```

### Via Direct Pipeline

```python
from multi_agents.run_pipeline import main

main()  # Runs all agents in sequence
```

### Individual Agents

```python
from multi_agents.agent_1.agent import run_agent1
from multi_agents.agent_2.agent import run_agent2
from multi_agents.agent_3.agent import run_agent3
from multi_agents.agent_4.agent import run_agent4

# Run sequentially
result1 = run_agent1()
state1 = result1['state_update']

result2 = run_agent2(state=state1)
state2 = result2['state_update']

# ... continue
```

---

## File Structure

```
multi_agents/
├── orchestrator.py          # Main orchestrator (decides agent calls)
├── run_pipeline.py           # Direct pipeline execution
├── shared_state.py           # MultiAgentState definition
├── agent_1/
│   └── agent.py             # Data parser
├── agent_2/
│   └── agent.py             # Constraints analyzer
├── agent_3/
│   └── agent.py             # Roster generator
├── agent_4/
│   └── agent.py             # Roster validator
└── dataset/
    ├── employee.xlsx        # Employee data
    ├── stores.csv           # Store requirements
    ├── managment_store.json # Management rules
    ├── rules.json           # Fair Work Act rules
    └── store_rule.json      # Store-specific rules
```

---

## Decision Making

### Who Decides Which Agent to Call?

**The Orchestrator** decides which agent to call based on:
1. **System Prompt**: Defines the workflow sequence
2. **Current State**: Checks what data is available
3. **Tool Responses**: Agents return `Command` objects that can specify `goto` targets
4. **Violation Status**: Agent 4's validation results determine if looping is needed

### When Does Looping Happen?

The loop between Agent 3 and Agent 4 is controlled by:
- **Agent 4's validation results**: If violations are found
- **Iteration count**: Maximum 7 iterations to allow more attempts to fix violations
- **Command routing**: Agent 4 returns `Command(goto="agent_3")` to trigger regeneration

### State Management

- **Single Shared State**: All agents read from and write to the same `MultiAgentState`
- **ToolRuntime**: Provides state access within tool functions
- **Command Updates**: Agents update state using `Command(update={...})`
- **State Persistence**: State persists across all agent calls in the workflow

---

## Output

The final output includes:

1. **Excel File**: `rag/roster.xlsx` with complete 14-day schedule
2. **Roster Dictionary**: Structured roster data in state
3. **Violations List**: Any validation issues found
4. **Summary Statistics**: Total shifts, hours, employees scheduled
5. **Compliance Status**: Whether roster meets all requirements

---

## Error Handling

- **Missing Data**: Agents check for required state data before execution
- **File Not Found**: Default paths are used if files not specified
- **Validation Failures**: System attempts up to 3 regeneration cycles
- **State Errors**: Graceful handling of missing state fields

---

## Future Enhancements

- Add more sophisticated constraint optimization
- Implement employee preference learning
- Add real-time roster updates
- Integrate with payroll systems
- Add predictive analytics for staffing needs
