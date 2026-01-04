# 故障排查指南

本文档提供常见问题的诊断和解决方案。

## 📋 目录

- [启动问题](#启动问题)
- [连接问题](#连接问题)
- [性能问题](#性能问题)
- [API错误](#api错误)
- [数据问题](#数据问题)
- [日志分析](#日志分析)

## 启动问题

### 问题1: 应用无法启动

**症状**:
```
Error: Failed to start application
```

**可能原因和解决方案**:

1. **配置错误**
   ```bash
   # 检查配置验证错误
   python -c "from app.core.config_validator import ConfigValidator; ConfigValidator.validate_and_raise()"
   ```
   
2. **端口被占用**
   ```bash
   # 检查8080端口
   lsof -i :8080
   # 或
   netstat -tulpn | grep 8080
   
   # 解决：停止占用端口的进程或更改端口
   kill -9 <PID>
   # 或
   uvicorn app.main:app --port 8081
   ```

3. **依赖未安装**
   ```bash
   # 重新安装依赖
   pip install -r requirements.txt
   ```

### 问题2: 启动时Milvus连接失败

**症状**:
```
ERROR: Failed to initialize vector store connection
```

**解决方案**:

1. **检查Milvus服务状态**
   ```bash
   # Docker
   docker ps | grep milvus
   
   # 查看Milvus日志
   docker logs milvus-standalone
   ```

2. **验证连接配置**
   ```bash
   # 检查MILVUS_URI是否正确
   echo $MILVUS_URI
   
   # 测试连接
   python -c "from pymilvus import connections; connections.connect('default', uri='<your-milvus-uri>')"
   ```

3. **启动Milvus**
   ```bash
   docker-compose up -d milvus-standalone
   ```

### 问题3: Redis连接失败

**症状**:
```
WARNING: Redis connection check failed
```

**解决方案**:

1. **检查Redis服务**
   ```bash
   # Docker
   docker ps | grep redis
   
   # 测试连接
   redis-cli -u $REDIS_URL ping
   ```

2. **启动Redis**
   ```bash
   docker-compose up -d redis
   ```

## 连接问题

### 问题4: LLM API调用超时

**症状**:
```
ERROR: LLM request timeout after 30s
```

**解决方案**:

1. **增加超时时间**
   ```bash
   # .env
   REQUEST_TIMEOUT=60
   ```

2. **检查LLM服务状态**
   ```bash
   # vLLM
   curl http://localhost:8000/v1/models
   
   # OpenAI
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. **检查网络连接**
   ```bash
   ping api.openai.com
   ```

### 问题5: 向量数据库查询慢

**症状**:
```
查询响应时间 > 5秒
```

**解决方案**:

1. **检查索引类型**
   ```python
   # 使用更高效的索引类型
   # 小数据集: IVF_FLAT
   # 大数据集: HNSW
   ```

2. **优化查询参数**
   ```bash
   # 减少返回结果数
   SIMILARITY_TOP_K=5
   ```

3. **检查Milvus资源**
   ```bash
   # 查看Milvus内存使用
   docker stats milvus-standalone
   ```

## 性能问题

### 问题6: 请求响应慢

**症状**:
```
平均响应时间 > 2秒
```

**诊断步骤**:

1. **检查日志中的处理时间**
   ```bash
   # 查看LoggingMiddleware输出
   grep "completed in" logs/app.log
   ```

2. **检查各组件耗时**
   ```bash
   # 启用详细日志
   LOG_LEVEL=DEBUG
   ```

**解决方案**:

1. **启用缓存**
   ```bash
   ENABLE_CACHE=true
   CACHE_TTL=3600
   ```

2. **增加worker数量**
   ```bash
   uvicorn app.main:app --workers 4
   ```

3. **优化数据库连接池**
   ```bash
   REDIS_MAX_CONNECTIONS=50
   ```

### 问题7: 内存使用过高

**症状**:
```
容器或进程内存使用持续增长
```

**诊断**:
```bash
# 查看内存使用
docker stats
# 或
ps aux | grep python

# Python内存分析
pip install memory-profiler
python -m memory_profiler app/main.py
```

**解决方案**:

1. **清理缓存**
   ```bash
   # 减少缓存TTL
   CACHE_TTL=1800
   ```

2. **限制连接池大小**
   ```bash
   REDIS_MAX_CONNECTIONS=20
   ```

3. **重启服务**
   ```bash
   docker-compose restart api
   ```

## API错误

### 问题8: 401 Unauthorized

**症状**:
```json
{
  "error": "Invalid API key",
  "code": "authentication_error"
}
```

**解决方案**:

1. **检查API密钥**
   ```bash
   # 确认API_KEY_REQUIRED设置
   echo $API_KEY_REQUIRED
   
   # 检查API_KEYS列表
   echo $API_KEYS
   ```

2. **请求中包含API密钥**
   ```bash
   curl -H "X-API-Key: sk-xxx" http://localhost:8080/api/v1/chat/completions
   ```

### 问题9: 429 Too Many Requests

**症状**:
```json
{
  "error": "Too many requests",
  "code": "rate_limit_exceeded",
  "retry_after": 30
}
```

**解决方案**:

1. **等待重试**
   ```bash
   # 查看Retry-After头
   sleep 30 && retry_request
   ```

2. **调整速率限制**
   ```bash
   # .env
   RATE_LIMIT_REQUESTS=200
   RATE_LIMIT_WINDOW=60
   ```

3. **禁用速率限制（开发环境）**
   ```bash
   RATE_LIMIT_ENABLED=false
   ```

### 问题10: 422 Validation Error

**症状**:
```json
{
  "error": "Validation failed",
  "code": "validation_error",
  "details": [...]
}
```

**解决方案**:

1. **检查请求格式**
   ```bash
   # 确保包含必需字段
   {
     "query": "你好",
     "session_id": "user123",
     "stream": true
   }
   ```

2. **验证字段格式**
   ```bash
   # session_id: 只能包含字母、数字、下划线、连字符
   # query: 1-10000字符
   ```

### 问题11: 500 Internal Server Error

**症状**:
```json
{
  "error": "Internal Server Error",
  "code": "server_error"
}
```

**诊断**:

1. **查看详细日志**
   ```bash
   # 查看最新错误
   tail -f logs/app.log | grep ERROR
   
   # Docker日志
   docker logs -f enterprise-ai-api
   ```

2. **启用DEBUG模式**
   ```bash
   LOG_LEVEL=DEBUG
   ```

## 数据问题

### 问题12: 文档上传失败

**症状**:
```
ERROR: Failed to process document
```

**解决方案**:

1. **检查文件大小**
   ```bash
   # 默认限制50MB
   # 如需调整，修改app/api/v1/ingest.py中的MAX_FILE_SIZE
   ```

2. **检查文件格式**
   ```bash
   # 支持的格式: .txt, .pdf, .docx, .md
   file your-document.pdf
   ```

3. **检查磁盘空间**
   ```bash
   df -h
   ```

### 问题13: 检索结果不准确

**症状**:
```
RAG返回的内容与查询不相关
```

**解决方案**:

1. **调整相似度阈值**
   ```bash
   SIMILARITY_TOP_K=10  # 增加返回结果数
   ```

2. **重新索引文档**
   ```bash
   # 清空知识库
   curl -X POST http://localhost:8080/api/v1/admin/clear-knowledge-base
   
   # 重新上传文档
   ```

3. **检查embedding模型**
   ```bash
   # 确认embedding模型已正确加载
   grep "Embedding model" logs/app.log
   ```

### 问题14: 会话记忆丢失

**症状**:
```
AI无法记住之前的对话内容
```

**解决方案**:

1. **检查Redis连接**
   ```bash
   redis-cli -u $REDIS_URL ping
   ```

2. **检查记忆配置**
   ```bash
   echo $SHORT_TERM_MEMORY_ENABLED
   echo $SHORT_TERM_TOKEN_LIMIT
   ```

3. **查看Redis数据**
   ```bash
   redis-cli -u $REDIS_URL keys "*session*"
   ```

## 日志分析

### 查看关键日志

```bash
# 错误日志
grep ERROR logs/app.log

# 警告日志
grep WARNING logs/app.log

# 特定会话日志
grep "session_id: user123" logs/app.log

# 性能日志
grep "completed in" logs/app.log

# 速率限制日志
grep "Rate limit" logs/app.log
```

### 日志级别

```bash
# 生产环境
LOG_LEVEL=INFO

# 调试问题
LOG_LEVEL=DEBUG

# 最小日志
LOG_LEVEL=WARNING
```

## 常用诊断命令

### 健康检查

```bash
# 基本健康检查
curl http://localhost:8080/health | jq

# 详细状态
curl http://localhost:8080/metrics | jq
```

### 服务状态

```bash
# Docker容器
docker-compose ps

# Docker日志
docker-compose logs -f api

# 系统资源
docker stats

# 进程状态
ps aux | grep python
```

### 网络连接

```bash
# 检查端口
netstat -tulpn | grep 8080

# 测试连接
curl -I http://localhost:8080/health

# DNS解析
nslookup api.openai.com
```

## 获取帮助

如果以上方法无法解决问题：

1. **收集诊断信息**:
   ```bash
   # 收集日志
   docker-compose logs > logs-$(date +%Y%m%d).txt
   
   # 系统信息
   docker version
   docker-compose version
   python --version
   ```

2. **查看配置**:
   ```bash
   # 脱敏后的配置
   env | grep -E "^(LLM|MILVUS|REDIS|VECTOR)" | sed 's/KEY=.*/KEY=***/'
   ```

3. **提交Issue**:
   - 问题描述
   - 错误日志
   - 配置信息（脱敏）
   - 复现步骤

---

**持续更新中...** 如有新的常见问题，欢迎提交PR补充。

