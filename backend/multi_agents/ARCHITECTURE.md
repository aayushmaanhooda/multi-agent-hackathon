# Multi-Agent Roster Generation System - Architecture Documentation

## Overview

This system implements a **multi-agent orchestration pattern** for automated roster generation using LangChain v1 and LangGraph. The architecture follows a **sequential pipeline with iterative refinement**, where specialized agents work together to generate, validate, and optimize work schedules.

## Architecture Pattern

### Pattern Type: **Sequential Multi-Agent Pipeline with Iterative Refinement Loop**

The system uses:
- **Sequential Execution**: Agents run in a specific order (Agent 1 → Agent 2 → Agent 3-4 Loop → Agent 5)
- **Shared State Management**: All agents read from and write to a centralized `MultiAgentState`
- **Iterative Refinement**: Agents 3 and 4 form a feedback loop that improves the roster over multiple iterations
- **Tool-Based Agent Exposure**: Each agent is exposed as a tool to the orchestrator using `ToolRuntime` and `InjectedToolCallId`

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Optional)                       │
│  - Coordinates agent execution                                   │
│  - Uses LangChain create_agent with tools                       │
│  - Can be used for LLM-driven orchestration                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RUN_PIPELINE (Main Entry)                    │
│  - Sequential agent execution                                   │
│  - Manages iteration loop                                       │
│  - Handles state updates                                        │
└─────────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  AGENT 1     │    │  AGENT 2     │    │  AGENT 3-4   │
│  Data Parser │───▶│  Constraints │───▶│  Loop        │
│              │    │  Analyzer    │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        │                   │                   │
        ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED STATE (MultiAgentState)               │
│  - employee_data, store_requirements, management_store          │
│  - constraints, rules_data                                      │
│  - roster, violations, iteration_count                          │
│  - final_check_report                                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │  AGENT 5     │
                    │  Final Check │
                    └──────────────┘
