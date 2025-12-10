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

    # Define target paths - save to main dataset folder
    # api.py is in backend/app/api.py
    # we want to go to backend/multi_agents/dataset

    current_dir = os.path.dirname(os.path.abspath(__file__))  # .../backend/app
    backend_root = os.path.dirname(current_dir)  # .../backend
    dataset_path = os.path.join(backend_root, "multi_agents", "dataset")

    print(f"Saving files to: {dataset_path}")  # Debug log
    os.makedirs(dataset_path, exist_ok=True)  # Ensure dir exists

    # Delete ALL existing .xlsx and .csv files to replace them
    # This ensures we always use the latest uploaded files
    if os.path.exists(dataset_path):
        for filename in os.listdir(dataset_path):
            file_path = os.path.join(dataset_path, filename)
            if os.path.isfile(file_path):
                file_ext = os.path.splitext(filename)[1].lower()
                # Delete all .xlsx and .csv files (except JSON config files)
                if file_ext in [".xlsx", ".csv"]:
                    try:
                        os.remove(file_path)
                        print(f"Deleted old file: {filename}")
                    except Exception as e:
                        print(f"Warning: Could not delete {filename}: {e}")

    # Save files with their ORIGINAL names (not renamed)
    # This preserves the user's file names
    def sanitize_filename(filename: str) -> str:
        """Remove path components and keep only safe characters"""
        safe_name = os.path.basename(filename)
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in "._-")
        return safe_name

    emp_filename = sanitize_filename(employee_file.filename)
    store_filename = sanitize_filename(store_file.filename)

    emp_save_path = os.path.join(dataset_path, emp_filename)
    store_save_path = os.path.join(dataset_path, store_filename)

    print(f"Saving employee file as: {emp_filename} -> {emp_save_path}")
    print(f"Saving store file as: {store_filename} -> {store_save_path}")

    try:
        # Reset file pointer to beginning (in case it was read before)
        employee_file.file.seek(0)
        store_file.file.seek(0)

        with open(emp_save_path, "wb") as buffer:
            shutil.copyfileobj(employee_file.file, buffer)
        print(f"✅ Successfully saved employee file to: {emp_save_path}")

        with open(store_save_path, "wb") as buffer:
            shutil.copyfileobj(store_file.file, buffer)
        print(f"✅ Successfully saved store file to: {store_save_path}")

        # Verify files were saved
        if os.path.exists(emp_save_path):
            file_size = os.path.getsize(emp_save_path)
            print(f"✅ Verified employee file exists: {file_size} bytes")
        if os.path.exists(store_save_path):
            file_size = os.path.getsize(store_save_path)
            print(f"✅ Verified store file exists: {file_size} bytes")

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
    Generate roster using the complete multi-agent pipeline with LangGraph orchestrator.

    Uses Command and goto for dynamic routing between agents:
    - Agent 1 → Agent 2 → Agent 3 → Agent 4
    - Agent 4 loops back to Agent 3 if violations found (via Command goto)
    - Agent 4 → Agent 5 when validation complete
    - Agent 5 finishes the pipeline

    Returns roster file path, violations, and report information.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Import the orchestrator
        import sys

        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.dirname(current_dir)
        multi_agents_path = os.path.join(backend_root, "multi_agents")
        sys.path.insert(0, multi_agents_path)

        from multi_agents.orchestrator import run_full_pipeline

        # Construct paths to uploaded files (saved in main dataset folder)
        dataset_path = os.path.join(backend_root, "multi_agents", "dataset")

        # Find ANY .xlsx file as employee file and ANY .csv file as store file
        # Use the most recently modified files
        employee_file = None
        store_file = None

        if not os.path.exists(dataset_path):
            raise HTTPException(
                status_code=404,
                detail=f"Dataset folder not found: {dataset_path}. Please upload files first.",
            )

        # Find ALL .xlsx files - use most recent as employee file
        xlsx_files = []
        csv_files = []

        for filename in os.listdir(dataset_path):
            file_path = os.path.join(dataset_path, filename)
            if os.path.isfile(file_path):
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext == ".xlsx":
                    mtime = os.path.getmtime(file_path)
                    xlsx_files.append((mtime, file_path, filename))
                elif file_ext == ".csv":
                    mtime = os.path.getmtime(file_path)
                    csv_files.append((mtime, file_path, filename))

        # Use most recent .xlsx file as employee file
        if xlsx_files:
            xlsx_files.sort(
                reverse=True
            )  # Sort by modification time (most recent first)
            employee_file = xlsx_files[0][1]
            print(
                f"✅ Found employee file (.xlsx): {xlsx_files[0][2]} -> {employee_file}"
            )
        else:
            print(f"⚠️  No .xlsx file found in {dataset_path}")
            # List all files for debugging
            all_files = os.listdir(dataset_path)
            print(f"   Available files: {all_files}")

        # Use most recent .csv file as store requirements file
        if csv_files:
            csv_files.sort(
                reverse=True
            )  # Sort by modification time (most recent first)
            store_file = csv_files[0][1]
            print(f"✅ Found store file (.csv): {csv_files[0][2]} -> {store_file}")
        else:
            print(f"⚠️  No .csv file found in {dataset_path}")
            # List all files for debugging
            all_files = os.listdir(dataset_path)
            print(f"   Available files: {all_files}")

        # Verify files exist before proceeding
        if not employee_file:
            raise HTTPException(
                status_code=404,
                detail="No .xlsx file found. Please upload an employee file (.xlsx) first.",
            )
        if not store_file:
            raise HTTPException(
                status_code=404,
                detail="No .csv file found. Please upload a store requirements file (.csv) first.",
            )

        # Management store file path (always JSON) - try both locations
        management_store_file = os.path.join(dataset_path, "managment_store.json")
        if not os.path.exists(management_store_file):
            management_store_file = os.path.join(
                backend_root, "multi_agents", "dataset", "managment_store.json"
            )

        # Rules files - try both locations
        rules_file = os.path.join(dataset_path, "rules.json")
        if not os.path.exists(rules_file):
            rules_file = os.path.join(
                backend_root, "multi_agents", "dataset", "rules.json"
            )

        store_rules_file = os.path.join(dataset_path, "store_rule.json")
        if not os.path.exists(store_rules_file):
            store_rules_file = os.path.join(
                backend_root, "multi_agents", "dataset", "store_rule.json"
            )

        print(f"Using employee file: {employee_file}")
        print(f"Using store file: {store_file}")
        print(f"Using management store file: {management_store_file}")

        # Run the complete pipeline using orchestrator with uploaded file paths
        print("Starting roster generation pipeline with LangGraph orchestrator...")
        result = run_full_pipeline(
            employee_file=employee_file,
            store_requirement_file=store_file,
            management_store_file=management_store_file,
            rules_file=rules_file,
            store_rules_file=store_rules_file,
        )

        # Extract results from orchestrator
        roster = result.get("roster", {})
        final_violations = result.get("violations", [])
        iteration_count = result.get("iterations", 0)

        excel_path = roster.get("excel_path") if isinstance(roster, dict) else None

        # Get report paths from final_check_report in state
        state = result.get("state", {})
        final_check_report = state.get("final_check_report", {})

        report_path = final_check_report.get("report_path", "")
        report_json_path = report_path.replace(".txt", ".json") if report_path else ""

        # Extract just the filename for download endpoints
        excel_filename = os.path.basename(excel_path) if excel_path else None
        report_filename = os.path.basename(report_path) if report_path else None
        report_json_filename = (
            os.path.basename(report_json_path) if report_json_path else None
        )

        # Get progress messages from result
        progress_messages = result.get("progress", [])

        # Return response with file paths and data
        return {
            "status": "success",
            "message": f"Roster generated successfully after {iteration_count} iteration(s)",
            "roster_file": excel_filename,
            "report_file": report_filename,
            "report_json_file": report_json_filename,
            "violations": final_violations,
            "violation_count": len(final_violations),
            "critical_violations": sum(
                1 for v in final_violations if v.get("severity") == "critical"
            ),
            "iterations": iteration_count,
            "coverage_percent": final_check_report.get(
                "availability_coverage_percent", 0
            ),
            "filled_slots": final_check_report.get("filled_slots", 0),
            "total_slots": final_check_report.get("total_slots", 0),
            "roster_status": final_check_report.get("roster_status", "unknown"),
            "summary": final_check_report.get("summary", ""),
            "recommendations": final_check_report.get("recommendations", []),
            "progress": progress_messages,  # Include progress messages for UI
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
