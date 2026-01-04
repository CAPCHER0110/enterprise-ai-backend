"""
安全模块 - API密钥验证和输入验证
"""
import re
import secrets
from typing import Optional
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings
from app.core.logging import logger


# 定义 Header 中的 key 名称，例如: X-API-KEY: secret-token
API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=False)

# 预编译正则表达式（性能优化）
SESSION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
QUERY_MAX_LENGTH = 10000
SESSION_ID_MAX_LENGTH = 128


async def get_api_key(api_key_header: Optional[str] = Security(API_KEY_HEADER)) -> str:
    """
    依赖注入：验证 API Key 是否有效
    
    使用时间常数比较防止时序攻击
    
    Args:
        api_key_header: 从请求头中提取的API密钥
        
    Returns:
        验证通过的API密钥
        
    Raises:
        HTTPException: 如果API密钥无效且配置要求验证
    """
    # 如果配置不要求API密钥，允许通过
    if not settings.API_KEY_REQUIRED:
        return api_key_header or ""
    
    # 如果没有提供API密钥
    if not api_key_header:
        logger.warning("API key required but not provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # 使用时间常数比较验证API密钥（防止时序攻击）
    is_valid = False
    for valid_key in settings.API_KEYS:
        if constant_time_compare(api_key_header, valid_key):
            is_valid = True
            break
    
    if is_valid:
        logger.debug("API key validated successfully")
        return api_key_header
    
    # API密钥无效 - 只记录部分密钥防止泄露
    masked_key = api_key_header[:8] + "..." if len(api_key_header) > 8 else "***"
    logger.warning(f"Invalid API key attempted: {masked_key}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API key",
    )


def validate_session_id(session_id: str) -> str:
    """
    验证会话ID格式
    
    Args:
        session_id: 会话ID
        
    Returns:
        验证通过的会话ID
        
    Raises:
        ValueError: 如果会话ID格式无效
    """
    if not session_id or not session_id.strip():
        raise ValueError("Session ID cannot be empty")
    
    session_id = session_id.strip()
    
    # 长度限制（先检查长度，避免正则处理过长字符串）
    if len(session_id) > SESSION_ID_MAX_LENGTH:
        raise ValueError(f"Session ID is too long (max {SESSION_ID_MAX_LENGTH} characters)")
    
    # 基本格式验证：只允许字母、数字、下划线、连字符
    if not SESSION_ID_PATTERN.match(session_id):
        raise ValueError("Session ID contains invalid characters")
    
    return session_id


def validate_query(query: str) -> str:
    """
    验证查询内容
    
    Args:
        query: 用户查询
        
    Returns:
        验证通过的查询
        
    Raises:
        ValueError: 如果查询无效
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    query = query.strip()
    
    # 长度限制
    if len(query) > QUERY_MAX_LENGTH:
        raise ValueError(f"Query is too long (max {QUERY_MAX_LENGTH} characters)")
    
    return query


def generate_api_key() -> str:
    """
    生成安全的API密钥
    
    Returns:
        格式为 sk-<32位随机hex字符串> 的API密钥
    """
    return f"sk-{secrets.token_hex(16)}"


def constant_time_compare(val1: str, val2: str) -> bool:
    """
    时间常数比较两个字符串（防止时序攻击）
    
    Args:
        val1: 第一个字符串
        val2: 第二个字符串
        
    Returns:
        是否相等
    """
    return secrets.compare_digest(val1.encode(), val2.encode())