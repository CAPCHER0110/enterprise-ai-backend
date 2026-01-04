"""
聊天相关的Pydantic模型

定义请求和响应的数据结构
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
import re


class ChatRequest(BaseModel):
    """聊天请求模型"""
    
    query: str = Field(
        ..., 
        description="用户的问题",
        example="如何配置 Dockerfile？",
        min_length=1,
        max_length=10000  # 限制查询长度
    )
    session_id: str = Field(
        ..., 
        description="会话ID，用于隔离用户记忆",
        example="user_123_session",
        min_length=1,
        max_length=128
    )
    stream: bool = Field(
        True, 
        description="是否开启流式响应"
    )
    # 可选的LLM覆盖配置（用于临时切换LLM）
    llm_provider: Optional[Literal["openai", "anthropic", "vllm"]] = Field(
        None, 
        description="LLM提供商（可选，覆盖默认配置）"
    )
    llm_model: Optional[str] = Field(
        None,
        description="LLM模型名称（可选，覆盖默认配置）",
        max_length=256
    )
    temperature: Optional[float] = Field(
        None,
        description="温度参数（可选，覆盖默认配置）",
        ge=0.0,
        le=2.0
    )
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """验证session_id格式"""
        # 只允许字母、数字、下划线、连字符
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                'session_id只能包含字母、数字、下划线和连字符'
            )
        return v
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """验证query不为空白"""
        if not v.strip():
            raise ValueError('query不能为空')
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "如何配置 Dockerfile？",
                    "session_id": "user_123_session",
                    "stream": True
                }
            ]
        }
    }


class SourceNode(BaseModel):
    """来源节点模型"""
    
    filename: str = Field(..., description="文件名")
    score: float = Field(..., description="相似度得分", ge=0.0, le=1.0)
    text: str = Field(..., description="文本内容")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "filename": "docker_guide.md",
                "score": 0.92,
                "text": "Dockerfile是用于构建Docker镜像的文本文件..."
            }
        }
    }


class ChatResponse(BaseModel):
    """聊天响应模型"""
    
    response: str = Field(..., description="AI的回复")
    sources: List[SourceNode] = Field(
        default_factory=list, 
        description="参考来源"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "response": "Dockerfile的配置步骤如下...",
                "sources": [
                    {
                        "filename": "docker_guide.md",
                        "score": 0.92,
                        "text": "Dockerfile是用于构建Docker镜像的文本文件..."
                    }
                ]
            }
        }
    }


class ChatStreamEvent(BaseModel):
    """SSE流式事件模型"""
    
    content: Optional[str] = Field(None, description="内容片段")
    error: Optional[str] = Field(None, description="错误信息")
    code: Optional[str] = Field(None, description="错误代码")
    done: bool = Field(False, description="是否完成")