from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

# 如果使用 SQLModel (推荐) 或 SQLAlchemy，这里定义 Table
# 这里为了演示 RAG 核心，我们只定义通用的业务实体模型

class UserProfile(BaseModel):
    id: str
    username: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    preferences: dict = {} # 存放用户偏好，如 {"language": "zh"}

class DocumentRecord(BaseModel):
    """记录上传文件的元数据"""
    id: str
    filename: str
    upload_time: datetime
    chunk_count: int
    status: str = "indexed"