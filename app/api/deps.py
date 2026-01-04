"""
依赖注入模块

所有服务使用单例模式，避免重复初始化
"""
from typing import Generator
from fastapi import Depends
from app.services.chat_service import ChatService
from app.services.ingest_service import IngestService
from app.services.memory_service import MemoryService
from app.core.security import get_api_key


# =============================================
# 服务依赖（单例模式，由服务类内部管理）
# =============================================

def get_memory_service() -> MemoryService:
    """获取记忆服务（单例）"""
    return MemoryService()


def get_chat_service() -> ChatService:
    """获取聊天服务（单例）"""
    return ChatService()


def get_ingest_service() -> IngestService:
    """获取文档摄取服务（单例）"""
    return IngestService()


# =============================================
# 组合依赖：需要鉴权的服务
# =============================================

def get_authorized_chat_service(
    api_key: str = Depends(get_api_key),
    service: ChatService = Depends(get_chat_service)
) -> ChatService:
    """获取需要鉴权的聊天服务"""
    return service


def get_authorized_ingest_service(
    api_key: str = Depends(get_api_key),
    service: IngestService = Depends(get_ingest_service)
) -> IngestService:
    """获取需要鉴权的摄取服务"""
    return service