import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


TaskStatus = Literal["todo", "in_progress", "done"]
TaskPriority = Literal["low", "medium", "high"]


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type (always 'bearer')")


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="User email (unique)")
    full_name: str | None = Field(None, description="Full name")
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")


class UserUpdate(BaseModel):
    full_name: str | None = Field(None, description="Full name")
    is_active: bool | None = Field(None, description="Whether user is active")


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class TaskPublic(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    description: str | None = None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str | None = Field(None, description="Task description")
    status: TaskStatus = Field("todo", description="Task status")
    priority: TaskPriority = Field("medium", description="Task priority")
    due_date: datetime | None = Field(None, description="Optional due date (ISO8601)")


class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200, description="Task title")
    description: str | None = Field(None, description="Task description")
    status: TaskStatus | None = Field(None, description="Task status")
    priority: TaskPriority | None = Field(None, description="Task priority")
    due_date: datetime | None = Field(None, description="Optional due date (ISO8601)")
