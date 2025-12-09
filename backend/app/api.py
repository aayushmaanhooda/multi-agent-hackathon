from fastapi import FastAPI, Depends, HTTPException, status, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import timedelta
import shutil
import os
from .config import lifespan
from .db import get_db
from .models import User
from .schemas import UserRegister, UserLogin, ChatRequest, ChatResponse
from .auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .dependencies import get_current_user
import sys
import uuid
from typing import Dict, List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from multi_agents.agent_1.agent import run_agent1
except ImportError:
    # Fallback or different structure
    print("Warning: Could not import run_agent1")

# Import RAG system
try:
    from multi_agents.rag.rag import (
        setup_rag_system,
        create_rag_agent,
        initialize_vector_store,
    )

    RAG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import RAG system: {e}")
    setup_rag_system = None
    create_rag_agent = None
    initialize_vector_store = None
    RAG_AVAILABLE = False

# Global RAG agent instance (initialized on first use)
_rag_agent = None
_vector_store = None

# In-memory conversation history storage
# Format: {conversation_id: [{"role": "user", "content": "..."}, ...]}
conversation_history: Dict[str, List[Dict[str, str]]] = {}


def get_or_create_rag_agent():
    """Initialize RAG agent if not already initialized."""
    global _rag_agent, _vector_store

    if not RAG_AVAILABLE:
        raise RuntimeError(
            "RAG system is not available. Please check that all dependencies are installed and the RAG module is properly configured."
        )

    if _rag_agent is None:
        try:
            # Get the path to the Excel file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            backend_root = os.path.dirname(current_dir)
            excel_path = os.path.join(backend_root, "multi_agents", "rag", "new.xlsx")
            output_path = os.path.join(
                backend_root, "multi_agents", "rag", "roster_doc.txt"
            )

            # Check if files exist
            if not os.path.exists(excel_path):
                raise FileNotFoundError(f"Excel file not found: {excel_path}")

            # Setup RAG system
            _vector_store, _rag_agent = setup_rag_system(
                excel_path=excel_path, output_path=output_path, populate_store=True
            )
            print("RAG system initialized successfully")
        except Exception as e:
            print(f"Error initializing RAG system: {e}")
            raise

    return _rag_agent


app = FastAPI(lifespan=lifespan)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Server is running"}


@app.get("/health")
def db_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database connection failed: {str(e)}"
        )


