from typing import Optional
from pydantic import BaseModel, EmailStr
from enum import Enum


class UserRole(str, Enum):
    admin = "admin"
    cashier = "cashier"


class RegisterRequest(BaseModel):
    store_name: str
    store_address: Optional[str] = None
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    store_id: str
    name: str
    email: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class StoreResponse(BaseModel):
    id: str
    name: str
    address: Optional[str]
    config: dict

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user: UserResponse
    store: StoreResponse
