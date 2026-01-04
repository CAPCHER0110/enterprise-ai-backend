# 更新日志

本文档记录项目的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.1.0] - 2026-01-04

### 新增

#### 测试套件
- 添加完整的测试套件（单元测试、API测试、服务测试）
- 添加pytest配置和共享fixtures
- 添加测试覆盖率配置
- 添加测试文档（tests/README.md）

#### 安全功能
- 实现速率限制器（滑动窗口算法）
- 添加速率限制中间件
- 添加配置验证器（启动时验证）
- 支持API Key和IP地址识别

#### 监控和指标
- 集成Prometheus指标导出
- 添加HTTP请求指标
- 添加LLM调用指标
- 添加向量数据库操作指标
- 添加Redis操作指标
- 添加缓存命中率指标
- 添加速率限制指标

#### 文档
- 添加部署指南（DEPLOYMENT_GUIDE.md）
- 添加故障排查指南（TROUBLESHOOTING.md）
- 添加项目审查报告（PROJECT_REVIEW.md）
- 添加改进总结（IMPROVEMENTS_SUMMARY.md）
- 更新README文档

### 改进

- 优化配置管理（添加速率限制配置）
- 改进metrics端点（返回Prometheus格式）
- 完善项目结构文档
- 增强生产环境就绪度

### 依赖

- 添加 `prometheus-client>=0.19.0`

## [1.0.0] - 2026-01-03

### 新增

#### 多LLM支持
- 支持OpenAI、Anthropic、vLLM
- LLM提供商工厂模式
- 动态LLM配置
- 请求级LLM切换

#### 多向量数据库支持
- 支持Milvus、ChromaDB、Pinecone、Qdrant
- 向量数据库提供商工厂模式
- 统一向量存储接口

#### 多记忆方案支持
- 支持LlamaIndex、LangChain、Mem0
- 短期记忆和长期记忆区分
- 记忆提供商工厂模式

#### 核心功能
- 重试机制（指数退避）
- 断路器模式
- Redis连接池
- 内存缓存
- 请求ID中间件
- 日志中间件
- 指标中间件
- 健康检查增强

#### API端点
- `/api/v1/chat/completions` - 聊天接口
- `/api/v1/ingest/upload` - 文档上传
- `/api/v1/admin/clear-knowledge-base` - 清空知识库
- `/api/v1/admin/stats` - 系统统计
- `/api/v1/llm/*` - LLM管理
- `/api/v1/vector-store/*` - 向量数据库管理
- `/api/v1/memory/*` - 记忆管理
- `/health` - 健康检查
- `/metrics` - 指标端点

#### 文档
- OPTIMIZATION_SUMMARY.md - 优化总结
- MULTI_LLM_SUPPORT.md - 多LLM支持文档
- MULTI_VECTOR_STORE_SUPPORT.md - 多向量数据库文档
- MULTI_MEMORY_SUPPORT.md - 多记忆方案文档
- README.md - 项目文档

### 改进

- 从Poetry迁移到requirements.txt
- 优化Dockerfile（多阶段构建）
- 完善docker-compose.yml
- 添加.gitignore
- 改进错误处理
- 增强日志系统
- 优化配置管理

### 依赖

#### 核心依赖
- fastapi>=0.109.0
- uvicorn[standard]>=0.27.0
- pydantic-settings>=2.1.0

#### AI栈
- llama-index-core>=0.10.0
- llama-index-llms-openai>=0.1.0
- llama-index-llms-anthropic>=0.1.0
- llama-index-embeddings-huggingface>=0.1.0
- llama-index-vector-stores-milvus>=0.1.0
- llama-index-vector-stores-chroma>=0.1.0
- llama-index-vector-stores-pinecone>=0.1.0
- llama-index-vector-stores-qdrant>=0.1.0
- llama-index-storage-chat-store-redis>=0.1.0

#### 记忆管理
- langchain>=0.1.0
- langchain-community>=0.0.20
- mem0ai>=0.1.0

#### 基础设施
- pymilvus>=2.3.0
- redis[hiredis]>=5.0.0
- python-multipart>=0.0.9
- httpx>=0.26.0

#### 向量数据库
- chromadb>=0.4.0
- pinecone-client>=2.2.0
- qdrant-client>=1.6.0

#### 开发工具
- pytest>=8.0.0
- mypy>=1.8.0
- black>=24.0.0

## [0.1.0] - 2024-01-01

### 新增

- 初始项目结构
- 基础FastAPI应用
- Milvus向量数据库集成
- vLLM集成
- Redis记忆存储
- 基础RAG功能
- 文档摄取
- 流式响应

---

## 版本说明

### 版本号格式

`主版本号.次版本号.修订号`

- **主版本号**: 不兼容的API变更
- **次版本号**: 向下兼容的功能新增
- **修订号**: 向下兼容的问题修正

### 变更类型

- **新增**: 新功能
- **改进**: 对现有功能的改进
- **修复**: 问题修复
- **废弃**: 即将移除的功能
- **移除**: 已移除的功能
- **安全**: 安全相关的修复
- **依赖**: 依赖项变更

---

**持续更新中...** 每次发布都会更新此文档。