```

## Agent Responsibilities

### Agent 1: Data Parser and Structurer

**Purpose**: Parse and structure input data files into a rich, usable format

**Responsibilities**:
- Load employee data from Excel (`employee.xlsx`)
- Load store requirements from CSV/JSON (`stores.csv`)
- Load management store data from JSON (`managment_store.json`)
- Structure data into standardized format
- Extract availability patterns
- Create employee summaries and role distributions

**Input**:
- `employee_file`: Path to employee.xlsx
- `store_requirement_file`: Path to stores.csv
- `management_store_file`: Path to managment_store.json

**Output** (writes to state):
- `employee_data`: List of employee dictionaries
- `store_requirements`: Store configuration data
- `management_store`: Shift codes, times, and management rules
- `structured_data`: Enriched and structured data summary

**Key Functions**:
- `load_employee_data()`: Parses Excel with header handling
- `load_store_requirements()`: Loads CSV/JSON store data
- `_structure_employee_data()`: Creates rich employee data structure
- `_structure_store_data()`: Organizes store configurations

**Design Decision**: LLM analysis is skipped for performance (data is already structured)

---

### Agent 2: Constraints Analyzer

**Purpose**: Analyze compliance rules and create structured constraints for roster generation

**Responsibilities**:
- Load rules from `rules.json` and `store_rule.json`
- Use LLM with Pydantic structured output to extract constraints
- Create structured constraint models (shift constraints, penalty rates, break requirements)
- Handle structured output validation errors gracefully
- Provide fallback constraint creation if LLM fails

**Input**:
- `rules_file`: Path to rules.json
- `store_rules_file`: Path to store_rule.json
- State from Agent 1

**Output** (writes to state):
- `constraints`: Structured constraints dictionary
- `rules_data`: Raw rules data
- `store_rules_data`: Raw store rules data

**Key Pydantic Models**:
- `StructuredConstraints`: Main constraints container
- `ShiftConstraint`: Min/max shift length, rest periods
- `PenaltyRate`: Weekend/holiday penalty multipliers
- `BreakRequirement`: Meal and rest break rules
- `WorkingHoursTemplate`: Fixed working hour templates

**Key Functions**:
- `run_agent2()`: Main execution function
- `_extract_constraints_from_rules()`: LLM-based extraction
- Fallback logic for constraint creation if LLM fails

**Design Decision**: Uses structured output with fallback to ensure constraints are always available

---

### Agent 3: Roster Generator

**Purpose**: Generate roster schedule that satisfies all constraints and requirements

**Responsibilities**:
- Generate 14-day roster (2 weeks)
- Assign employees to shifts based on availability
- Respect employee availability preferences
- Apply shift constraints (min/max hours, rest periods)
- Assign stores and managers to shifts
- Learn from violations in previous iterations
- Export roster to Excel format

**Input**:
- State from Agents 1 and 2
- `violations`: List of violations from previous iteration (for learning)

**Output** (writes to state):
- `roster`: Generated roster with shifts, assignments, and metadata
- `roster_metadata`: Generation statistics and summary

**Key Features**:
- **Violation Learning**: Analyzes violations from Agent 4 to improve roster
  - Tracks problematic assignments
  - Maintains violation blacklist
  - Adjusts shift preferences
  - Tracks rest period violations
  - Handles shift length issues
- **Progressive Rest Period Enforcement**: 
  - Iteration 1: Skip if < 7 hours (maximize coverage)
  - Iteration 2: Skip if < 8 hours
  - Iteration 3: Skip if < 8.5 hours
  - Iteration 4: Skip if < 9 hours
  - Iteration 5: Skip if < 9.5 hours
  - Iterations 6-7: Skip if < 10 hours (full requirement)
- **Dynamic Rest Period Checking**: Checks rest periods against previous shifts in current roster
- **Employee Shuffling**: Randomizes employee order per iteration for variation

**Key Functions**:
- `_generate_roster_from_state()`: Core roster generation logic
- `_assign_store_to_employee()`: Store assignment based on traffic/requirements
- `_assign_manager_to_shift()`: Manager coverage assignment
- `_get_shift_info()`: Retrieves shift time and hours from management store
- `_export_roster_to_excel()`: Exports roster to Excel file

**Design Decisions**:
- Uses accumulated violations across iterations to prevent reintroducing problems
- Balances coverage vs violations through progressive thresholds
- Skips LLM calls for performance (deterministic generation)

---

### Agent 4: Roster Validator

**Purpose**: Validate generated roster against all constraints and identify violations

**Responsibilities**:
- Check employee availability compliance
- Validate shift length constraints
- Check rest period requirements (10 hours minimum)
- Verify manager coverage
- Check store/station coverage requirements
- Return structured violation list with recommendations

**Input**:
- State with roster from Agent 3

**Output** (writes to state):
- `violations`: List of violation dictionaries
- `validation_complete`: Boolean flag
- Violation counts (total, critical)

**Violation Types**:
1. **Availability**: Employee not available for assigned shift
2. **Shift Length**: Shift too short or too long
3. **Rest Period**: Insufficient rest between shifts (< 10 hours)
4. **Manager Coverage**: Missing manager on shift
5. **Store Coverage**: Insufficient staff for station/store

**Key Functions**:
- `_check_employee_availability()`: Validates availability matches assignment
- `_check_shift_length_constraints()`: Validates min/max shift hours
- `_check_rest_periods()`: Validates 10-hour rest period requirement
- `_check_manager_coverage()`: Ensures manager on each shift
- `_check_store_coverage()`: Validates station staffing requirements

**Design Decision**: Day key calculation matches Agent 3 exactly to prevent false violations

---

### Agent 5: Final Comprehensive Check and Report Generator

**Purpose**: Perform final validation and generate comprehensive reports

**Responsibilities**:
- Check availability coverage (how many slots filled)
- Verify staffing requirements (e.g., 6 needed in kitchen)
- Generate detailed check report (JSON and text)
- Provide recommendations for improvements
- Calculate final roster status

**Input**:
- State with final roster and violations

**Output** (writes to state):
- `final_check_report`: Comprehensive report dictionary
- `final_check_complete`: Boolean flag
- Report files (JSON and text)

**Key Checks**:
1. **Availability Coverage**: 
   - Total availability slots
   - Filled vs unfilled slots
   - Coverage percentage
   - Lists unfilled slots
2. **Staffing Requirements**:
   - Per store, per station, per day
   - Required vs assigned staff counts
   - Identifies understaffed stations

**Key Functions**:
- `_check_availability_coverage()`: Checks if all availability slots are filled
- `_check_staffing_requirements()`: Validates staffing levels
- `_generate_final_report()`: Creates comprehensive report
- `_export_check_report()`: Exports report to files

**Report Status**:
- `approved`: Roster is complete and meets all requirements
- `needs_review`: Minor issues that need review
- `needs_review`: Significant gaps requiring attention

---

## State Management

### MultiAgentState

All agents share a single `MultiAgentState` object that extends LangChain's `AgentState`:

```python
class MultiAgentState(AgentState):
    # From Agent 1
    employee_data: List[Dict[str, Any]]
    store_requirements: Dict[str, Any]
    management_store: Dict[str, Any]
    structured_data: Dict[str, Any]
    
    # From Agent 2
    constraints: Dict[str, Any]
    rules_data: Dict[str, Any]
    store_rules_data: Dict[str, Any]
    
    # From Agent 3
    roster: Dict[str, Any]
    roster_metadata: Dict[str, Any]
    
    # From Agent 4
    violations: List[Dict[str, Any]]
    iteration_count: int
    validation_complete: bool
    
    # From Agent 5
    final_check_report: Dict[str, Any]
    final_check_complete: bool
    
    # Messages
    messages: Sequence[BaseMessage]
