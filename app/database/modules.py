from sqlmodel import SQLModel, Field
from sqlalchemy import Column, DateTime, Boolean, String, func, Integer, ForeignKey
from typing import Optional
from pydantic import EmailStr
from datetime import datetime

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(sa_column=Column(String(50), unique=True, index=True, nullable=False))
    email: EmailStr = Field(sa_column=Column(String(255), unique=True, index=True, nullable=False))
    hashed_password: str = Field(sa_column=Column(String(255), nullable=False))
    last_name: str = Field(sa_column=Column(String(50), nullable=True))
    first_name: str = Field(sa_column=Column(String(50), nullable=True))
    is_active: bool = Field(sa_column=Column(Boolean, nullable=False, server_default="0"))
    is_admin: bool = Field(sa_column=Column(Boolean, nullable=False, server_default="0"))
    totp_secret: Optional[str] = Field(sa_column=Column(String(32), nullable=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()))

class APIKey(SQLModel, table=True):
    __tablename__ = "api_keys"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(sa_column=Column(Integer, ForeignKey("users.id"), nullable=False, index=True))
    token: str = Field(sa_column=Column(String(255), unique=True, index=True, nullable=False))
    description: Optional[str] = Field(sa_column=Column(String(255), nullable=True))
    is_active: bool = Field(sa_column=Column(Boolean, nullable=False, server_default="1"))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True))
    expires_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=True))

# Permission and Role
class Permission(SQLModel, table=True):
    __tablename__ = "permissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(100), unique=True, index=True, nullable=False))
    description: Optional[str] = Field(sa_column=Column(String(255), nullable=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()))

class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(100), unique=True, index=True, nullable=False))
    description: Optional[str] = Field(sa_column=Column(String(255), nullable=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()))

# Association Tables for Many-to-Many Relationships

# User-Permission direct assignment
class UserPermission(SQLModel, table=True):
    __tablename__ = "user_permissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(sa_column=Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    permission_id: int = Field(sa_column=Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))

# User-Role assignment
class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(sa_column=Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    role_id: int = Field(sa_column=Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))

# APIKey-Permission direct assignment
class APIKeyPermission(SQLModel, table=True):
    __tablename__ = "api_key_permissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    api_key_id: int = Field(sa_column=Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, index=True))
    permission_id: int = Field(sa_column=Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))

# APIKey-Role assignment
class APIKeyRole(SQLModel, table=True):
    __tablename__ = "api_key_roles"

    id: Optional[int] = Field(default=None, primary_key=True)
    api_key_id: int = Field(sa_column=Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False, index=True))
    role_id: int = Field(sa_column=Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))

# Role-Permission assignment (roles contain permissions)
class RolePermission(SQLModel, table=True):
    __tablename__ = "role_permissions"

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: int = Field(sa_column=Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True))
    permission_id: int = Field(sa_column=Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now()))

# Event catalog (what happened)
class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(sa_column=Column(String(100), unique=True, index=True, nullable=False))
    description: Optional[str] = Field(sa_column=Column(String(255), nullable=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True))
    updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()))

# Per-user event logs
class UserEventLog(SQLModel, table=True):
    __tablename__ = "user_event_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(sa_column=Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True))
    event_id: int = Field(sa_column=Column(Integer, ForeignKey("events.id", ondelete="RESTRICT"), nullable=False, index=True))
    ip_address: Optional[str] = Field(sa_column=Column(String(45), nullable=True))
    user_agent: Optional[str] = Field(sa_column=Column(String(255), nullable=True))
    message: Optional[str] = Field(sa_column=Column(String(1024), nullable=True))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True))