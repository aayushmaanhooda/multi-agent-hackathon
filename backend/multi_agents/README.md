# Multi-Agent Roster Generation System

This system uses LangChain v1 multi-agent patterns to generate work rosters through three specialized agents.

## Architecture

### Shared State: `MultiAgentState`
- Uses `AgentState` from LangChain v1 (not TypedDict)
- Shared across all agents for seamless data flow
- Located in `shared_state.py`

### Agent 1: Data Parser (`agent_1/agent.py`)
- **Function**: Parses and structures input files
- **Inputs**: `employee.xlsx`, store requirements, management store
- **Outputs**: Structured employee data, store requirements, management store data
- **Tool**: `run_agent1_tool` - Uses `ToolRuntime` and `InjectedToolCallId`

### Agent 2: Constraints Analyzer (`agent_2/agent.py`)
- **Function**: Analyzes rules and creates structured constraints
- **Inputs**: `rules.json`, `store_rule.json`, state from Agent 1
- **Outputs**: Structured constraints (compliance, penalty rates, break requirements)
- **Tool**: `run_agent2_tool` - Uses `ToolRuntime` and `InjectedToolCallId`

### Agent 3: Roster Generator (`agent_3/agent.py`)
- **Function**: Generates roster schedule
- **Inputs**: State from Agent 1 and Agent 2
- **Outputs**: Complete roster schedule with compliance checks
- **Tool**: `generate_roster_tool` - Uses `ToolRuntime` and `InjectedToolCallId`

### Orchestrator (`orchestrator.py`)
- **Function**: Coordinates all three agents
- Uses agents as tools in a supervisor pattern
- Manages the workflow: Agent 1 → Agent 2 → Agent 3

## Usage

### Running Individual Agents

```python
from agent_1.agent import run_agent1
from agent_2.agent import run_agent2
from agent_3.agent import run_agent3
from shared_state import MultiAgentState

# Run Agent 1
result1 = run_agent1()
state1 = result1["state_update"]

# Run Agent 2
result2 = run_agent2(state=state1)
state2 = result2["state_update"]

# Convert to MultiAgentState
multi_state = MultiAgentState(**state2)

# Run Agent 3
result3 = run_agent3(state=multi_state)
roster = result3["roster"]
```

### Running Full Pipeline via Orchestrator

```python
from orchestrator import run_full_pipeline

result = run_full_pipeline()
roster = result["roster"]
```

## Key Features

1. **Shared State**: All agents use `MultiAgentState` (AgentState-based)
2. **ToolRuntime**: Agents access state via `ToolRuntime` when called as tools
3. **InjectedToolCallId**: Proper tool call responses using `InjectedToolCallId`
4. **Command Pattern**: State updates use `Command` for proper state management
5. **LangChain v1**: Uses latest LangChain v1 patterns and APIs

## File Structure

```
multi_agents/
├── shared_state.py          # MultiAgentState definition
├── orchestrator.py          # Main orchestrator
├── agent_1/
│   ├── __init__.py
│   └── agent.py            # Data parser
├── agent_2/
│   ├── __init__.py
│   └── agent.py            # Constraints analyzer
├── agent_3/
│   ├── __init__.py
│   └── agent.py            # Roster generator
└── dataset/
    ├── employee.xlsx
    ├── rules.json
    ├── store_rule.json
    └── ...
```

## State Flow

```
Initial State (empty)
    ↓
Agent 1: Parse Data
    → employee_data
    → store_requirements
    → management_store
    → structured_data
    ↓
Agent 2: Analyze Constraints
    → constraints
    → rules_data
    → store_rules_data
    ↓
Agent 3: Generate Roster
    → roster
    → roster_metadata
    ↓
Final State (complete roster)
```
