from pydantic import BaseModel, EmailStr
from typing import Optional, List


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRegister(BaseModel):
    name: str  # Usually map to 'username' in UI but model calls it name
    email: EmailStr
    password: str
    role: str = "employee"  # employee or admin
    access_code: Optional[str] = None  # Required if role is admin


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None  # For maintaining conversation history


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
