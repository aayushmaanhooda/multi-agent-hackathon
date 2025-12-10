# Multi-Agent System - LangGraph Orchestrated Roster Generation

## Overview

A sophisticated multi-agent system built with LangChain and LangGraph that generates optimized employee rosters for McDonald's stores. The system uses five specialized agents working in coordination through a shared state machine to parse data, analyze constraints, generate schedules, validate compliance, and produce comprehensive reports.

## Architecture Philosophy

This system uses a **state machine-orchestrated multi-agent architecture** where:

- **LangGraph State Machine** orchestrates agent execution flow
- **Shared State (`MultiAgentState`)** enables inter-agent communication
- **Deterministic Routing** uses conditional logic based on state values (not LLM reasoning)
- **Iterative Refinement** through Agent 3-4 loop until compliance achieved

### State Machine Orchestration vs True Supervisor Agent

**State Machine Orchestration (This System)**:
- LangGraph state machine controls agent execution flow
- Routing logic is **deterministic and hardcoded** (not decided by an intelligent supervisor)
- Conditional routing based on state values (e.g., violation count, iteration count)
- State machine enforces workflow structure
- Predictable execution order with conditional branching
- **No supervisor agent** - routing is rule-based, not LLM-decided

**True Supervisor Agent Architecture**:
- A supervisor agent (LLM-powered) intelligently decides which agent to call next
- Supervisor reasons about the current state and chooses the best next action
- More flexible but less predictable
- Supervisor makes decisions dynamically based on context

**Hands-Off Multi-Agent**:
- Agents communicate directly with each other
- No central orchestrator
- Agents decide when to call other agents
- Most flexible but least predictable

Our system uses state machine orchestration for reliability, traceability, and deterministic behavior in roster generation. The routing is **not** decided by an intelligent supervisor - it's based on explicit conditional logic in the state machine.

## Tech Stack

- **LangChain** - Agent framework and LLM integration
- **LangGraph** - State machine orchestration
- **OpenAI GPT-4o-mini** - LLM for agent reasoning
- **Pydantic** - Structured output validation
- **Pandas** - Data processing
- **OpenPyXL** - Excel file generation
- **Pinecone** - Vector store (for RAG)

## Project Structure

```
multi_agents/
├── orchestrator.py      # LangGraph state machine orchestrator
├── shared_state.py      # MultiAgentState definition
├── agent_1/
│   └── agent.py         # Data Parser & Structurer
├── agent_2/
│   └── agent.py         # Constraints Analyzer
├── agent_3/
│   └── agent.py         # Roster Generator (LLM-powered)
├── agent_4/
│   └── agent.py         # Roster Validator
├── agent_5/
│   └── agent.py         # Final Check & Report Generator
├── rag/
│   └── rag.py           # RAG system for roster queries
├── dataset/             # Input files (employee.xlsx, stores.csv, configs)
└── README.md
```

## Agent Roles & Responsibilities

### Agent 1: Data Parser & Structurer

**Purpose**: Parse and structure input files into a rich, structured state.

**Responsibilities**:
- Load employee data from `.xlsx` or `.csv` files
- Parse store requirements from `.csv` files
- Load management store configuration from JSON
- Structure data into `MultiAgentState`
- Enrich employee data with availability parsing

**Tools**:
- `load_employee_data(file_path)` - Loads and parses employee files
- `load_store_requirements(file_path)` - Loads store requirements
- `load_management_store(file_path)` - Loads management config
- `structure_data(...)` - Structures all data into state format

**Output State Fields**:
- `employee_data`: List of employee dictionaries
- `store_requirements`: Store configuration dict
- `management_store`: Management rules dict
- `structured_data`: Enriched structured data

**Key Features**:
- Handles both Excel (.xlsx) and CSV formats
- Parses employee availability from structured format
- Validates data integrity
- Skips header rows automatically

### Agent 2: Constraints Analyzer

**Purpose**: Analyze rules and constraints to create structured constraint data for roster generation.

