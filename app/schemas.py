from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[int] = None

class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    resolved: bool
    cached: bool = False

class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)    

class DocumentOut(BaseModel):
    id: int
    filename: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentUploadOut(BaseModel):
    id: int
    filename: str
    chunke: int
    
        
                    