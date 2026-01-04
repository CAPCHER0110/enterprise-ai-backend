# 部署指南

本文档提供详细的部署指导，帮助您在不同环境中部署 Enterprise AI Backend。

## 📋 目录

- [部署前准备](#部署前准备)
- [本地开发环境](#本地开发环境)
- [Docker部署](#docker部署)
- [生产环境部署](#生产环境部署)
- [配置说明](#配置说明)
- [性能调优](#性能调优)
- [监控和日志](#监控和日志)

## 部署前准备

### 系统要求

- **CPU**: 4核或以上
- **内存**: 8GB或以上（建议16GB+）
- **存储**: 50GB或以上
- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+) 或 macOS

### 依赖服务

1. **向量数据库** (选择其一):
   - Milvus 2.3+ (推荐)
   - ChromaDB 0.4+
   - Pinecone
   - Qdrant 1.6+

2. **缓存/记忆存储**:
   - Redis 5.0+ (必需)

3. **LLM服务** (选择其一):
   - vLLM Server (自托管)
   - OpenAI API
   - Anthropic API

## 本地开发环境

### 1. 克隆代码

```bash
git clone https://github.com/your-username/enterprise-ai-backend.git
cd enterprise-ai-backend
```

### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 生产依赖
pip install -r requirements.txt

# 开发依赖
pip install -r requirements-dev.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑.env文件，配置你的服务
```

### 5. 启动服务

```bash
# 使用uvicorn启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# 或使用Dockerfile
docker build -t enterprise-ai-backend .
docker run -p 8080:8080 --env-file .env enterprise-ai-backend
```

### 6. 验证部署

```bash
# 健康检查
curl http://localhost:8080/health

# 查看API文档
open http://localhost:8080/docs
```

## Docker部署

### 使用Docker Compose（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 停止服务
docker-compose down
```

### 单独使用Docker

```bash
# 构建镜像
docker build -t enterprise-ai-backend:latest .

# 运行容器
docker run -d \
  --name enterprise-ai \
  -p 8080:8080 \
  --env-file .env \
  enterprise-ai-backend:latest

# 查看日志
docker logs -f enterprise-ai

# 停止容器
docker stop enterprise-ai
docker rm enterprise-ai
```

## 生产环境部署

### 环境配置清单

在生产环境部署前，请确保完成以下配置：

#### 1. 安全配置 ✅

```bash
# .env
# 启用API密钥验证
API_KEY_REQUIRED=true
API_KEYS=["sk-prod-xxx", "sk-prod-yyy"]

# CORS配置（设置为你的前端域名）
ALLOWED_ORIGINS=["https://yourdomain.com"]

# 启用速率限制
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# 日志级别
LOG_LEVEL=INFO
```

#### 2. 数据库配置 ✅

```bash
# Milvus（生产环境）
MILVUS_URI=http://milvus-cluster:19530
MILVUS_TOKEN=your-auth-token
MILVUS_COLLECTION=production_knowledge

# Redis（生产环境）
REDIS_URL=redis://:password@redis-cluster:6379/0
REDIS_MAX_CONNECTIONS=50
```

#### 3. LLM配置 ✅

```bash
# 选择LLM提供商
LLM_PROVIDER=openai  # 或 anthropic, vllm

# OpenAI
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4

# 超时和重试
REQUEST_TIMEOUT=60
RETRY_MAX_ATTEMPTS=3
```

#### 4. 性能配置 ✅

```bash
# 缓存
ENABLE_CACHE=true
CACHE_TTL=3600

# 批量操作
BATCH_SIZE=100

# 连接池
REDIS_MAX_CONNECTIONS=50
```

### 使用Kubernetes部署

创建 `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: enterprise-ai-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: enterprise-ai-backend
  template:
    metadata:
      labels:
        app: enterprise-ai-backend
    spec:
      containers:
      - name: api
        image: your-registry/enterprise-ai-backend:latest
        ports:
        - containerPort: 8080
        env:
        - name: MILVUS_URI
          value: "http://milvus:19530"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        envFrom:
        - secretRef:
            name: ai-backend-secrets
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: enterprise-ai-backend
spec:
  selector:
    app: enterprise-ai-backend
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

应用配置:

```bash
# 创建secrets
kubectl create secret generic ai-backend-secrets \
  --from-literal=OPENAI_API_KEY=sk-xxx \
  --from-literal=MILVUS_TOKEN=xxx

# 部署
kubectl apply -f deployment.yaml

# 查看状态
kubectl get pods
kubectl logs -f deployment/enterprise-ai-backend

# 查看服务
kubectl get svc enterprise-ai-backend
```

### 使用Nginx反向代理

创建 `/etc/nginx/sites-available/enterprise-ai`:

```nginx
upstream backend {
    server 127.0.0.1:8080;
    # 如果有多个实例
    # server 127.0.0.1:8081;
    # server 127.0.0.1:8082;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # SSL配置（推荐使用Let's Encrypt）
    # listen 443 ssl http2;
    # ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # 健康检查
    location /health {
        proxy_pass http://backend/health;
        access_log off;
    }
}
```

启用配置:

```bash
sudo ln -s /etc/nginx/sites-available/enterprise-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 配置说明

### 环境变量优先级

1. 系统环境变量（最高优先级）
2. `.env` 文件
3. 代码中的默认值（最低优先级）

### 必需配置项

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `LLM_PROVIDER` | LLM提供商 | `openai`, `anthropic`, `vllm` |
| `LLM_API_KEY` | LLM API密钥 | `sk-xxx` |
| `MILVUS_URI` | Milvus连接地址 | `http://milvus:19530` |
| `REDIS_URL` | Redis连接地址 | `redis://localhost:6379/0` |

### 可选配置项

详见 `.env.example` 文件。

## 性能调优

### 1. 应用层优化

```bash
# 增加worker数量（基于CPU核心数）
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8080 \
  --timeout 120

# 或使用uvicorn
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8080 \
  --workers 4 \
  --loop uvloop
```

### 2. Redis优化

```bash
# 增加最大连接数
REDIS_MAX_CONNECTIONS=100

# 启用连接池
# （已在代码中实现）
```

### 3. Milvus优化

```bash
# 调整索引类型（根据数据规模）
# IVF_FLAT: 小数据集（< 100万）
# IVF_SQ8: 中等数据集（100万-1000万）
# HNSW: 大数据集（> 1000万）

# 调整相似度搜索参数
SIMILARITY_TOP_K=5  # 根据需求调整
```

### 4. LLM优化

```bash
# 调整超时时间
REQUEST_TIMEOUT=60

# 启用缓存
ENABLE_CACHE=true
CACHE_TTL=3600

# 调整批量大小
BATCH_SIZE=100
```

## 监控和日志

### 日志收集

#### 1. 文件日志

```bash
# 配置日志输出
LOG_LEVEL=INFO

# 日志会输出到stdout，可以重定向到文件
uvicorn app.main:app > /var/log/enterprise-ai/app.log 2>&1
```

#### 2. 使用ELK Stack

```yaml
# docker-compose.yml 添加
filebeat:
  image: docker.elastic.co/beats/filebeat:8.5.0
  volumes:
    - /var/log/enterprise-ai:/var/log/app:ro
    - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
```

### 健康检查

```bash
# 基本健康检查
curl http://localhost:8080/health

# 详细健康检查（包含依赖服务状态）
curl http://localhost:8080/health | jq
```

### 指标监控

```bash
# 获取应用指标
curl http://localhost:8080/metrics

# 集成Prometheus（见下一节）
```

## 故障排查

详见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## 安全最佳实践

1. ✅ **启用API密钥验证**
2. ✅ **使用HTTPS**
3. ✅ **配置CORS白名单**
4. ✅ **启用速率限制**
5. ✅ **定期更新依赖**
6. ✅ **使用环境变量存储敏感信息**
7. ✅ **定期备份数据**

## 备份和恢复

### 备份

```bash
# 备份Milvus数据
# （使用Milvus官方备份工具）

# 备份Redis数据
redis-cli --rdb /backup/dump.rdb

# 备份配置
cp .env /backup/env-backup-$(date +%Y%m%d)
```

### 恢复

```bash
# 恢复Redis数据
redis-cli --rdb /backup/dump.rdb

# 恢复配置
cp /backup/env-backup-20240101 .env
```

## 扩展性

### 水平扩展

1. 部署多个API实例
2. 使用负载均衡器（Nginx/HAProxy）
3. 使用Redis分布式锁（如果需要）
4. 使用分布式速率限制（Redis实现）

### 垂直扩展

1. 增加CPU和内存
2. 优化worker数量
3. 调整连接池大小

---

**需要帮助？** 查看 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) 或提交Issue。

