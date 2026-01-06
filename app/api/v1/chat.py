"""
聊天API端点 - 提供RAG对话能力
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.responses import StreamingResponse, JSONResponse # 引入 JSONResponse
from app.models.chat import ChatRequest, ChatResponse, SourceNode # 引入响应模型
from app.services.chat_service import ChatService
from app.core.logging import logger, set_request_context
from app.core.security import validate_query, validate_session_id
from app.core.exceptions import ValidationException

router = APIRouter()


def get_chat_service() -> ChatService:
    """依赖注入：获取ChatService实例"""
    return ChatService()


@router.post("/completions")
async def chat_endpoint(
    req: ChatRequest,
    request: Request,
    service: ChatService = Depends(get_chat_service)
):
    """
    流式对话接口 (SSE)
    
    支持 Server-Sent Events (SSE) 流式响应
    可选参数允许临时覆盖LLM配置
    """
    # 验证输入
    try:
        validated_query = validate_query(req.query)
        validated_session_id = validate_session_id(req.session_id)
    except ValueError as e:
        raise ValidationException(str(e))
    
    # 设置日志上下文
    set_request_context(session_id=validated_session_id)

    # --- 新增：处理非流式请求 ---
    if not req.stream:
        try:
            logger.info(f"Starting standard chat for session {validated_session_id}")
            response = await service.chat(
                validated_query,
                validated_session_id,
                llm_provider=req.llm_provider,
                llm_model=req.llm_model,
                temperature=req.temperature
            )

            # 解析来源文档 (LlamaIndex Response -> SourceNode)
            sources = []
            if hasattr(response, 'source_nodes'):
                for node_with_score in response.source_nodes:
                    node = node_with_score.node
                    sources.append(SourceNode(
                        filename=node.metadata.get('file_name', 'unknown'),
                        score=node_with_score.score or 0.0,
                        text=node.get_content()[:500] # 截取部分文本避免过长
                    ))

            # 返回 JSON 响应
            return ChatResponse(
                response=response.response,
                sources=sources
            )

        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    # --- 原有的流式处理逻辑 ---
    async def event_generator():
        try:
            logger.info(f"Starting chat stream for session {validated_session_id}")
            
            # 获取 Service 的生成器（支持自定义LLM参数）
            stream = service.chat_stream(
                validated_query,
                validated_session_id,
                llm_provider=req.llm_provider,
                llm_model=req.llm_model,
                temperature=req.temperature
            )
            
            # 转换为 SSE 格式
            async for token in stream:
                # SSE 格式: data: content\n\n
                yield f"data: {json.dumps({'content': token}, ensure_ascii=False)}\n\n"
            
            # 发送完成标记
            yield "data: [DONE]\n\n"
            logger.info(f"Chat stream completed for session {validated_session_id}")
            
        except ValidationException as e:
            logger.warning(f"Validation error in chat stream: {e.message}")
            error_data = json.dumps({
                "error": e.message,
                "code": e.code
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
        except Exception as e:
            logger.error(f"Error generating response for session {validated_session_id}: {e}", exc_info=True)
            error_data = json.dumps({
                "error": "An error occurred while generating the response",
                "code": "server_error"
            }, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
        }
    )
