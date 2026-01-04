# 多向量数据库支持文档

本文档说明如何使用和配置多种向量数据库提供商。

## 支持的向量数据库

1. **Milvus** - 开源、高性能向量数据库
2. **ChromaDB** - 轻量级、易用的向量数据库
3. **Pinecone** - 全托管向量数据库服务
4. **Qdrant** - 高性能、Rust实现的向量数据库

## 配置方式

### 方式1: 环境变量配置（推荐）

在 `.env` 文件中配置：

```bash
# 选择向量数据库提供商
VECTOR_STORE_PROVIDER=milvus  # 可选: milvus, chroma, pinecone, qdrant

# Milvus配置
MILVUS_URI=http://milvus:19530  # 或本地文件: ./milvus_data.db
MILVUS_TOKEN=  # 可选：认证令牌
MILVUS_COLLECTION=enterprise_knowledge
MILVUS_DIM=1024

# ChromaDB配置
CHROMA_PERSIST_DIR=./chroma_db

# Pinecone配置
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=  # 旧版API需要，新版可留空
PINECONE_INDEX=enterprise-knowledge

# Qdrant配置
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # 可选：API密钥
QDRANT_COLLECTION=enterprise_knowledge

# 通用配置
VECTOR_STORE_DIM=1024  # 向量维度
```

## 提供商详细信息

### Milvus

- **名称**: Milvus
- **类型**: 开源、分布式
- **特点**: 高性能、高可用、云原生
- **部署**: 本地或云端
- **适用场景**: 大规模生产环境

**配置示例**:
```bash
VECTOR_STORE_PROVIDER=milvus
MILVUS_URI=http://milvus:19530
MILVUS_COLLECTION=enterprise_knowledge
MILVUS_DIM=1024
```

**Docker部署**:
```yaml
# docker-compose.yml
milvus-standalone:
  image: milvusdb/milvus:v2.3.0
  ports:
    - "19530:19530"
```

### ChromaDB

- **名称**: ChromaDB
- **类型**: 轻量级、开源
- **特点**: 易用、Python原生、本地部署
- **部署**: 本地文件系统
- **适用场景**: 开发、测试、小规模生产

**配置示例**:
```bash
VECTOR_STORE_PROVIDER=chroma
CHROMA_PERSIST_DIR=./chroma_db
```

**优势**:
- 无需额外服务
- 快速启动
- 适合开发测试

### Pinecone

- **名称**: Pinecone
- **类型**: 全托管服务
- **特点**: 易用、自动扩展、高可用
- **部署**: 云端托管
- **适用场景**: 快速原型、中小规模生产

**配置示例**:
```bash
VECTOR_STORE_PROVIDER=pinecone
PINECONE_API_KEY=your-api-key
PINECONE_INDEX=enterprise-knowledge
```

**优势**:
- 无需运维
- 自动扩展
- 高可用性

### Qdrant

- **名称**: Qdrant
- **类型**: 开源、高性能
- **特点**: Rust实现、REST API、Docker支持
- **部署**: 本地或云端
- **适用场景**: 高性能需求、REST API集成

**配置示例**:
```bash
VECTOR_STORE_PROVIDER=qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=enterprise_knowledge
```

**Docker部署**:
```bash
docker run -p 6333:6333 qdrant/qdrant
```

## API使用

### 1. 查看支持的提供商

```bash
curl http://localhost:8080/api/v1/vector-store/providers
```

### 2. 查看当前配置

```bash
curl http://localhost:8080/api/v1/vector-store/current
```

### 3. 查看特定提供商信息

```bash
curl http://localhost:8080/api/v1/vector-store/provider/milvus
curl http://localhost:8080/api/v1/vector-store/provider/chroma
curl http://localhost:8080/api/v1/vector-store/provider/pinecone
curl http://localhost:8080/api/v1/vector-store/provider/qdrant
```

## 代码使用示例

### 在代码中创建向量存储实例

```python
from app.utils.vector_store_providers import VectorStoreProviderFactory

# 创建Milvus向量存储
vector_store = VectorStoreProviderFactory.create_vector_store(
    provider="milvus",
    collection_name="my_collection",
    dimension=1024
)

# 创建ChromaDB向量存储
vector_store = VectorStoreProviderFactory.create_vector_store(
    provider="chroma",
    collection_name="my_collection"
)

# 创建Pinecone向量存储
vector_store = VectorStoreProviderFactory.create_vector_store(
    provider="pinecone",
    collection_name="my_index",
    dimension=1024,
    api_key="your-key"
)

# 创建Qdrant向量存储
vector_store = VectorStoreProviderFactory.create_vector_store(
    provider="qdrant",
    collection_name="my_collection",
    dimension=1024,
    url="http://localhost:6333"
)
```

## 迁移指南

### 从Milvus迁移到其他数据库

1. **备份数据**: 导出现有向量数据
2. **更新配置**: 修改 `.env` 文件中的 `VECTOR_STORE_PROVIDER`
3. **重新索引**: 运行文档摄取服务重新建立索引

### 提供商选择建议

| 场景 | 推荐提供商 | 原因 |
|------|-----------|------|
| 开发/测试 | ChromaDB | 快速启动，无需额外服务 |
| 小规模生产 | ChromaDB/Qdrant | 简单部署，性能足够 |
| 中大规模生产 | Milvus/Qdrant | 高性能，可扩展 |
| 快速原型 | Pinecone | 无需运维，快速上线 |
| 云原生部署 | Milvus/Pinecone | 支持K8s，高可用 |

## 性能对比

| 提供商 | 查询速度 | 写入速度 | 扩展性 | 易用性 |
|--------|---------|---------|--------|--------|
| Milvus | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| ChromaDB | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Pinecone | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Qdrant | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## 注意事项

1. **数据迁移**: 切换提供商需要重新索引数据
2. **维度一致性**: 确保所有提供商使用相同的向量维度
3. **依赖安装**: 根据使用的提供商安装相应的依赖包
4. **性能测试**: 在生产环境切换前进行性能测试
5. **数据备份**: 定期备份向量数据

## 故障排查

### 问题1: 向量数据库连接失败

**错误**: `Failed to initialize vector store connection`

**解决方案**:
- 检查连接URL是否正确
- 检查网络连接
- 检查服务是否运行
- 查看日志获取详细错误信息

### 问题2: 集合/索引不存在

**错误**: `Collection/Index not found`

**解决方案**:
- 首次使用会自动创建集合
- 检查集合名称是否正确
- 对于Pinecone，确保API密钥有效

### 问题3: 维度不匹配

**错误**: `Dimension mismatch`

**解决方案**:
- 确保所有配置使用相同的维度
- 检查embedding模型的输出维度
- 重新索引数据

## 最佳实践

1. **开发环境**: 使用ChromaDB，快速启动
2. **生产环境**: 根据规模选择Milvus或Qdrant
3. **云部署**: 考虑使用Pinecone减少运维负担
4. **数据备份**: 定期导出向量数据
5. **监控**: 监控查询性能和存储使用情况

---

*最后更新: 2026*

