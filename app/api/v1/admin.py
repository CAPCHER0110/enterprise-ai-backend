"""
管理员API端点

提供知识库管理、系统统计和缓存管理功能
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_api_key
from app.core.logging import logger
from app.core.cache import cache
from app.core.config import settings
from app.utils.llm_factory import get_index, reset_index

router = APIRouter()


async def _clear_milvus_collection(collection_name: str) -> dict:
    """清空Milvus集合"""
    try:
        from app.utils.vector_store import MilvusManager
        manager = MilvusManager.get_instance()
        
        if manager.client.has_collection(collection_name):
            manager.client.drop_collection(collection_name)
            return {"status": "success", "message": f"Milvus collection '{collection_name}' cleared"}
        else:
            return {"status": "info", "message": f"Collection '{collection_name}' does not exist"}
    except ImportError:
        raise HTTPException(status_code=500, detail="Milvus manager not available")


async def _clear_chroma_collection(collection_name: str) -> dict:
    """清空ChromaDB集合"""
    try:
        import chromadb
        persist_dir = settings.CHROMA_PERSIST_DIR
        
        try:
            client = chromadb.PersistentClient(path=persist_dir)
        except AttributeError:
            client = chromadb.Client()
        
        try:
            client.delete_collection(collection_name)
            return {"status": "success", "message": f"ChromaDB collection '{collection_name}' cleared"}
        except ValueError:
            return {"status": "info", "message": f"Collection '{collection_name}' does not exist"}
    except ImportError:
        raise HTTPException(status_code=500, detail="ChromaDB not installed")


async def _clear_qdrant_collection(collection_name: str) -> dict:
    """清空Qdrant集合"""
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
        
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)
            return {"status": "success", "message": f"Qdrant collection '{collection_name}' cleared"}
        else:
            return {"status": "info", "message": f"Collection '{collection_name}' does not exist"}
    except ImportError:
        raise HTTPException(status_code=500, detail="Qdrant client not installed")


@router.delete("/knowledge-base/clear", dependencies=[Depends(get_api_key)])
async def clear_knowledge_base():
    """
    [危险] 清空企业知识库
    
    根据配置的向量数据库提供商清空相应的集合
    需要API密钥认证
    """
    provider = settings.VECTOR_STORE_PROVIDER.lower()
    collection_name = settings.VECTOR_STORE_COLLECTION
    
    try:
        logger.warning(f"Admin clearing knowledge base: provider={provider}, collection={collection_name}")
        
        if provider == "milvus":
            result = await _clear_milvus_collection(collection_name)
        elif provider == "chroma":
            result = await _clear_chroma_collection(collection_name)
        elif provider == "qdrant":
            result = await _clear_qdrant_collection(collection_name)
        elif provider == "pinecone":
            # Pinecone需要使用delete_all而不是删除集合
            result = {
                "status": "warning", 
                "message": "Pinecone清空需要手动通过Pinecone控制台完成"
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported vector store provider: {provider}"
            )
        
        # 清空相关缓存
        cache.clear()
        
        # 重置索引以便重新初始化
        reset_index()
        
        result["provider"] = provider
        result["collection"] = collection_name
        
        if result["status"] == "success":
            logger.warning(f"Knowledge base cleared: {result}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing knowledge base: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", dependencies=[Depends(get_api_key)])
async def system_stats():
    """
    查看系统详细状态和统计信息
    
    返回所有组件的健康状态和详细统计
    需要API密钥认证
    """
    from app.core.connections import RedisConnectionPool
    from datetime import datetime
    
    stats = {
        "status": "healthy",
        "version": "1.1.0",
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.utcnow().isoformat(),
        "configuration": {
            "llm_provider": settings.LLM_PROVIDER,
            "llm_model": settings.LLM_MODEL_NAME,
            "vector_store_provider": settings.VECTOR_STORE_PROVIDER,
            "memory_provider": settings.MEMORY_PROVIDER,
        },
        "components": {}
    }
    
    # 向量数据库统计
    vector_store_name = settings.VECTOR_STORE_PROVIDER.lower()
    collection_name = settings.VECTOR_STORE_COLLECTION
    
    try:
        vector_store_stats = await _get_vector_store_stats(vector_store_name, collection_name)
        stats["components"]["vector_store"] = vector_store_stats
        
        if vector_store_stats.get("status") == "error":
            stats["status"] = "degraded"
    except Exception as e:
        stats["components"]["vector_store"] = {
            "status": "error",
            "provider": vector_store_name,
            "error": str(e)
        }
        stats["status"] = "degraded"
    
    # Redis 统计
    try:
        redis_healthy = await RedisConnectionPool.health_check()
        redis_info = await RedisConnectionPool.get_info()
        stats["components"]["redis"] = {
            "status": "connected" if redis_healthy else "unhealthy",
            **redis_info
        }
        if not redis_healthy:
            stats["status"] = "degraded"
    except Exception as e:
        stats["components"]["redis"] = {
            "status": "error",
            "error": str(e)
        }
        stats["status"] = "degraded"
    
    # 缓存统计
    cache_stats = cache.get_stats()
    stats["components"]["cache"] = cache_stats
    
    # 速率限制器统计
    from app.core.rate_limiter import rate_limiter
    stats["components"]["rate_limiter"] = {
        "enabled": settings.RATE_LIMIT_ENABLED,
        "default_limit": settings.RATE_LIMIT_REQUESTS,
        "window_seconds": settings.RATE_LIMIT_WINDOW,
        "active_clients": len(rate_limiter._requests)
    }
    
    return stats


async def _get_vector_store_stats(provider: str, collection_name: str) -> dict:
    """获取向量数据库统计信息"""
    base_info = {
        "provider": provider,
        "collection": collection_name
    }
    
    try:
        if provider == "milvus":
            from app.utils.vector_store import MilvusManager
            manager = MilvusManager.get_instance()
            
            if manager.client.has_collection(collection_name):
                collection_info = manager.client.describe_collection(collection_name)
                return {
                    "status": "connected",
                    **base_info,
                    "dimension": collection_info.get("dimension", "unknown"),
                    "consistency_level": collection_info.get("consistency_level", "unknown")
                }
            else:
                return {"status": "collection_not_found", **base_info}
        
        elif provider == "chroma":
            import chromadb
            client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            try:
                collection = client.get_collection(collection_name)
                return {
                    "status": "connected",
                    **base_info,
                    "count": collection.count()
                }
            except ValueError:
                return {"status": "collection_not_found", **base_info}
        
        elif provider == "qdrant":
            from qdrant_client import QdrantClient
            client = QdrantClient(url=settings.QDRANT_URL)
            
            if client.collection_exists(collection_name):
                info = client.get_collection(collection_name)
                return {
                    "status": "connected",
                    **base_info,
                    "points_count": info.points_count,
                    "vectors_count": info.vectors_count
                }
            else:
                return {"status": "collection_not_found", **base_info}
        
        elif provider == "pinecone":
            return {"status": "connected", **base_info, "note": "详细统计需通过Pinecone控制台查看"}
        
        else:
            return {"status": "unknown_provider", **base_info}
            
    except ImportError as e:
        return {"status": "dependency_missing", **base_info, "error": str(e)}
    except Exception as e:
        return {"status": "error", **base_info, "error": str(e)}

@router.post("/cache/clear", dependencies=[Depends(get_api_key)])
async def clear_cache():
    """
    清空应用缓存
    
    需要API密钥认证
    """
    try:
        cleared_count = len(cache._cache) if hasattr(cache, '_cache') else 0
        cache.clear()
        logger.info("Cache cleared by admin")
        return {
            "status": "success",
            "message": "Cache cleared successfully",
            "cleared_entries": cleared_count
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cache/stats", dependencies=[Depends(get_api_key)])
async def cache_stats():
    """
    获取缓存统计信息
    
    需要API密钥认证
    """
    return cache.get_stats()