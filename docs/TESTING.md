# 测试文档

本文档详细说明 Kaka AI Dev 的测试策略和方法。

## 测试统计

| 指标 | 数值 | 说明 |
|------|------|------|
| **总测试数** | 395 个 | 单元测试 + 集成测试 |
| **代码覆盖率** | 89% | 超过目标（85%） |
| **测试文件** | 7 个 | 覆盖所有核心模块 |
| **通过率** | 100% | 394 passed, 1 skipped |

---

## 测试套件

### 单元测试（364 个测试）

| 测试文件 | 测试数量 | 覆盖模块 | 覆盖率 |
|---------|---------|---------|--------|
| `test_webhook_handler.py` | 96 个 | Webhook 处理器 | 100% |
| `test_validators.py` | 78 个 | 验证器（签名验证） | 100% |
| `test_git_service.py` | 69 个 | Git 操作服务 | 100% |
| `test_claude_service.py` | 57 个 | Claude Code CLI 服务 | 98% |
| `test_github_service.py` | 32 个 | GitHub API 服务 | 94% |
| `test_api.py` | 32 个 | API 端点 | 70-94% |

### 集成测试（31 个测试）

| 测试文件 | 测试数量 | 覆盖场景 |
|---------|---------|---------|
| `test_integration.py` | 31 个 | 端到端工作流测试 |

---

## 运行测试

### 运行所有测试

```bash
# 使用 pytest
pytest

# 使用 Makefile
make test
```

### 运行特定测试

```bash
# 运行特定测试文件
pytest tests/test_webhook_handler.py

# 运行特定测试函数
pytest tests/test_webhook_handler.py::test_handle_labeled_event

# 运行特定测试类
pytest tests/test_webhook_handler.py::TestWebhookHandler
```

### 测试选项

```bash
# 详细输出
pytest -v

# 显示打印输出
pytest -s

# 只运行失败的测试
pytest --lf

# 遇到第一个失败时停止
pytest -x

# 运行标记的测试
pytest -m "not slow"
```

---

## 覆盖率报告

### 生成覆盖率报告

```bash
# 生成 HTML 覆盖率报告
pytest --cov=app --cov-report=html

# 在浏览器中查看
make coverage-open
```

### 覆盖率详情

```
模块                              覆盖率
----------------------------------------
app/models/github_events.py       100%
app/services/git_service.py       100%
app/services/webhook_handler.py   100%
app/utils/validators.py           100%
app/services/claude_service.py     98%
app/services/github_service.py     94%
app/config.py                      94%
app/api/health.py                  83%
app/main.py                        70%
app/utils/logger.py                27%
----------------------------------------
TOTAL                              89%
```

---

## 测试编写

### 测试文件结构

```python
# tests/test_services.py
import pytest
from app.services import WebhookHandler

class TestWebhookHandler:
    """Webhook Handler 测试"""

    @pytest.fixture
    def handler(self):
        """创建 handler 实例"""
        return WebhookHandler()

    def test_handle_labeled_event(self, handler):
        """测试处理标签事件"""
        # 测试代码
        pass

    def test_handle_comment_event(self, handler):
        """测试处理评论事件"""
        # 测试代码
        pass
```

### 使用 Fixture

```python
@pytest.fixture
def sample_issue():
    """创建示例 Issue"""
    return Issue(
        number=123,
        title="Test Issue",
        body="Test body"
    )

@pytest.fixture
def sample_webhook_payload():
    """创建示例 Webhook payload"""
    return {
        "action": "labeled",
        "issue": {
            "number": 123,
            "title": "Test"
        }
    }
```

### Mock 外部依赖

```python
from unittest.mock import Mock, patch

def test_github_service(monkeypatch):
    """测试 GitHub Service"""
    mock_github = Mock()
    monkeypatch.setattr("app.services.github_service.Github", mock_github)

    # 测试代码
    service = GitHubService()
    service.get_issue(123)
```

---

## 集成测试

### 测试场景

1. **标签触发流程**
   - Webhook 接收
   - 任务创建
   - 分支创建
   - 代码提交

2. **评论触发流程**
   - 评论解析
   - 命令验证
   - 任务执行

3. **错误处理**
   - Webhook 签名验证失败
   - Git 操作失败
   - Claude CLI 超时

### 运行集成测试

```bash
# 运行所有集成测试
pytest tests/test_integration.py

# 运行特定集成测试
pytest tests/test_integration.py::test_label_workflow
```

---

## 测试最佳实践

### 1. 测试命名

```python
# 好的命名
def test_create_branch_success()
def test_create_branch_invalid_name_raises_error()

# 不好的命名
def test_branch()
def test_1()
```

### 2. 测试结构

```python
def test_feature():
    # Arrange (准备)
    input_data = prepare_test_data()

    # Act (执行)
    result = process_data(input_data)

    # Assert (断言)
    assert result.success is True
```

### 3. 测试隔离

```python
def test_with_fixture(sample_data):
    # 使用 fixture 确保测试隔离
    assert sample_data.status == "pending"
```

### 4. 异步测试

```python
@pytest.mark.asyncio
async def test_async_service():
    result = await async_function()
    assert result is not None
```

---

## 测试数据

### Fixtures 目录

```
tests/
├── fixtures/
│   ├── webhook_payloads.json
│   ├── issues.json
│   └── responses.json
└── conftest.py           # 共享 fixtures
```

### 使用测试数据

```python
import json

@pytest.fixture
def webhook_payload():
    with open("tests/fixtures/webhook_payloads.json") as f:
        return json.load(f)
```

---

## 持续集成

### CI 配置

```yaml
# .github/workflows/test.yml
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
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 下一步

- [开发指南](DEVELOPMENT.md) - 开发文档