**Responsibilities**:
- Load rules from `rules.json` and `store_rule.json`
- Use LLM with Pydantic structured output to parse constraints
- Create structured constraint objects (shift constraints, penalty rates, compliance requirements)
- Validate constraint structure

**Tools**:
- `load_rules(file_path)` - Loads rules JSON
- `load_store_rules(file_path)` - Loads store-specific rules
- `run_agent2_tool(...)` - Main agent execution tool

**LLM Integration**:
- Uses `create_agent` with GPT-4o-mini
- Structured output via Pydantic models:
  - `ShiftConstraint` - Min/max shift lengths, rest periods
  - `PenaltyRate` - Penalty rates by day type
  - `ComplianceRequirement` - Compliance rules

**Output State Fields**:
- `constraints`: Structured constraints dict
- `rules_data`: Raw rules data
- `store_rules_data`: Raw store rules data

**Key Features**:
- LLM-powered constraint extraction
- Structured validation via Pydantic
- Handles complex nested rules
- Extracts penalty rates, shift limits, compliance rules

### Agent 3: Roster Generator

**Purpose**: Generate optimized roster schedule using LLM intelligence.

**Responsibilities**:
- Generate weekly roster schedule
- Assign employees to shifts based on availability
- Meet staffing requirements for each station
- Optimize for 80-90% coverage
- Minimize shortages
- Apply shift hours from management store
- Handle penalty rates and breaks

**Tools**:
- `generate_roster_tool(...)` - Main roster generation tool
  - Takes employee data, constraints, store requirements
  - Returns generated roster with shifts

**LLM Integration**:
- Uses `create_agent` with GPT-4o-mini
- System prompt emphasizes:
  - **PRIMARY GOAL**: Achieve 80-90% coverage
  - **MINIMIZE SHORTAGES**: Fill all understaffed stations
  - **FILL ALL AVAILABILITY**: Assign available employees
  - **LENIENT CONSTRAINTS**: Allow flexibility when stations understaffed

**Coverage Targets**:
- Minimum: 80% coverage
- Target: 90% coverage
- Ideal: 90%+ with zero shortages

**Output State Fields**:
- `roster`: Generated roster dict with shifts
- `roster_metadata`: Metadata about generation (iteration, total shifts, etc.)

**Key Features**:
- LLM-powered intelligent scheduling
- Coverage optimization (80-90% target)
- Shortage minimization
- Flexible constraint handling
- Shift hour variation based on shift codes
- Excel export capability

### Agent 4: Roster Validator

**Purpose**: Validate generated roster against all constraints and rules.

**Responsibilities**:
- Check employee availability compliance
- Validate constraint adherence (shift lengths, rest periods)
- Check compliance requirements (hours limits, breaks)
- Identify violations with severity levels
- Provide recommendations for fixes

**Tools**:
- `validate_roster_tool(...)` - Main validation tool
  - Checks availability, constraints, compliance
  - Returns list of violations

**Validation Checks**:
- **Availability**: Employee assigned to unavailable shift
- **Constraint**: Shift length, rest period violations
- **Compliance**: Hours limits, break requirements
- **Staffing**: Station understaffing

**Violation Severity**:
- `critical`: Must fix (availability, critical constraints)
- `warning`: Should fix (minor constraint violations)
- `info`: Nice to fix (optimization opportunities)

**Output State Fields**:
- `violations`: List of violation dictionaries
- `validation_complete`: Boolean flag
- `iteration_count`: Incremented on each validation

**Key Features**:
- Comprehensive violation detection
- Severity classification
- Detailed violation messages
- Fix recommendations
- Iteration tracking

### Agent 5: Final Check & Report Generator

**Purpose**: Perform final comprehensive check and generate reports.

**Responsibilities**:
- Verify final roster completeness
- Check availability coverage (filled vs total slots)
- Verify staffing requirements met
- Generate comprehensive text report
- Generate JSON report with structured data
- Calculate coverage metrics

