# 多LLM支持文档

本文档说明如何使用和配置多种LLM提供商。

## 支持的LLM提供商

1. **OpenAI** - OpenAI官方API
2. **Anthropic** - Anthropic Claude API
3. **vLLM** - vLLM推理服务器（OpenAI兼容接口）

## 配置方式

### 方式1: 环境变量配置（推荐）

在 `.env` 文件中配置：

```bash
# 选择LLM提供商
LLM_PROVIDER=vllm  # 可选: openai, anthropic, vllm

# OpenAI配置
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_API_BASE=  # 可选：自定义OpenAI兼容端点

# Anthropic配置
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key
ANTHROPIC_MODEL=claude-3-haiku-20240307

# vLLM配置
VLLM_API_BASE=http://localhost:8000/v1
VLLM_API_KEY=sk-local-dev
VLLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct

# 通用LLM参数
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=1024
```

### 方式2: 代码中配置

系统会根据 `LLM_PROVIDER` 自动选择对应的配置：

- `LLM_PROVIDER=openai` → 使用 `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_API_BASE`
- `LLM_PROVIDER=anthropic` → 使用 `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
- `LLM_PROVIDER=vllm` → 使用 `VLLM_API_BASE`, `VLLM_API_KEY`, `VLLM_MODEL`

## API使用

### 1. 使用默认LLM配置

```bash
curl -X POST "http://localhost:8080/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好",
    "session_id": "user123",
    "stream": true
  }'
```

### 2. 临时切换LLM提供商

在请求中指定LLM参数，会临时覆盖默认配置：

```bash
# 使用OpenAI
curl -X POST "http://localhost:8080/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好",
    "session_id": "user123",
    "stream": true,
    "llm_provider": "openai",
    "llm_model": "gpt-4",
    "temperature": 0.7
  }'

# 使用Anthropic
curl -X POST "http://localhost:8080/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "你好",
    "session_id": "user123",
    "stream": true,
    "llm_provider": "anthropic",
    "llm_model": "claude-3-sonnet-20240229"
  }'
```

### 3. 查看支持的提供商

```bash
curl http://localhost:8080/api/v1/llm/providers
```

### 4. 查看当前LLM配置

```bash
curl http://localhost:8080/api/v1/llm/current
```

### 5. 查看特定提供商信息

```bash
curl http://localhost:8080/api/v1/llm/provider/openai
curl http://localhost:8080/api/v1/llm/provider/anthropic
curl http://localhost:8080/api/v1/llm/provider/vllm
```

## 提供商详细信息

### OpenAI

- **名称**: OpenAI
- **模型**: gpt-4, gpt-4-turbo, gpt-3.5-turbo
- **需要API密钥**: 是
- **需要API Base**: 否（可选，用于自定义端点）
- **支持自定义端点**: 是（可用于vLLM或其他OpenAI兼容服务）

**配置示例**:
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-3.5-turbo
```

### Anthropic

- **名称**: Anthropic
- **模型**: claude-3-opus, claude-3-sonnet, claude-3-haiku
- **需要API密钥**: 是
- **需要API Base**: 否
- **支持自定义端点**: 否

**配置示例**:
```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_MODEL=claude-3-haiku-20240307
```

### vLLM

- **名称**: vLLM
- **模型**: 自定义模型路径（如 Qwen/Qwen2.5-1.5B-Instruct）
- **需要API密钥**: 是（通常可以接受任意值）
- **需要API Base**: 是
- **支持自定义端点**: 是

**配置示例**:
```bash
LLM_PROVIDER=vllm
VLLM_API_BASE=http://localhost:8000/v1
VLLM_API_KEY=sk-local-dev
VLLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
```

## 代码使用示例

### 在代码中创建LLM实例

```python
from app.utils.llm_providers import LLMProviderFactory

# 创建OpenAI LLM
llm = LLMProviderFactory.create_llm(
    provider="openai",
    model="gpt-4",
    api_key="sk-your-key"
)

# 创建Anthropic LLM
llm = LLMProviderFactory.create_llm(
    provider="anthropic",
    model="claude-3-sonnet-20240229",
    api_key="sk-ant-your-key"
)

# 创建vLLM LLM
llm = LLMProviderFactory.create_llm(
    provider="vllm",
    model="Qwen/Qwen2.5-1.5B-Instruct",
    api_key="sk-local-dev",
    api_base="http://localhost:8000/v1"
)
```

### 在服务中使用

```python
from app.utils.llm_factory import create_llm_instance

# 创建临时LLM实例（不替换全局实例）
custom_llm = create_llm_instance(
    provider="openai",
    model="gpt-4",
    temperature=0.7
)
```

## 注意事项

1. **API密钥安全**: 生产环境请使用环境变量或密钥管理服务，不要硬编码
2. **成本考虑**: 不同提供商的定价不同，请根据需求选择
3. **性能差异**: vLLM通常提供最佳性能（本地部署），但需要GPU资源
4. **模型兼容性**: 确保选择的模型支持你的用例
5. **临时切换**: 请求中的LLM参数会创建新的LLM实例，可能增加延迟

## 故障排查

### 问题1: LLM初始化失败

**错误**: `Failed to create LLM instance`

**解决方案**:
- 检查API密钥是否正确
- 检查网络连接
- 检查API Base URL是否正确（vLLM）
- 查看日志获取详细错误信息

### 问题2: 模型不存在

**错误**: `Model not found`

**解决方案**:
- 检查模型名称是否正确
- 对于OpenAI，确保账户有权限访问该模型
- 对于vLLM，确保模型已正确加载

### 问题3: API配额超限

**错误**: `Rate limit exceeded`

**解决方案**:
- 检查API配额
- 实现请求限流
- 考虑使用vLLM本地部署

## 最佳实践

1. **生产环境**: 使用环境变量配置，不要硬编码密钥
2. **开发环境**: 可以使用vLLM本地部署，节省成本
3. **测试**: 使用不同的LLM提供商测试响应质量
4. **监控**: 监控不同提供商的延迟和错误率
5. **降级策略**: 实现LLM提供商的自动降级机制

---

*最后更新: 2026*