```

**State Access Pattern**:
- Agents read from state using `getattr()` or dictionary access
- Agents write to state using `setattr()` or dictionary assignment
- Helper functions `_update_state()` and `_get_state_value()` handle both dict and object types

---

## Workflow and Execution Flow

### Sequential Pipeline Execution

```
1. Agent 1: Parse Data
   ├─ Load employee.xlsx
   ├─ Load stores.csv
   ├─ Load managment_store.json
   └─ Structure data → Write to state

2. Agent 2: Analyze Constraints
   ├─ Load rules.json
   ├─ Load store_rule.json
   ├─ Extract constraints (LLM + fallback)
   └─ Write constraints to state

3. Agent 3-4 Loop (up to 7 iterations):
   ├─ Agent 3: Generate Roster
   │  ├─ Read state (employees, constraints, violations)
   │  ├─ Generate 14-day roster
   │  ├─ Apply violation learning
   │  ├─ Export to Excel
   │  └─ Write roster to state
   │
   ├─ Agent 4: Validate Roster
   │  ├─ Read roster from state
   │  ├─ Check all constraints
   │  ├─ Identify violations
   │  └─ Write violations to state
   │
   └─ Loop Decision:
      ├─ If violations = 0: Exit loop ✅
      ├─ If iterations < 7: Continue loop
      └─ If iterations = 7: Exit loop (max reached)

4. Agent 5: Final Check
   ├─ Read final roster and violations
   ├─ Check availability coverage
   ├─ Check staffing requirements
   ├─ Generate comprehensive report
   └─ Write report to state
```

### Iterative Refinement Loop

The Agent 3-4 loop implements **iterative refinement**:

1. **Iteration 1**: Generate initial roster (maximize coverage)
2. **Iteration 2-7**: 
   - Agent 4 identifies violations
   - Agent 3 learns from violations
   - Agent 3 regenerates roster with fixes
   - Progressive strictness (rest period thresholds increase)

**Violation Learning Mechanism**:
- **Accumulated Violations**: All violations from previous iterations are tracked
- **Problematic Assignments**: Tracked as `(employee, date, shift_code)` tuples
- **Violation Blacklist**: Critical violations prevent re-assignment
- **Shift Preferences**: Preferred shifts extracted from violation messages
- **Rest Period Tracking**: Dates with rest period violations are tracked
- **Dynamic Checking**: Real-time rest period validation during generation

---

## Communication Patterns

### 1. Tool-Based Agent Exposure

Each agent exposes itself as a LangChain tool:

```python
@tool
def run_agent1_tool(
    employee_file: str = "",
    runtime: ToolRuntime = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = None,
) -> Command:
    # Access state via runtime
    # Update state via runtime
    # Return Command with goto for orchestration
