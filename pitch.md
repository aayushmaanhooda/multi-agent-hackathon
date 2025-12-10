# ROSTER AI - 3 Minute Pitch

## The Problem (30 seconds)

Creating employee schedules for restaurants like McDonald's is incredibly complex. Managers spend hours every week trying to:
- Match employee availability with shift requirements
- Ensure all stations are properly staffed
- Comply with labor laws and company policies
- Maximize coverage while minimizing costs
- Handle last-minute changes and conflicts

This manual process is time-consuming, error-prone, and often results in understaffed shifts or unhappy employees.

## The Solution (45 seconds)

**ROSTER AI** is an intelligent multi-agent system that automates roster generation using cutting-edge AI technology.

Our system uses **5 specialized AI agents** working together through a LangGraph orchestration framework:

1. **Agent 1 - Data Parser**: Extracts and structures employee availability and store requirements
2. **Agent 2 - Constraints Analyzer**: Analyzes labor laws, shift limits, and business rules
3. **Agent 3 - Roster Generator**: Uses LLM intelligence to create optimized schedules targeting 80-90% coverage
4. **Agent 4 - Validator**: Checks for violations and compliance issues
5. **Agent 5 - Final Check**: Generates comprehensive reports with coverage metrics

Each agent specializes in one aspect of roster generation, ensuring accuracy and optimization.

## The Flow (60 seconds)

Here's how it works:

**Step 1: Upload Data**
- Manager uploads employee availability file (.xlsx) and store requirements (.csv)
- Files are automatically processed and structured

**Step 2: Multi-Agent Pipeline Execution**
- **Agent 1** parses all data into a structured format
- **Agent 2** extracts and analyzes all constraints and rules
- **Agent 3** generates an intelligent roster schedule using LLM reasoning
- **Agent 4** validates the roster for any violations
- If violations are found, the system automatically loops back to Agent 3 to refine the schedule (up to 4 iterations)
- **Agent 5** performs final comprehensive check and generates detailed reports

**Step 3: Results & Optimization**
- System returns a complete roster with:
  - 80-90% employee coverage (maximizing shift assignments)
  - Zero or minimal shortages
  - Full compliance with all rules
  - Detailed Excel export ready for use
  - Comprehensive validation reports

The entire process takes just minutes, compared to hours of manual work.

## Key Features (30 seconds)

- **Intelligent Optimization**: LLM-powered scheduling that understands context and constraints
- **High Coverage**: Targets 80-90% coverage, ensuring maximum employee utilization
- **Automatic Validation**: Self-correcting system that iteratively improves until optimal
- **Compliance First**: Built-in validation for labor laws, shift limits, and business rules
- **User-Friendly**: Simple file upload interface with real-time progress tracking
- **RAG-Powered Chat**: Natural language queries about schedules ("Who's working Monday afternoon?")

## Technology Stack (15 seconds)

- **Frontend**: React + Vite for modern, responsive UI
- **Backend**: FastAPI with SQLite for fast, reliable API
- **AI Layer**: LangChain + LangGraph for multi-agent orchestration
- **LLM**: OpenAI GPT-4o-mini for intelligent decision-making
- **Vector Store**: Pinecone for RAG-powered roster queries

## The Value Proposition (30 seconds)

**ROSTER AI** transforms a 4-6 hour weekly task into a 2-minute automated process.

**For Managers:**
- Save 20+ hours per month
- Eliminate scheduling errors
- Ensure optimal staffing levels
- Focus on business operations instead of spreadsheets

**For Businesses:**
- Reduce labor costs through optimization
- Improve employee satisfaction with fair schedules
- Ensure compliance automatically
- Scale to multiple locations easily

**For Employees:**
- Fair, optimized schedules
- Better work-life balance
- Transparent availability matching

## Demo Flow

1. Upload employee and store files
2. Click "Generate Roster"
3. Watch 5 agents work in real-time
4. Receive optimized roster in minutes
5. Download Excel file and reports

## Closing (10 seconds)

ROSTER AI isn't just automation—it's intelligent orchestration. By combining specialized AI agents with LLM reasoning, we've created a system that doesn't just follow rules, but optimizes for the best possible outcome.

**Ready to revolutionize workforce scheduling? Let's talk.**

---

*Built with ❤️ using LangChain, LangGraph, and OpenAI*
