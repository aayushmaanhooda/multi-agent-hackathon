# Backend - FastAPI Multi-Agent Roster System

## Overview

FastAPI-based backend that serves as the API layer and orchestrator for a multi-agent roster generation system. The backend exposes REST endpoints for file uploads, roster generation, and RAG-powered chat, while coordinating LangChain agents through LangGraph.

## Architecture

```
backend/
├── app/
│   ├── api.py           # Main FastAPI routes and endpoints
│   ├── auth.py          # JWT authentication utilities
│   ├── config.py        # Configuration and database setup
│   ├── db.py            # Database connection and session management
│   ├── dependencies.py  # FastAPI dependencies (auth, DB)
│   ├── models.py        # SQLAlchemy database models
│   └── schemas.py       # Pydantic request/response schemas
├── multi_agents/        # Multi-agent system (see multi_agents/README.md)
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── scripts/
    └── iterate_roster_generation.py  # Iterative roster generation script
```

## Tech Stack

- **FastAPI** - Modern async web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Database (via psycopg2-binary)
- **JWT** - Authentication (python-jose, bcrypt)
- **LangChain/LangGraph** - Multi-agent orchestration
- **Pandas** - Data processing
- **OpenPyXL** - Excel file handling

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL database
- OpenAI API key (for LLM agents)

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the backend root:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/roster_db

# JWT Authentication
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI (for LangChain agents)
OPENAI_API_KEY=your-openai-api-key

# Optional: Pinecone (for RAG vector store)
PINECONE_API_KEY=your-pinecone-key
PINECONE_ENVIRONMENT=your-pinecone-env
PINECONE_INDEX_NAME=roster-index

```

## Running the Server

### Development Mode

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn app.api:app --host localhost --port 8000 --reload
```

Server runs on `http://localhost:8000`

### Production Mode

```bash
uvicorn app.api:app --host 0.0.0.0 --port 8000 --workers 4
```

## Database Setup

The backend uses PostgreSQL with SQLAlchemy ORM:

### Models

- **User**: Stores user accounts (email, password hash, role)
- Authentication handled via JWT tokens
- Session management via HTTP-only cookies

### Database Initialization

Database tables are created automatically on first run via SQLAlchemy's `create_all()`.

## API Routes

### Authentication

- `POST /register` - User registration
  - Body: `{name, email, password, role, access_code?}`
  - Returns: User data and access token

- `POST /login` - User login
  - Body: `{email, password}`
  - Returns: Access token (stored in HTTP-only cookie)

- `POST /logout` - User logout
  - Clears session cookie

- `GET /dashboard` - Get current user
  - Protected route
  - Returns: Current user data

### Roster Management

- `POST /upload-roster` - Upload employee and store files
  - **Admin only**
  - FormData: `employee_file` (.xlsx), `store_file` (.csv)
  - Saves files to `backend/multi_agents/dataset/`
  - Deletes old .xlsx/.csv files before saving

- `POST /generate-roster` - Generate roster via multi-agent pipeline
  - **Admin only**
  - Triggers full LangGraph workflow:
    - Agent 1 → Agent 2 → Agent 3 → Agent 4 → (loop) → Agent 5
  - Returns: `{roster_file, report_file, violations, coverage_percent, progress, ...}`

- `GET /get-roster` - Get current roster status
  - Returns: Coverage metrics, violations, roster status

- `GET /download-roster/{filename}` - Download Excel roster
  - **Admin only**
  - Serves file from `backend/multi_agents/rag/`

- `GET /download-report/{filename}` - Download report (txt/json)
  - **Admin only**
  - Serves file from `backend/multi_agents/rag/`

### RAG Chat

- `POST /chat` - RAG-powered chat interface
  - Body: `{message, conversation_id?}`
  - Returns: AI response based on roster data
  - Uses LangChain RAG agent with vector store

## Multi-Agent Integration

### Orchestration Flow

The backend acts as the entry point for the multi-agent system:

1. **File Upload** (`/upload-roster`):
   - Receives employee (.xlsx) and store (.csv) files
   - Saves to `backend/multi_agents/dataset/`
   - Files are automatically detected by agents

2. **Roster Generation** (`/generate-roster`):
   - Imports `orchestrator.run_full_pipeline()`
   - Passes file paths to orchestrator
   - Orchestrator creates LangGraph state machine
   - Agents execute in sequence with conditional routing
   - Returns final roster and metrics

3. **Agent Communication**:
   - Agents communicate via `MultiAgentState` (shared state)
   - LangGraph handles routing between agents
   - Backend receives progress updates from orchestrator
   - Progress messages returned to frontend