@app.post("/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    # 1. Check if email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. If Admin, verify access code
    if user.role == "admin":
        if user.access_code != "rrr":  # Hardcoded for now
            raise HTTPException(status_code=403, detail="Invalid Admin Access Code")

    # 3. Hash password
    hashed_pwd = get_password_hash(user.password)

    # 4. Create user
    new_user = User(
        name=user.name, email=user.email, password=hashed_pwd, role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully", "id": str(new_user.id)}


@app.post("/login")
def login(user: UserLogin, response: Response, db: Session = Depends(get_db)):
    try:
        # 1. Find user
        db_user = db.query(User).filter(User.email == user.email).first()
        if not db_user:
            print(f"Login attempt failed: User not found for email: {user.email}")
            raise HTTPException(
                status_code=400, detail="Invalid credentials"
            )  # Generic error

        # 2. Verify Password
        password_valid = verify_password(user.password, db_user.password)
        if not password_valid:
            print(f"Login attempt failed: Invalid password for email: {user.email}")
            raise HTTPException(status_code=400, detail="Invalid credentials")

        print(f"Login successful for user: {user.email}")

        # 3. Create Access Token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": db_user.email}, expires_delta=access_token_expires
        )

        # 4. Set HTTP-only Cookie
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            # secure=True, # Uncomment in production with HTTPS
            samesite="lax",  # Needed for localhost cross-port
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

        # 5. Return success (No token in body)
        return {
            "message": "Login successful",
            "user": {
                "id": str(db_user.id),
                "name": db_user.name,
                "email": db_user.email,
                "role": db_user.role,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@app.post("/logout")
def logout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logged out successfully"}


@app.get("/dashboard")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
    }


@app.post("/upload-roster")
def upload_roster(
    employee_file: UploadFile = File(...),
    store_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    # Security check: Ensure user is admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    allowed_extensions = {".xlsx", ".csv"}

    # helper to check extension
    def validate_file(filename: str):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type for {filename}. Allowed: {allowed_extensions}",
            )
        return ext

    emp_ext = validate_file(employee_file.filename)
    store_ext = validate_file(store_file.filename)

    # Define target paths
    # api.py is in backend/app/api.py
    # we want to go to backend/multi_agents/agent_1/dataset

    current_dir = os.path.dirname(os.path.abspath(__file__))  # .../backend/app
    backend_root = os.path.dirname(current_dir)  # .../backend
    dataset_path = os.path.join(backend_root, "multi_agents", "agent_1", "dataset")

    print(f"Saving files to: {dataset_path}")  # Debug log
    os.makedirs(dataset_path, exist_ok=True)  # Ensure dir exists

    # Save Employee File
    # Overwrite 'employee.xlsx' (or csv) logic:
    # Actually, the agent logic looks for specific filenames or assumes structure?
    # agent.ipynb just loaded "employee.xlsx".
    # We should strictly enforce saving as "employee.xlsx" if possible, or handle variable names.
    # The user said "dataset folder in backend".
    # To keep it simple and consistent with Agent 1, we should save as standard names.

    emp_save_path = os.path.join(
        dataset_path, "employee" + emp_ext
    )  # e.g. employee.xlsx

    # Store File
    store_save_path = os.path.join(
        dataset_path, "stores" + store_ext
    )  # e.g. stores.csv

    try:
        with open(emp_save_path, "wb") as buffer:
            shutil.copyfileobj(employee_file.file, buffer)

        with open(store_save_path, "wb") as buffer:
            shutil.copyfileobj(store_file.file, buffer)

    except Exception as e:
        print(f"Error saving files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save files: {str(e)}")

    return {
        "message": "Roster files uploaded and saved successfully",
        "files": [emp_save_path, store_save_path],
    }


@app.post("/generate-roster")
def generate_roster(current_user: User = Depends(get_current_user)):
    """
    Generate roster using the complete multi-agent pipeline.
    Returns roster file path, violations, and report information.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Import the full pipeline components
        import sys

        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.dirname(current_dir)
        multi_agents_path = os.path.join(backend_root, "multi_agents")
        sys.path.insert(0, multi_agents_path)

        from multi_agents.agent_1.agent import run_agent1
        from multi_agents.agent_2.agent import run_agent2
        from multi_agents.agent_3.agent import run_agent3
        from multi_agents.agent_4.agent import run_agent4
        from multi_agents.agent_5.agent import run_agent5
        from multi_agents.shared_state import MultiAgentState

        # Helper functions
        def _update_state(state, key, value):
            if isinstance(state, dict):
                state[key] = value
            else:
                setattr(state, key, value)

        def _get_state_value(state, key, default=None):
            if isinstance(state, dict):
                return state.get(key, default)
            else:
                return getattr(state, key, default)

        # Run the complete pipeline
        print("Starting roster generation pipeline...")

        # Step 1: Agent 1
        result1 = run_agent1()
        state1 = result1.get("state_update", {})
        employee_count = result1.get("employee_count", 0)

        if employee_count == 0:
            raise HTTPException(
                status_code=400,
                detail="No employees found. Please upload employee data first.",
            )

        # Step 2: Agent 2
        result2 = run_agent2(state=state1)
        state2 = result2.get("state_update", {})
        constraints = result2.get("constraints", {})

        # Step 3-4: Agent 3-4 Loop
        multi_state = MultiAgentState(
            employee_data=state2.get("employee_data", []),
            store_requirements=state2.get("store_requirements", {}),
            management_store=state2.get("management_store", {}),
            structured_data=state2.get("structured_data", {}),
            constraints=state2.get("constraints", {}),
            rules_data=state2.get("rules_data", {}),
            store_rules_data=state2.get("store_rules_data", {}),
            roster={},
            roster_metadata={},
            violations=[],
            iteration_count=0,
            validation_complete=False,
            final_check_report={},
            final_check_complete=False,
            messages=state2.get("messages", []),
        )

        max_iterations = 7
        iteration = 0
        accumulated_violations = []

        while iteration < max_iterations:
            iteration += 1
            print(f"--- Iteration {iteration}/{max_iterations} ---")

            # Generate roster
            _update_state(multi_state, "violations", accumulated_violations)
            result3 = run_agent3(state=multi_state, use_llm=False)
            updated_state = result3.get("state", {})
            roster_data = result3.get("roster", {})

            roster_to_set = (
                roster_data
                if roster_data
                else (
                    updated_state.get("roster", {})
                    if isinstance(updated_state, dict)
                    else getattr(updated_state, "roster", {})
                )
            )
            _update_state(multi_state, "roster", roster_to_set)

            # Validate roster
            result4 = run_agent4(state=multi_state)
            new_violations = result4.get("violations", [])
            violation_count = result4.get("violation_count", 0)
            critical_count = result4.get("critical_count", 0)

            # Accumulate violations
            violation_keys = set()
            for v in accumulated_violations:
                key = (
                    str(v.get("employee", "")).lower().strip(),
                    str(v.get("date", "")).strip(),
                    str(v.get("type", "")).strip(),
                    str(v.get("shift_code", "")).upper().strip(),
                )
                violation_keys.add(key)

            for v in new_violations:
                key = (
                    str(v.get("employee", "")).lower().strip(),
                    str(v.get("date", "")).strip(),
                    str(v.get("type", "")).strip(),
                    str(v.get("shift_code", "")).upper().strip(),
                )
                if key not in violation_keys:
                    accumulated_violations.append(v)
                    violation_keys.add(key)

            _update_state(multi_state, "violations", new_violations)
            _update_state(multi_state, "iteration_count", iteration)
            _update_state(
                multi_state, "validation_complete", result4.get("is_compliant", False)
            )

            # Early stopping check
            if violation_count == 0:
                break

            shifts = (
                roster_to_set.get("shifts", [])
                if isinstance(roster_to_set, dict)
                else getattr(roster_to_set, "shifts", [])
            )
            current_coverage = (len(shifts) / 345.0 * 100) if len(shifts) > 0 else 0
            if iteration >= 3 and current_coverage >= 90.0 and violation_count <= 10:
                break

        # Step 5: Agent 5 - Final Check
        result5 = run_agent5(state=multi_state)

        # Get final results
        roster = _get_state_value(multi_state, "roster", {})
        final_violations = _get_state_value(multi_state, "violations", [])

        excel_path = (
            roster.get("excel_path")
            if isinstance(roster, dict)
            else getattr(roster, "excel_path", None)
        )

        report_path = result5.get("report_path", "")
        report_json_path = report_path.replace(".txt", ".json") if report_path else ""

        # Extract just the filename for download endpoints
        excel_filename = os.path.basename(excel_path) if excel_path else None
        report_filename = os.path.basename(report_path) if report_path else None
        report_json_filename = (
            os.path.basename(report_json_path) if report_json_path else None
        )

        # Return response with file paths and data
        # Use result5 directly since run_agent5 returns the report data, not state
        return {
            "status": "success",
            "message": f"Roster generated successfully after {iteration} iteration(s)",
            "roster_file": excel_filename,
            "report_file": report_filename,
            "report_json_file": report_json_filename,
            "violations": final_violations,
            "violation_count": len(final_violations),
            "critical_violations": sum(
                1 for v in final_violations if v.get("severity") == "critical"
            ),
            "iterations": iteration,
            "coverage_percent": result5.get("availability_coverage_percent", 0),
            "filled_slots": result5.get("filled_slots", 0),
            "total_slots": result5.get("total_slots", 0),
            "roster_status": result5.get("roster_status", "unknown"),
            "summary": result5.get("summary", ""),
            "recommendations": result5.get("recommendations", []),
        }

    except Exception as e:
        print(f"Roster generation error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to generate roster: {str(e)}"
        )


@app.get("/download-roster/{filename}")
def download_roster(filename: str, current_user: User = Depends(get_current_user)):
    """
    Download the generated roster Excel file.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.dirname(current_dir)
        roster_path = os.path.join(backend_root, "multi_agents", "rag", filename)

        if not os.path.exists(roster_path):
            raise HTTPException(status_code=404, detail="Roster file not found")

        from fastapi.responses import FileResponse

        return FileResponse(
            roster_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download file: {str(e)}"
        )


@app.get("/download-report/{filename}")
def download_report(filename: str, current_user: User = Depends(get_current_user)):
    """
    Download the final check report file (text or JSON).
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.dirname(current_dir)
        report_path = os.path.join(backend_root, "multi_agents", "rag", filename)

        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Report file not found")

        from fastapi.responses import FileResponse

        # Determine media type
        if filename.endswith(".json"):
            media_type = "application/json"
        else:
            media_type = "text/plain"

        return FileResponse(
            report_path,
            media_type=media_type,
            filename=filename,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to download file: {str(e)}"
        )


@app.get("/get-roster")
def get_roster(current_user: User = Depends(get_current_user)):
    """
    Get current roster information if it exists.
    Returns roster data from the final check report if available.
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.dirname(current_dir)
        rag_dir = os.path.join(backend_root, "multi_agents", "rag")

        roster_path = os.path.join(rag_dir, "roster.xlsx")
        report_json_path = os.path.join(rag_dir, "final_roster_check_report.json")

        # Check if roster exists
        roster_exists = os.path.exists(roster_path)

        if not roster_exists:
            return {"exists": False, "message": "Roster not yet set"}

        # Try to load report data if available
        report_data = {}
        if os.path.exists(report_json_path):
            try:
                with open(report_json_path, "r") as f:
                    import json

                    report_data = json.load(f)
            except Exception as e:
                print(f"Error reading report JSON: {e}")

        # Get roster filename
        roster_filename = os.path.basename(roster_path)
        report_filename = (
            os.path.basename(report_json_path)
            if os.path.exists(report_json_path)
            else None
        )
        report_txt_filename = (
            "final_roster_check_report.txt"
            if os.path.exists(os.path.join(rag_dir, "final_roster_check_report.txt"))
            else None
        )

        return {
            "exists": True,
            "roster_file": roster_filename,
            "report_file": report_txt_filename,
            "report_json_file": report_filename,
            "coverage_percent": report_data.get("availability_coverage_percent", 0),
            "filled_slots": report_data.get("filled_slots", 0),
            "total_slots": report_data.get("total_availability_slots", 0),
            "roster_status": report_data.get("roster_status", "unknown"),
            "summary": report_data.get("summary", ""),
            "recommendations": report_data.get("recommendations", []),
            "violation_count": len(report_data.get("availability_checks", []))
            - report_data.get("filled_slots", 0),
            "critical_violations": 0,  # Would need to calculate from violations
        }
    except Exception as e:
        print(f"Error getting roster: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to get roster: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
def chat(chat_request: ChatRequest, current_user: User = Depends(get_current_user)):
    """
    Chat endpoint for RAG-based roster queries.
    Supports conversation history for long conversations.
    """
    try:
        # Initialize RAG agent if needed
        agent = get_or_create_rag_agent()

        # Get or create conversation ID
        conversation_id = chat_request.conversation_id
        if not conversation_id or conversation_id not in conversation_history:
            conversation_id = str(uuid.uuid4())
            conversation_history[conversation_id] = []

        # Add user message to history
        conversation_history[conversation_id].append(
            {"role": "user", "content": chat_request.message}
        )

        # Build messages for agent (convert history to LangChain format)
        messages = []
        for msg in conversation_history[conversation_id]:
            if msg["role"] == "user":
                messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                messages.append({"role": "assistant", "content": msg["content"]})

        # Get response from agent using invoke for more reliable response
        try:
            result = agent.invoke({"messages": messages})

            # Extract response content from result
            if hasattr(result, "messages") and result.messages:
                last_msg = result.messages[-1]
                if hasattr(last_msg, "content"):
                    response_content = last_msg.content
                elif isinstance(last_msg, dict) and "content" in last_msg:
                    response_content = last_msg["content"]
                else:
                    response_content = str(last_msg)
            elif hasattr(result, "output"):
                response_content = result.output
            elif isinstance(result, dict):
                # Try to extract from dict
                if "messages" in result and result["messages"]:
                    last_msg = result["messages"][-1]
                    if isinstance(last_msg, dict) and "content" in last_msg:
                        response_content = last_msg["content"]
                    elif hasattr(last_msg, "content"):
                        response_content = last_msg.content
                    else:
                        response_content = str(last_msg)
                elif "output" in result:
                    response_content = result["output"]
                else:
                    response_content = str(result)
            else:
                response_content = str(result)
        except Exception as e:
            print(f"Error invoking agent: {e}")
            # Fallback to stream method
            response_content = ""
            try:
                for event in agent.stream(
                    {"messages": messages},
                    stream_mode="values",
                ):
                    if "messages" in event and event["messages"]:
                        last_message = event["messages"][-1]
                        if hasattr(last_message, "content"):
                            response_content = last_message.content
                        elif (
                            isinstance(last_message, dict) and "content" in last_message
                        ):
                            response_content = last_message["content"]
            except Exception as stream_error:
                print(f"Error streaming agent: {stream_error}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get response from agent: {str(stream_error)}",
                )

        if not response_content:
            raise HTTPException(status_code=500, detail="Agent returned empty response")

        # Add assistant response to history
        conversation_history[conversation_id].append(
            {"role": "assistant", "content": response_content}
        )

        # Limit conversation history to last 50 messages to prevent memory issues
        if len(conversation_history[conversation_id]) > 50:
            conversation_history[conversation_id] = conversation_history[
                conversation_id
            ][-50:]

        return ChatResponse(response=response_content, conversation_id=conversation_id)

    except RuntimeError as e:
        # Handle RAG system not available
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to process chat message: {str(e)}"
        )
