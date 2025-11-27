from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from .mariadb import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)
    totp_secret = Column(String(32), nullable=True) # TOTP key
    email_2fa_enabled = Column(Boolean, default=False)

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)    # 外鍵關聯到 roles 表的 id

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    role = relationship("Role", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user")

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("User", back_populates="role")
    api_keys = relationship("APIKey", back_populates="role")

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # e.g. "api.read", "api.write", "api.delete"

class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uix_role_permission"),)

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"))
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"))

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission")

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    key = Column(String(512), unique=True, nullable=False)  # jwt token
    description = Column(String(255), nullable=True)    # 使用者自訂
    is_active = Column(Boolean, default=True)
    expired_at = Column(DateTime(timezone=True), nullable=True) # 為空表示永不過期

    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)    # 外鍵關聯到 roles 表的 id

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="api_keys")
    role = relationship("Role", back_populates="api_keys")
    permissions = relationship("APIKeyPermission", back_populates="api_key", cascade="all, delete-orphan")

class APIKeyPermission(Base):
    __tablename__ = "api_key_permissions"
    __table_args__ = (UniqueConstraint("api_key_id", "permission_id", name="uix_apikey_permission"),)

    id = Column(Integer, primary_key=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id", ondelete="CASCADE"))
    permission_id = Column(Integer, ForeignKey("permissions.id", ondelete="CASCADE"))

    api_key = relationship("APIKey", back_populates="permissions")
    permission = relationship("Permission")