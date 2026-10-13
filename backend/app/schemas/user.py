"""
QueueWise AI — User Schemas
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import UserRole


class UserBase(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=100)
    auth_identifier: str = Field(..., min_length=3, max_length=100)
    role: UserRole = UserRole.CITIZEN
    is_active: bool = True


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
