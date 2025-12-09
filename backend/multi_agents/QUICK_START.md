# Quick Start Guide - Multi-Agent Roster System

## How to Run the Complete Pipeline

### Method 1: Direct Pipeline (Recommended)

```bash
# Navigate to the multi_agents directory
cd backend/multi_agents

# Run the complete pipeline
python run_pipeline.py
```

**OR** from backend directory:

```bash
cd backend
python -m multi_agents.run_pipeline
```

This will:
1. ✅ Load all files from `multi_agents/dataset/` folder automatically
2. ✅ Run all 5 agents in sequence
3. ✅ Generate roster Excel file
4. ✅ Generate final check report

### Method 2: Using Orchestrator

```bash
cd backend/multi_agents
python orchestrator.py
```

**OR** from backend directory:

```bash
cd backend
python -m multi_agents.orchestrator
```

### Method 3: Python Script

```python
from multi_agents.run_pipeline import main

if __name__ == "__main__":
    main()
```

## File Locations

The system **automatically picks up files** from:
```
backend/multi_agents/dataset/
├── employee.xlsx              # Employee data with availability
├── stores.csv                 # Store requirements (or store_config_data.json)
├── managment_store.json       # Management rules and shift codes
├── rules.json                 # Fair Work Act compliance rules
└── store_rule.json            # Store-specific working hours templates
```

## Output Files

After running, you'll get:

1. **Roster Excel File**: `backend/multi_agents/rag/roster.xlsx`
   - Complete 14-day schedule
   - All employee assignments
   - Store assignments
   - Manager assignments

2. **Final Check Report**: `backend/multi_agents/rag/final_roster_check_report.txt`
   - Availability coverage statistics
   - Staffing requirements check
   - Recommendations

3. **JSON Report**: `backend/multi_agents/rag/final_roster_check_report.json`
   - Machine-readable format

## What Each Agent Does

1. **Agent 1**: Loads and structures data from dataset folder
2. **Agent 2**: Analyzes rules and creates constraints
3. **Agent 3**: Generates the roster schedule
4. **Agent 4**: Validates roster (loops with Agent 3 if needed)
5. **Agent 5**: Final comprehensive check and report generation

## Example Output

```
============================================================
ROSTER GENERATION & VALIDATION PIPELINE
============================================================

[Step 1/5] Running Agent 1: Data Parser...
------------------------------------------------------------
✅ Agent 1 completed: Processed 50 employees

[Step 2/5] Running Agent 2: Constraints Analyzer...
------------------------------------------------------------
✅ Agent 2 completed: Extracted 15 compliance requirements

[Step 3-4/5] Running Agent 3-4 Loop: Generate & Validate...
------------------------------------------------------------
--- Iteration 1/3 ---
  Generating roster (iteration 1)...
  Validating roster (iteration 1)...
  ✅ Validation complete: 0 violations (0 critical)
  ✅ No violations found! Roster is compliant.

✅ Agent 3-4 loop completed after 1 iteration(s)
   Generated 450 shift assignments
   Found 0 violations
✅ Excel file created: backend/multi_agents/rag/roster.xlsx

[Step 5/5] Running Agent 5: Final Comprehensive Check...
------------------------------------------------------------
✅ Agent 5 completed: Final check status - APPROVED
   Availability Coverage: 95.5% (382/400 slots filled)
✅ Final check report saved: backend/multi_agents/rag/final_roster_check_report.txt

============================================================
PIPELINE COMPLETED WITH FINAL CHECK
============================================================
📊 Employees processed: 50
📋 Compliance rules: 15
📅 Shifts generated: 450
🔄 Iterations: 1/3
⚠️  Violations: 0
📈 Availability Coverage: 95.5%
📁 Roster file: backend/multi_agents/rag/roster.xlsx
📄 Check report: backend/multi_agents/rag/final_roster_check_report.txt
✅ Roster is fully compliant and approved!
============================================================
```

## Requirements

Make sure you have:
- Python 3.8+
- Required packages installed (see requirements.txt)
- `.env` file with OpenAI API key (for LLM agents)
- All data files in `multi_agents/dataset/` folder

## Troubleshooting

### If files are not found:
- Check that all files exist in `backend/multi_agents/dataset/`
- Verify file names match exactly (case-sensitive)

### If you get import errors:
```bash
# Option 1: Run from multi_agents directory (most reliable)
cd backend/multi_agents
python run_pipeline.py

# Option 2: Run from backend directory
cd backend
python -m multi_agents.run_pipeline

# Option 3: Add to Python path
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -m multi_agents.run_pipeline
```

### If OpenAI API errors:
- Check your `.env` file has `OPENAI_API_KEY=your_key_here`
- Verify your API key is valid and has credits

## Custom File Paths

If you want to use different file paths:

```python
from multi_agents.run_pipeline import main
from multi_agents.agent_1.agent import run_agent1
from multi_agents.agent_2.agent import run_agent2
# ... etc

# Or use orchestrator with custom paths
from multi_agents.orchestrator import run_full_pipeline

result = run_full_pipeline(
    employee_file="path/to/custom/employee.xlsx",
    store_requirement_file="path/to/custom/stores.csv",
    management_store_file="path/to/custom/managment_store.json",
    rules_file="path/to/custom/rules.json",
    store_rules_file="path/to/custom/store_rule.json"
)
```
