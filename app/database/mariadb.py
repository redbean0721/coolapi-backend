from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
import os

DATABASE_URL = os.getenv("MARIADB_URL")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,         # 啟用SQL查詢日誌
    future=True,        # 使用SQLAlchemy 2.0風格
    pool_size=10,       # 連接池的大小
    max_overflow=20,    # 超出連接池大小後允許的最大連接數
    pool_pre_ping=True, # 啟用連接池的預檢測功能
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False, # 提交後不過期實例
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    """初始化資料庫，創建所有表"""
    # 需要先導入所有模型，確保它們被註冊到 SQLModel.metadata
    from app.database.modules import (
        User, APIKey, Permission, Role,
        UserPermission, UserRole, APIKeyPermission, APIKeyRole, RolePermission
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)