**Tools**:
- `final_check_tool(...)` - Main final check tool
  - Checks coverage, staffing, completeness
  - Generates reports

**Report Generation**:
- **Text Report** (`final_roster_check_report.txt`):
  - Availability coverage analysis
  - Staffing requirement checks
  - Summary and recommendations
  
- **JSON Report** (`final_roster_check_report.json`):
  - Structured data for programmatic access
  - Coverage percentages
  - Detailed slot-by-slot analysis

**Output State Fields**:
- `final_check_report`: Report dict with:
  - `roster_status`: "compliant", "needs_improvement", etc.
  - `availability_coverage_percent`: Coverage percentage
  - `filled_slots`: Number of filled slots
  - `total_slots`: Total available slots
  - `report_path`: Path to generated report
  - `summary`: Text summary
  - `recommendations`: List of recommendations

**Key Features**:
- Comprehensive final validation
- Coverage metric calculation
- Dual report format (text + JSON)
- Detailed slot analysis
- Actionable recommendations

## Shared State (`MultiAgentState`)

All agents communicate through a shared state object:

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
    
    # LangChain messages
    messages: Sequence[BaseMessage]
```

**State Management**:
- LangGraph automatically merges state updates
- Each agent reads full state, writes partial updates
- State persists across agent executions
- Enables iterative refinement

## LangGraph Orchestration

### State Machine Structure

```
START
  ↓
Agent 1 (Parse Data)
  ↓
Agent 2 (Analyze Constraints)
  ↓
Agent 3 (Generate Roster)
  ↓
Agent 4 (Validate Roster)
  ↓
  ├─→ [Violations Found & Iterations < 4] → Agent 3 (Loop)
  │
  └─→ [No Violations OR Max Iterations] → Agent 5 (Final Check)
      ↓
     END
```

### Conditional Routing

**From Agent 4**:
```python
if violation_count == 0 or validation_complete:
    return "agent_5"  # Move to final check
elif iteration_count < max_iterations:
    return "agent_3"  # Loop back to regenerate
else:
    return "agent_5"  # Max iterations reached
```

**Routing Logic**:
- Agent 1 → Always goes to Agent 2
- Agent 2 → Always goes to Agent 3
- Agent 3 → Always goes to Agent 4
- Agent 4 → Conditionally routes to Agent 3 or Agent 5
- Agent 5 → Always ends workflow

### Graph Creation

```python
workflow = StateGraph(MultiAgentState)

# Add nodes
workflow.add_node("agent_1", agent_1_node)
workflow.add_node("agent_2", agent_2_node)
workflow.add_node("agent_3", agent_3_node)
workflow.add_node("agent_4", agent_4_node)
workflow.add_node("agent_5", agent_5_node)

# Set entry point
workflow.set_entry_point("agent_1")

# Add conditional edges
workflow.add_conditional_edges("agent_1", route_from_agent_1, {...})
workflow.add_conditional_edges("agent_4", route_from_agent_4, {...})
# ... etc

