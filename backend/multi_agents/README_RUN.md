# How to Run the Roster Generation Pipeline

## Quick Answer

**Yes!** If you run Agent 3, it will automatically run Agent 1 and Agent 2 first, then generate the Excel file in the `rag` folder.

## Three Ways to Run

### Option 1: Run Agent 3 Directly (Easiest)
```bash
cd backend/multi_agents
source ../../.multi-agent-env/bin/activate  # or your venv
python3 agent_3/agent.py
```

This will:
1. ✅ Run Agent 1 (parse employee data)
2. ✅ Run Agent 2 (analyze constraints)
3. ✅ Run Agent 3 (generate roster)
4. ✅ Create/update `rag/new.xlsx` with the roster

### Option 2: Use the Pipeline Script (Recommended)
```bash
cd backend/multi_agents
source ../../.multi-agent-env/bin/activate
python3 run_pipeline.py
```

This provides better output formatting and error handling.

### Option 3: Use the Orchestrator (Advanced)
```bash
cd backend/multi_agents
source ../../.multi-agent-env/bin/activate
python3 orchestrator.py
```

This uses LangChain's multi-agent orchestrator pattern.

## Output File

The Excel file is always saved to:
```
backend/multi_agents/rag/new.xlsx
```

**Note:** The file will be **overwritten** each time you run the pipeline. If you want to keep previous versions, modify the filename in `agent_3/agent.py`.

## File Structure

The Excel file contains:
- **Date**: Shift date (YYYY-MM-DD)
- **Day**: Day of week
- **Employee Name**: Employee's name
- **Employee ID**: Employee ID
- **Hours**: Shift duration
- **Shift Code**: Shift code (1F, 2F, 3F, S, etc.)
- **Shift Time**: Time range (e.g., "06:30 - 15:30")
- **Employment Type**: Full-Time, Part-Time, Casual
- **Status**: Scheduled, Weekend, etc.
- **Station**: Kitchen, Counter, etc.
- **Store**: Store name
- **Manager**: Manager assignment

## Example Output

```
✅ Agent 1 completed: Processed 51 employees
✅ Agent 2 completed: Extracted 7 compliance requirements
✅ Agent 3 completed: Generated 345 shift assignments
✅ Excel file created: backend/multi_agents/rag/new.xlsx
```

## Troubleshooting

1. **No Excel file created?**
   - Check that the `rag` folder exists
   - Ensure you have write permissions
   - Check the console for error messages

2. **Want to use LLM for roster generation?**
   - In `agent_3/agent.py`, change `use_llm=False` to `use_llm=True`
   - This will use GPT-4o-mini for smarter roster generation (slower but potentially better)

3. **Want to run agents individually?**
   ```python
   from agent_1.agent import run_agent1
   from agent_2.agent import run_agent2
   from agent_3.agent import run_agent3
   from shared_state import MultiAgentState
   
   # Run individually
   result1 = run_agent1()
   result2 = run_agent2(state=result1['state_update'])
   multi_state = MultiAgentState(**result2['state_update'])
   result3 = run_agent3(state=multi_state)
   ```
