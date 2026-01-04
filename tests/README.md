# 测试文档

本目录包含 Enterprise AI Backend 的测试套件。

## 测试结构

```
tests/
├── conftest.py              # Pytest配置和共享fixtures
├── test_core/              # 核心功能测试
│   ├── test_config.py      # 配置测试
│   ├── test_retry.py       # 重试机制测试
│   ├── test_cache.py       # 缓存测试
│   └── test_rate_limiter.py # 速率限制测试
├── test_api/               # API测试
│   ├── test_health.py      # 健康检查测试
│   └── test_chat.py        # 聊天API测试
└── test_services/          # 服务层测试
    └── test_memory_service.py # 记忆服务测试
```

## 运行测试

### 运行所有测试

```bash
pytest
```

### 运行特定测试文件

```bash
pytest tests/test_core/test_config.py
```

### 运行特定测试类

```bash
pytest tests/test_core/test_config.py::TestSettings
```

### 运行特定测试方法

```bash
pytest tests/test_core/test_config.py::TestSettings::test_settings_load
```

### 运行带标记的测试

```bash
# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 运行异步测试
pytest -m asyncio
```

### 详细输出

```bash
pytest -v
```

### 显示print输出

```bash
pytest -s
```

### 覆盖率报告

```bash
# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html

# 查看HTML报告
open htmlcov/index.html
```

### 并行运行测试

```bash
# 安装pytest-xdist
pip install pytest-xdist

# 并行运行
pytest -n auto
```

## 测试配置

### pytest.ini

测试配置文件包含：
- 测试路径
- 文件/类/函数模式
- 输出选项
- 标记定义

### .coveragerc

覆盖率配置文件包含：
- 源代码路径
- 排除模式
- 报告格式

## Fixtures

### 共享Fixtures (conftest.py)

- `client`: FastAPI测试客户端
- `mock_redis`: 模拟Redis客户端
- `mock_milvus`: 模拟Milvus客户端
- `mock_llm`: 模拟LLM
- `mock_embed_model`: 模拟Embedding模型
- `sample_session_id`: 示例会话ID
- `sample_query`: 示例查询
- `sample_document_content`: 示例文档内容

## 测试类型

### 单元测试

测试单个函数或类的行为，使用模拟对象隔离依赖。

```python
def test_cache_set_and_get():
    cache = SimpleCache()
    cache.set("key", "value")
    assert cache.get("key") == "value"
```

### 集成测试

测试多个组件的集成，可能涉及真实的外部服务。

```python
@pytest.mark.integration
async def test_chat_with_real_llm():
    # 需要真实的LLM服务
    pass
```

### 异步测试

测试异步函数，使用`@pytest.mark.asyncio`标记。

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

## 模拟(Mocking)

### 使用unittest.mock

```python
from unittest.mock import patch, MagicMock

@patch('app.services.chat_service.ChatService.chat_stream')
def test_with_mock(mock_chat_stream):
    mock_chat_stream.return_value = "mocked response"
    # 测试代码
```

### 使用fixtures模拟

```python
def test_with_fixture_mock(mock_redis):
    mock_redis.ping.return_value = True
    # 测试代码
```

## 最佳实践

### 1. 测试命名

使用描述性的测试名称：

```python
# Good
def test_rate_limiter_allows_requests_within_limit():
    pass

# Bad
def test_1():
    pass
```

### 2. 测试隔离

每个测试应该独立，不依赖其他测试：

```python
def setup_method(self):
    """每个测试前重置状态"""
    self.cache = SimpleCache()
    self.cache.clear()
```

### 3. 使用fixtures

将重复的设置代码提取到fixtures：

```python
@pytest.fixture
def configured_limiter():
    limiter = RateLimiter()
    limiter.set_default_rule(requests=10, window=60)
    return limiter
```

### 4. 测试边界条件

测试正常情况、边界条件和错误情况：

```python
def test_empty_input():
    pass

def test_maximum_input():
    pass

def test_invalid_input():
    pass
```

### 5. 断言消息

为断言添加描述性消息：

```python
assert result == expected, f"Expected {expected}, got {result}"
```

## 持续集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run tests
      run: pytest --cov=app --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## 调试测试

### 使用pdb

```python
def test_with_debugger():
    import pdb; pdb.set_trace()
    # 测试代码
```

### 使用pytest --pdb

```bash
# 在失败时自动进入调试器
pytest --pdb
```

### 打印调试信息

```bash
# 显示print输出
pytest -s

# 显示日志
pytest --log-cli-level=DEBUG
```

## 常见问题

### Q: 测试运行很慢

A: 使用并行测试或跳过慢速测试：

```bash
pytest -n auto  # 并行
pytest -m "not slow"  # 跳过慢速测试
```

### Q: 模拟不生效

A: 确保模拟路径正确：

```python
# 模拟导入位置，而不是定义位置
@patch('app.services.chat_service.SomeClass')  # Correct
@patch('some_module.SomeClass')  # Wrong
```

### Q: 异步测试失败

A: 确保使用正确的异步测试标记：

```python
@pytest.mark.asyncio
async def test_async():
    pass
```

## 贡献指南

添加新测试时：

1. 将测试放在正确的目录
2. 使用描述性的测试名称
3. 添加docstring说明测试目的
4. 确保测试独立且可重复
5. 更新本README如果添加新的测试类型

---

**持续更新中...** 欢迎提交PR改进测试套件！