# Compile graph
app = workflow.compile()
```

## Agent Workflow Pipeline

### Step-by-Step Execution

1. **Initialization**:
   - Create initial `MultiAgentState` with empty fields
   - Load file paths (employee, store, config files)
   - Create LangGraph state machine

2. **Agent 1 Execution**:
   - Loads employee data from `.xlsx` or `.csv`
   - Parses store requirements from `.csv`
   - Loads management store JSON
   - Structures data into state
   - Updates: `employee_data`, `store_requirements`, `management_store`, `structured_data`

3. **Agent 2 Execution**:
   - Reads rules from `rules.json` and `store_rule.json`
   - Uses LLM to extract structured constraints
   - Validates constraint structure via Pydantic
   - Updates: `constraints`, `rules_data`, `store_rules_data`

4. **Agent 3 Execution** (First Iteration):
   - Receives full state (employees, constraints, requirements)
   - LLM generates roster schedule
   - Assigns employees to shifts
   - Optimizes for 80-90% coverage
   - Exports to Excel
   - Updates: `roster`, `roster_metadata`

5. **Agent 4 Execution** (First Iteration):
   - Validates roster against constraints
   - Checks availability compliance
   - Identifies violations
   - Updates: `violations`, `iteration_count`, `validation_complete`

6. **Iteration Loop** (If Violations Found):
   - Agent 4 routes back to Agent 3
   - Agent 3 regenerates roster (with violation context)
   - Agent 4 validates again
   - Repeats up to 4 times total

7. **Agent 5 Execution** (Final):
   - Performs comprehensive final check
   - Calculates coverage metrics
   - Verifies staffing requirements
   - Generates text and JSON reports
   - Updates: `final_check_report`, `final_check_complete`

8. **Workflow Completion**:
   - State machine reaches END
   - Final state returned to caller
   - Reports saved to `rag/` directory

## Techniques Used

### LangChain Agents

Each agent uses `create_agent` from LangChain:

```python
agent = create_agent(
    model="openai:gpt-4o-mini",
    tools=[tool1, tool2, ...],
    system_prompt="...",
)
```

**Features**:
- Tool calling for structured operations
- System prompts for agent behavior
- LLM reasoning for complex decisions

### LangGraph State Machine

- **StateGraph**: Defines workflow structure
- **Nodes**: Agent execution functions
- **Conditional Edges**: Dynamic routing logic
- **State Merging**: Automatic state updates

### Structured Output

Pydantic models ensure type safety:

```python
class ShiftConstraint(BaseModel):
    min_shift_length_hours: Optional[float]
    max_shift_length_hours: Optional[float]
    min_rest_between_shifts_hours: Optional[float]
```

**Benefits**:
- Type validation
- LLM output structure enforcement
- Error detection

### Tool Calling

Agents use LangChain tools:

```python
@tool
def generate_roster_tool(...):
    """Tool description for LLM"""
    # Implementation
    return result
```

**Features**:
- LLM decides when to call tools
- Tool descriptions guide LLM behavior
- Structured tool inputs/outputs

### Memory Layer

- **RAG System**: Uses Pinecone vector store
- **State Persistence**: LangGraph checkpointing

### Action Planning

LLM agents plan actions:
- Agent 3 plans shift assignments
- Considers multiple constraints simultaneously
- Optimizes for coverage and shortages
- Adapts based on validation feedback

## Interaction Diagram

```
┌─────────────┐
│   Frontend  │
│  (React)    │
└──────┬──────┘
       │ HTTP POST /generate-roster
       ↓
┌─────────────┐
│   Backend   │
│  (FastAPI)  │
└──────┬──────┘
       │ run_full_pipeline()
       ↓
┌─────────────────────────────────────┐
│      LangGraph Orchestrator          │
│  ┌───────────────────────────────┐  │
│  │     StateGraph                │  │
│  │                               │  │
│  │  Agent 1 ──→ Agent 2         │  │
│  │     │            │            │  │
│  │     │            ↓            │  │
│  │     │         Agent 3        │  │
│  │     │            │            │  │
│  │     │            ↓            │  │
│  │     │         Agent 4        │  │
│  │     │         ↙    ↘         │  │
│  │     │    Loop    Agent 5    │  │
│  │     │    (if violations)    │  │
│  └───────────────────────────────┘  │
│                                       │
│  Shared State (MultiAgentState)      │
└─────────────────────────────────────┘
       │
       │ Final State
       ↓
┌─────────────┐
│   Backend   │
│  Returns    │
│  Results    │
└──────┬──────┘
       │ JSON Response
       ↓
┌─────────────┐
│   Frontend  │
│  Displays   │
└─────────────┘
```

## Setup & Running

### Prerequisites

- Python 3.10+
- OpenAI API key
- Required Python packages (see `requirements.txt`)

### Environment Variables

```env
OPENAI_API_KEY=your-key
PINECONE_API_KEY=your-key  # Optional
```

### Running Agents Directly

```python
from multi_agents.orchestrator import run_full_pipeline

