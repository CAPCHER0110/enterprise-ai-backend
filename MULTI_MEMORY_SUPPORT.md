# 多记忆方案支持文档

本文档说明如何使用和配置多种记忆管理方案，支持短期记忆和长期记忆。

## 支持的记忆方案

1. **LlamaIndex** - LlamaIndex记忆管理（ChatMemoryBuffer + Redis）
2. **LangChain** - LangChain记忆管理（ConversationBufferWindowMemory + Redis）
3. **Mem0** - Mem0高级记忆管理（语义记忆 + 向量存储）

## 记忆类型

### 短期记忆（Short-term Memory）

- **定义**: 当前会话内的上下文记忆
- **实现**: 滑动窗口机制，自动管理token限制
- **特点**: 
  - 快速访问
  - 自动清理过期内容
  - 受token限制约束

### 长期记忆（Long-term Memory）

- **定义**: 跨会话的持久化记忆
- **实现**: 
  - LlamaIndex/LangChain: Redis持久化
  - Mem0: 向量存储的语义记忆
- **特点**:
  - 跨会话持久化
  - 可检索历史对话
  - 支持语义搜索（Mem0）

## 配置方式

### 方式1: 环境变量配置（推荐）

在 `.env` 文件中配置：

```bash
# 选择记忆提供商
MEMORY_PROVIDER=llamaindex  # 可选: llamaindex, langchain, mem0

# 短期记忆配置
SHORT_TERM_MEMORY_ENABLED=true
SHORT_TERM_TOKEN_LIMIT=3000  # 短期记忆token限制

# 长期记忆配置
LONG_TERM_MEMORY_ENABLED=true

# Redis配置（用于LlamaIndex和LangChain的长期记忆）
REDIS_URL=redis://localhost:6379/0

# Mem0配置（可选）
MEM0_CONFIG={}  # JSON格式的自定义配置
```

## 提供商详细信息

### LlamaIndex

- **名称**: LlamaIndex
- **短期记忆**: ChatMemoryBuffer（滑动窗口）
- **长期记忆**: RedisChatStore（Redis持久化）
- **特点**: 
  - 与LlamaIndex深度集成
  - 自动token管理
  - Redis持久化
- **适用场景**: 使用LlamaIndex构建的RAG应用

**配置示例**:
```bash
MEMORY_PROVIDER=llamaindex
SHORT_TERM_TOKEN_LIMIT=3000
LONG_TERM_MEMORY_ENABLED=true
REDIS_URL=redis://localhost:6379/0
```

**优势**:
- 与LlamaIndex无缝集成
- 自动管理token限制
- 简单易用

### LangChain

- **名称**: LangChain
- **短期记忆**: ConversationBufferWindowMemory（滑动窗口）
- **长期记忆**: RedisChatMessageHistory（Redis持久化）
- **特点**:
  - 与LangChain集成
  - 灵活的窗口大小配置
  - Redis持久化
- **适用场景**: 使用LangChain构建的应用

**配置示例**:
```bash
MEMORY_PROVIDER=langchain
SHORT_TERM_TOKEN_LIMIT=3000
LONG_TERM_MEMORY_ENABLED=true
REDIS_URL=redis://localhost:6379/0
```

**优势**:
- 与LangChain生态集成
- 灵活的配置选项
- 支持多种记忆类型

### Mem0

- **名称**: Mem0
- **短期记忆**: 会话内上下文
- **长期记忆**: 向量存储的语义记忆
- **特点**:
  - 高级语义记忆
  - 向量存储支持
  - 记忆检索和搜索
- **适用场景**: 需要高级记忆管理的应用

**配置示例**:
```bash
MEMORY_PROVIDER=mem0
SHORT_TERM_TOKEN_LIMIT=3000
LONG_TERM_MEMORY_ENABLED=true
# Mem0使用配置的向量数据库
VECTOR_STORE_PROVIDER=milvus
```

**优势**:
- 语义记忆能力
- 支持记忆检索
- 向量存储集成

## API使用

### 1. 查看支持的提供商

```bash
curl http://localhost:8080/api/v1/memory/providers
```

### 2. 查看当前配置