```

**Benefits**:
- Agents can be called by orchestrator or directly
- State access via `ToolRuntime`
- Supports `Command` with `goto` for dynamic routing

### 2. Direct Function Calls

In `run_pipeline.py`, agents are called directly as functions:

```python
result1 = run_agent1()
result2 = run_agent2(state=state1)
result3 = run_agent3(state=multi_state)
```

**Benefits**:
- Simpler execution flow
- Direct state passing
- Better error handling
- Faster execution (no LLM overhead)

### 3. State-Based Communication

All agents communicate through shared state:
- **Write**: Agents write results to state
- **Read**: Agents read previous results from state
- **No Direct Communication**: Agents don't call each other directly

---

## Key Design Decisions

### 1. **Shared State vs Message Passing**

**Choice**: Shared State (`MultiAgentState`)

**Rationale**:
- Simpler data access
- All agents see complete context
- Easier debugging and inspection
- LangChain v1 pattern compatibility

### 2. **Sequential vs Parallel Execution**

**Choice**: Sequential Pipeline

**Rationale**:
- Agents have dependencies (Agent 2 needs Agent 1's output)
- Iterative loop requires sequential execution
- Simpler error handling
- Predictable execution order

### 3. **LLM Usage Strategy**

**Choice**: Minimal LLM usage (only Agent 2 for constraint extraction)

**Rationale**:
- Performance: LLM calls are slow
- Determinism: Roster generation should be reproducible
- Cost: Reduces API costs
- Reliability: Deterministic logic is more predictable

**Where LLMs are used**:
- Agent 2: Constraint extraction (with fallback)
- Orchestrator: Optional LLM-driven coordination

**Where LLMs are NOT used**:
- Agent 1: Data parsing (deterministic)
- Agent 3: Roster generation (deterministic with learning)
- Agent 4: Validation (rule-based)
- Agent 5: Reporting (deterministic)

### 4. **Iterative Refinement Strategy**

**Choice**: Progressive strictness with violation learning

**Rationale**:
- **Iteration 1**: Maximize coverage (fill all slots)
- **Iterations 2-7**: Gradually fix violations
- **Progressive Thresholds**: Rest period checks become stricter
- **Violation Accumulation**: Learn from all previous iterations

**Benefits**:
- Balances coverage and violations
- Prevents reintroducing fixed problems
- Allows system to converge to optimal solution

### 5. **Violation Handling Strategy**

**Choice**: Multi-layered violation tracking

**Mechanisms**:
1. **Blacklist**: Critical violations prevent re-assignment
2. **Problematic Assignments**: Track exact `(employee, date, shift)` that caused violations
3. **Shift Preferences**: Extract preferred shifts from violation messages
4. **Rest Period Tracking**: Track dates with rest period issues
5. **Dynamic Checking**: Real-time validation during generation

**Benefits**:
- Comprehensive learning from violations
- Prevents repeating mistakes
- Allows targeted fixes

### 6. **Coverage vs Violations Balance**

**Choice**: Configurable balance with early stopping

**Strategy**:
- Early iterations: Prioritize coverage
- Later iterations: Prioritize violation reduction
- Early stopping: Stop if excellent balance achieved (≥90% coverage, ≤10 violations)

**Implementation**:
- Progressive rest period thresholds
- Conditional skipping based on iteration
- Early stopping logic in `run_pipeline.py`

---

## Data Flow

### Input Data Files

```
dataset/
├── employee.xlsx          # Employee data with availability
├── stores.csv             # Store requirements
├── managment_store.json   # Shift codes, times, management rules
├── rules.json             # Compliance rules
└── store_rule.json        # Store-specific rules
```

### Data Transformation Flow

```
Raw Files (Excel/CSV/JSON)
    ↓
Agent 1: Parse & Structure
    ↓
Structured Data (employee_data, store_requirements, management_store)
    ↓
Agent 2: Extract Constraints
    ↓
Structured Constraints (shift_constraints, penalty_rates, break_requirements)
    ↓
Agent 3: Generate Roster
    ↓