result = run_full_pipeline(
    employee_file="path/to/employee.xlsx",
    store_requirement_file="path/to/stores.csv",
    management_store_file="path/to/managment_store.json",
    rules_file="path/to/rules.json",
    store_rules_file="path/to/store_rule.json",
)
```

### Triggering from Backend

Agents are triggered via FastAPI endpoint:

```bash
POST /generate-roster
```

Backend handles file path detection and orchestrator invocation.

### Triggering from Frontend

Frontend calls backend API:

```javascript
const response = await fetch('/generate-roster', {
    method: 'POST',
    credentials: 'include'
});
```

## Adding New Agents

### Step 1: Create Agent Module

Create `agent_N/agent.py`:

```python
from langchain.agents import create_agent
from langchain.tools import tool
from shared_state import MultiAgentState

@tool
def my_agent_tool(state: MultiAgentState):
    """Tool description"""
    # Agent logic
    return {"state_update": {...}}

def run_agentN(state: MultiAgentState):
    agent = create_agent(
        model="openai:gpt-4o-mini",
        tools=[my_agent_tool],
        system_prompt="...",
    )
    # Execute agent
    return result
```

### Step 2: Add to Shared State

Update `shared_state.py`:

```python
class MultiAgentState(AgentState):
    # ... existing fields
    agent_n_output: Annotated[Dict[str, Any], "Agent N output"]
```

### Step 3: Add Node to Orchestrator

Update `orchestrator.py`:

```python
def agent_n_node(state: MultiAgentState):
    result = run_agentN(state=state)
    return {"agent_n_output": result.get("output")}

workflow.add_node("agent_n", agent_n_node)
```

### Step 4: Add Routing Logic

```python
def route_from_agent_N(state: MultiAgentState):
    # Determine next agent
    return "agent_next"

workflow.add_conditional_edges(
    "agent_n",
    route_from_agent_N,
    {"agent_next": "agent_next"}
)
```

## RAG System Integration

The RAG system (`rag/rag.py`) enables natural language queries about rosters:

- **Vector Store**: Pinecone for roster embeddings
- **Embeddings**: OpenAI text-embedding-3-small
- **Document Processing**: Converts Excel rows to natural language
- **Retrieval**: Semantic search for relevant roster information
- **Generation**: LLM generates answers based on retrieved context

Used by backend `/chat` endpoint for admin chat interface.

## Performance Optimization

### Coverage Targets

- **Minimum**: 80% coverage
- **Target**: 90% coverage
- **Iteration Limit**: 4 iterations max

### Constraint Leniency

When stations are understaffed:
- Allow up to 10% hours overage
- Minimum 6h rest (instead of 10h)
- Allow up to 5x required staff per station

### LLM Prompt Engineering

Agent 3 system prompt emphasizes:
- Coverage maximization
- Shortage minimization
- Availability slot filling
- Flexible constraint handling

## Troubleshooting

### Agent Import Errors
- Ensure Python path includes `multi_agents` directory
- Check all dependencies installed
- Verify agent module structure

### State Update Issues
- Check state field names match exactly
- Verify state updates return dict format
- Check LangGraph state merging

### LLM Tool Calling Issues
- Verify tool descriptions are clear
- Check tool input/output formats
- Ensure system prompts guide tool usage

### Coverage Not Meeting Targets
- Check employee availability data
- Verify constraints aren't too strict
- Review Agent 3 system prompt
- Check iteration limit reached

## Future Improvements

- **Parallel Agent Execution**: Run independent agents in parallel
- **Agent Specialization**: More specialized agents for specific tasks
- **Learning from Violations**: ML model to predict violations
- **Multi-Store Optimization**: Optimize across multiple stores
- **Real-Time Updates**: WebSocket for real-time progress
- **Advanced RAG**: More sophisticated retrieval strategies
- **Agent Memory**: Long-term memory for learning patterns