```bash
curl http://localhost:8080/api/v1/memory/current
```

### 3. 查看特定提供商信息

```bash
curl http://localhost:8080/api/v1/memory/provider/llamaindex
curl http://localhost:8080/api/v1/memory/provider/langchain
curl http://localhost:8080/api/v1/memory/provider/mem0
```

### 4. 清空会话记忆

```bash
curl -X DELETE http://localhost:8080/api/v1/memory/session/user123 \
  -H "X-API-KEY: sk-admin-secret"
```

## 代码使用示例

### 在代码中使用记忆服务

```python
from app.services.memory_service import MemoryService

# 获取记忆服务（单例）
memory_service = MemoryService()

# 获取记忆对象
memory = memory_service.get_memory(session_id="user123")

# 清空记忆
await memory_service.clear_memory(session_id="user123")

# 保存记忆（长期记忆）
await memory_service.save_memory(
    session_id="user123",
    messages=[
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
)
```

### 创建自定义记忆提供商

```python
from app.utils.memory_providers import MemoryProviderFactory

# 创建LlamaIndex记忆提供商
memory_provider = MemoryProviderFactory.create_memory_provider(
    provider="llamaindex",
    short_term_token_limit=5000,
    long_term_enabled=True
)

# 获取记忆
memory = memory_provider.get_memory(session_id="user123")
```

## 记忆策略

### 滑动窗口策略

- **原理**: 保持最近的N个token的对话历史
- **优点**: 自动管理，无需手动清理
- **缺点**: 可能丢失较早的重要信息

### 总结策略

- **原理**: 将历史对话总结为关键信息
- **优点**: 保留重要信息，减少token使用
- **缺点**: 可能丢失细节

### 语义记忆策略（Mem0）

- **原理**: 将记忆转换为向量存储，支持语义检索
- **优点**: 智能检索相关记忆
- **缺点**: 需要额外的向量存储

## 最佳实践

1. **开发环境**: 使用LlamaIndex，简单易用
2. **生产环境**: 根据需求选择：
   - 简单场景：LlamaIndex
   - LangChain生态：LangChain
   - 高级需求：Mem0
3. **短期记忆**: 根据模型上下文窗口设置合理的token限制
4. **长期记忆**: 启用长期记忆以支持跨会话对话
5. **性能优化**: 
   - 定期清理过期记忆
   - 使用Redis持久化长期记忆
   - 监控记忆存储使用情况

## 迁移指南

### 从LlamaIndex迁移到其他方案

1. **备份数据**: 导出Redis中的对话历史
2. **更新配置**: 修改 `MEMORY_PROVIDER`
3. **重新索引**: 对于Mem0，需要重新建立记忆索引

### 提供商选择建议

| 场景 | 推荐提供商 | 原因 |
|------|-----------|------|
| LlamaIndex RAG | LlamaIndex | 深度集成 |
| LangChain应用 | LangChain | 生态兼容 |
| 高级记忆需求 | Mem0 | 语义记忆 |
| 简单场景 | LlamaIndex | 易用性 |

## 注意事项

1. **Token限制**: 确保短期记忆token限制不超过模型上下文窗口
2. **Redis依赖**: LlamaIndex和LangChain的长期记忆需要Redis
3. **向量存储**: Mem0的长期记忆需要向量数据库
4. **数据迁移**: 切换提供商需要重新建立记忆
5. **性能影响**: 长期记忆可能增加查询延迟

## 故障排查

### 问题1: 记忆不持久化

**错误**: 会话结束后记忆丢失

**解决方案**:
- 检查 `LONG_TERM_MEMORY_ENABLED` 是否启用
- 检查Redis连接是否正常
- 检查记忆提供商配置

### 问题2: Token限制问题

**错误**: 记忆超出token限制

**解决方案**:
- 调整 `SHORT_TERM_TOKEN_LIMIT`
- 启用长期记忆保存重要信息
- 使用总结策略减少token使用

### 问题3: 记忆检索失败

**错误**: 无法检索历史记忆

**解决方案**:
- 检查长期记忆是否启用
- 检查Redis/向量数据库连接
- 查看日志获取详细错误

---

*最后更新: 2026*