### Agent Workflow

```
Frontend Request
    ↓
POST /generate-roster
    ↓
orchestrator.run_full_pipeline()
    ↓
LangGraph State Machine
    ├── Agent 1: Parse data
    ├── Agent 2: Analyze constraints
    ├── Agent 3: Generate roster
    ├── Agent 4: Validate roster
    │   └── Loop back to Agent 3 if violations (max 4 iterations)
    └── Agent 5: Final check & report
    ↓
Return results to frontend
```

## File Handling

### Uploaded Files

- **Location**: `backend/multi_agents/dataset/`
- **Employee Files**: Any `.xlsx` file (most recent used)
- **Store Files**: Any `.csv` file (most recent used)
- **Config Files**: `managment_store.json`, `rules.json`, `store_rule.json`

### Generated Files

- **Location**: `backend/multi_agents/rag/`
- **Roster**: `roster.xlsx` - Generated schedule
- **Reports**: `final_roster_check_report.txt/json` - Validation reports

## Authentication & Authorization

### JWT Token Flow

1. User logs in via `/login`
2. Backend validates credentials
3. JWT token created with user info
4. Token stored in HTTP-only cookie
5. Subsequent requests include cookie automatically
6. `get_current_user` dependency validates token

### Role-Based Access

- **Admin**: Full access to roster generation endpoints
- **Regular Users**: Limited to dashboard

Protected routes use `Depends(get_current_user)` and check `current_user.role`.

## CORS Configuration

CORS middleware configured to allow frontend:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For production, update `allow_origins` with actual frontend domain.

## Error Handling

- HTTP exceptions for client errors (400, 403, 404, 500)
- Detailed error messages in response
- Exception logging for debugging
- Graceful handling of missing files or agent failures

## RAG System Integration

The backend initializes a RAG (Retrieval-Augmented Generation) system:

- **Vector Store**: Pinecone (optional, can use local)
- **Embeddings**: OpenAI embeddings
- **Agent**: LangChain agent with RAG tools

RAG system loads roster data from Excel files and enables natural language queries about the roster.

## Iterative Roster Generation

A utility script (`scripts/iterate_roster_generation.py`) can be used to iteratively generate rosters until coverage targets are met:

```bash
python backend/scripts/iterate_roster_generation.py
```

This script:
- Calls `/generate-roster` repeatedly
- Monitors coverage percentage (target: 80-90%)
- Tracks shortages
- Stops when targets are met or max iterations reached

## Database Models

### User Model

```python
class User(Base):
    id: int
    name: str
    email: str (unique)
    password_hash: str
    role: str  # "admin" or "user"
    created_at: datetime
```

## API Response Formats

### Success Response

```json
{
    "status": "success",
    "message": "...",
    "data": {...}
}
```

### Error Response

```json
{
    "detail": "Error message here"
}
```

### Roster Generation Response

```json
{
    "status": "success",
    "message": "Roster generated successfully after 2 iteration(s)",
    "roster_file": "roster.xlsx",
    "report_file": "final_roster_check_report.txt",
    "violations": [...],
    "violation_count": 5,
    "critical_violations": 2,
    "iterations": 2,
    "coverage_percent": 85.5,
    "filled_slots": 342,
    "total_slots": 400,
    "roster_status": "compliant",
    "progress": ["Agent 1: ...", " Agent 1 completed: ..."]
}
```

## Testing

### Manual Testing

1. Start backend: `python main.py`
2. Test endpoints via curl or Postman
3. Check logs for agent progress
4. Verify file uploads in `multi_agents/dataset/`
5. Check generated files in `multi_agents/rag/`

### Integration Testing

Test full workflow:

1. Register admin user
2. Login to get token
3. Upload files via `/upload-roster`
4. Generate roster via `/generate-roster`
5. Check coverage and violations
6. Download roster and reports

## Production Considerations

- Use environment variables for all secrets
- Configure proper CORS origins
- Set up database connection pooling
- Use production-grade ASGI server (Gunicorn + Uvicorn workers)
- Enable HTTPS
- Set up logging and monitoring
- Configure rate limiting
- Use Redis for session storage (if scaling)

## Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check `DATABASE_URL` format
- Ensure database exists

### Agent Import Errors
- Verify `multi_agents` directory structure
- Check Python path includes backend root
- Ensure all agent dependencies installed

### File Upload Issues
- Check directory permissions for `multi_agents/dataset/`
- Verify file extensions (.xlsx, .csv)
- Check file size limits

### RAG System Errors
- Verify OpenAI API key is set
- Check Pinecone credentials (if using)
- Ensure roster files exist before chat queries
