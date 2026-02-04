from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserInfo(BaseModel):
    email: str
    name: str
    picture: Optional[str] = None
    
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo

class Email(BaseModel):
    id: str
    thread_id: str
    sender: str
    sender_email: str
    subject: str
    snippet: str
    body: str
    date: str
    summary: Optional[str] = None
    suggested_reply: Optional[str] = None

class EmailListResponse(BaseModel):
    emails: List[Email]
    
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[str] = None
    metadata: Optional[dict] = None

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    message: str
    action: Optional[str] = None
    data: Optional[dict] = None
    
class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    thread_id: Optional[str] = None
    message_id: Optional[str] = None

class DeleteEmailRequest(BaseModel):
    email_id: str
    
class GenerateReplyRequest(BaseModel):
    email_id: str
    original_email: Email
    custom_instruction: Optional[str] = None