Roster (shifts, assignments, Excel file)
    ↓
Agent 4: Validate
    ↓
Violations List
    ↓
[Loop: Agent 3 ← Violations → Agent 4]
    ↓
Final Roster
    ↓
Agent 5: Final Check
    ↓
Comprehensive Report (JSON + Text)
```

---

## Error Handling

### 1. **Structured Output Validation**

Agent 2 uses try-catch for LLM structured output:
```python
try:
    result = agent.invoke(inputs)
except (StructuredOutputValidationError, ValueError, Exception) as e:
    # Fallback to direct constraint creation
```

### 2. **State Access Safety**

Helper functions handle both dict and object types:
```python
def _update_state(state, key, value):
    if isinstance(state, dict):
        state[key] = value
    else:
        setattr(state, key, value)
```

### 3. **None Value Handling**

All numeric constraints have defaults:
```python
min_hours = float(min_hours) if min_hours is not None else 3.0
max_hours = float(max_hours) if max_hours is not None else 12.0
```

### 4. **File Loading Errors**

All file loaders have try-catch with fallbacks:
```python
try:
    df = pd.read_excel(file_path, skiprows=3, header=0)
except Exception as e:
    print(f"Error loading employee data: {e}")
    return []
```

---

## Performance Optimizations

### 1. **LLM Call Reduction**

- Agent 1: LLM analysis skipped (data already structured)
- Agent 3: No LLM calls (deterministic generation)
- Agent 4: No LLM calls (rule-based validation)
- Agent 5: No LLM calls (deterministic reporting)

### 2. **Violation Accumulation**

- Tracks violations across iterations to prevent reintroduction
- Uses set-based deduplication for efficiency

### 3. **Early Stopping**

- Stops if excellent balance achieved (≥90% coverage, ≤10 violations)
- Prevents unnecessary iterations

### 4. **Deterministic Generation**

- Uses `random.seed(42 + iteration)` for reproducibility
- Employee shuffling for variation without randomness

---

## Output Files

### Generated Files

1. **Roster Excel File**: `rag/roster.xlsx`
   - Contains all shift assignments
   - Columns: Date, Day, Employee Name, Hours, Shift Code, Shift Time, etc.

2. **Final Check Report (JSON)**: `rag/final_roster_check_report.json`
   - Machine-readable report
   - Contains all check results

3. **Final Check Report (Text)**: `rag/final_roster_check_report.txt`
   - Human-readable report
   - Includes recommendations

---

## Extension Points

### Adding New Agents

1. Create agent directory: `agent_N/`
2. Create `agent.py` with:
   - `run_agentN()` function
   - `run_agentN_tool()` for orchestrator integration
3. Add state fields to `MultiAgentState`
4. Update `run_pipeline.py` to call new agent
5. Update orchestrator to include new tool

### Adding New Violation Types

1. Add violation type to Agent 4's validation functions
2. Add tracking logic to Agent 3's violation learning
3. Update violation handling in roster generation

### Adding New Constraints

1. Add constraint model to Agent 2's Pydantic models
2. Update extraction logic in Agent 2
3. Update validation logic in Agent 4
4. Update generation logic in Agent 3

---

## Technology Stack

- **LangChain v1**: Agent framework and tool system
- **LangGraph**: State management and orchestration
- **Pydantic**: Structured data validation
- **Pandas**: Data processing and Excel export
- **Python 3.x**: Core language

---

## Architecture Summary

This multi-agent system follows a **sequential pipeline with iterative refinement** pattern:

1. **Sequential Agents**: Agents 1, 2, 5 run once in sequence
2. **Iterative Loop**: Agents 3-4 loop up to 7 times for refinement
3. **Shared State**: All agents communicate through `MultiAgentState`
4. **Violation Learning**: Agent 3 learns from Agent 4's feedback
5. **Progressive Optimization**: System balances coverage and violations across iterations
6. **Tool-Based Integration**: Agents can be used as tools in orchestrator or called directly

The architecture prioritizes:
- **Determinism**: Reproducible results
- **Performance**: Minimal LLM usage
- **Learning**: Violation-based improvement
- **Balance**: Coverage vs violations optimization
