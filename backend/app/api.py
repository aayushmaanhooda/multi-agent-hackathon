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
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")

    try:
        # Invoke Agent 1
        result = run_agent1()

        # Check result status
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("error_message", "Agent execution failed"),
            )

        return result

    except Exception as e:
        print(f"Agent execution error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to generate roster: {str(e)}"
        )


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
