# 贡献指南

感谢您对 Kaka AI Dev 的关注！我们欢迎各种形式的贡献。

## 目录

- [如何贡献](#如何贡献)
- [报告 Bug](#报告-bug)
- [提交代码](#提交代码)
- [代码审查准则](#代码审查准则)
- [开发规范](#开发规范)

---

## 如何贡献

### 报告 Bug

1. 在 [Issues](https://github.com/wersling/kaka/issues) 中搜索现有问题
2. 创建新的 Issue，包含：
   - 清晰的标题和描述
   - 复现步骤
   - 预期行为和实际行为
   - 环境信息（Python 版本、操作系统等）

**Bug 报告模板**：

```markdown
### 问题描述
简要描述问题

### 复现步骤
1. 步骤 1
2. 步骤 2
3. ...

### 预期行为
描述预期的行为

### 实际行为
描述实际发生的行为

### 环境信息
- Python 版本:
- 操作系统:
- 版本号:

### 日志
```
粘贴相关日志
```
```

### 提交功能建议

1. 在 Issues 中搜索现有建议
2. 创建新的 Issue，描述你的功能建议
3. 说明使用场景和预期效果

---

## 提交代码

### 1. Fork 项目

```bash
# Fork 并克隆你的 fork
git clone https://github.com/your-username/kaka.git
cd kaka
```

### 2. 创建分支

```bash
# 获取最新代码
git checkout main
git pull upstream/main

# 创建功能分支
git checkout -b feature/your-feature-name
```

### 3. 编写代码

- 遵循现有代码风格
- 添加类型提示
- 编写文档字符串
- 添加测试

### 4. 运行测试

```bash
# 运行所有测试
pytest

# 代码质量检查
black --check .
flake8 app/
mypy app/
```

### 5. 提交更改

```bash
git add .
git commit -m "feat: 添加新功能描述"
```

### 6. 推送到 Fork

```bash
git push origin feature/your-feature-name
```

### 7. 创建 Pull Request

1. 访问 GitHub 上的你的 fork
2. 点击 "Compare & pull request"
3. 填写 PR 模板
4. 关联相关 Issue（使用 `Closes #123`）
5. 等待代码审查

---

## 代码审查准则

### 必须满足的条件

- ✅ 代码通过所有测试
- ✅ 代码覆盖率不降低
- ✅ 遵循代码风格指南
- ✅ 文档完整且准确
- ✅ 无安全漏洞
- ✅ 通过所有代码质量检查

### 审查流程

1. **自动检查**：CI 会自动运行测试和代码检查
2. **人工审查**：维护者会审查代码
3. **反馈**：如有问题，会在 PR 中留言
4. **修改**：根据反馈修改代码
5. **合并**：通过审查后合并到主分支

---

## 开发规范

### Git 提交信息格式

使用 Conventional Commits 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型（type）

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具链相关

### 提交示例

```bash
feat(webhook): 支持 Pull Request 事件

添加对 PR 打开和更新事件的处理

- 添加 PR 事件模型
- 实现 PR 处理器
- 添加单元测试

Closes #123
```

### 代码风格

- 使用 Black 格式化代码
- 遵循 PEP 8 规范
- 使用类型提示
- 编写文档字符串

示例：

```python
from typing import Optional

def process_issue(
    issue_number: int,
    label: str,
    priority: Optional[int] = None
) -> bool:
    """
    处理 GitHub Issue

    Args:
        issue_number: Issue 编号
        label: 触发标签
        priority: 任务优先级（可选）

    Returns:
        处理是否成功

    Raises:
        GitHubError: GitHub API 错误
        ValidationError: 数据验证错误
    """
    # 实现代码
    pass
```

---

## 开发最佳实践

### 1. 使用类型提示

```python
def create_task(issue: Issue) -> Task:
    pass
```

### 2. 编写文档字符串

```python
def create_branch(branch_name: str) -> bool:
    """
    创建新的 Git 分支

    Args:
        branch_name: 分支名称

    Returns:
        是否创建成功
    """
    pass
```

### 3. 使用结构化日志

```python
self.logger.info("处理 Issue", extra={
    "issue_number": issue.number,
    "title": issue.title,
    "labels": [label.name for label in issue.labels]
})
```

### 4. 异常处理

```python
try:
    result = await service.process()
except GitHubError as e:
    self.logger.error(f"GitHub API 错误: {e}")
    raise
except Exception as e:
    self.logger.error(f"未知错误: {e}", exc_info=True)
    raise
```

---

## 测试要求

### 单元测试

所有新功能必须包含单元测试：

```python
def test_process_issue():
    """测试处理 Issue"""
    issue = Issue(number=123, title="Test")
    result = process_issue(issue)
    assert result.success is True
```

### 测试覆盖率

- 目标覆盖率：> 85%
- 新代码覆盖率：100%
- 关键路径必须有测试

---

## 行为准则

### 尊重和包容

- 尊重不同的观点和经验
- 使用友好和包容的语言
- 接受建设性批评

### 协作精神

- 优先考虑社区利益
- 协调解决分歧
- 帮助新成员成长

---

## 许可证

贡献的代码将采用 [MIT 许可证](../LICENSE)。

---

## 致谢

感谢所有贡献者！您们让这个项目变得更好。

---

## 联系方式

- **项目主页**: https://github.com/wersling/kaka
- **问题反馈**: https://github.com/wersling/kaka/issues
- **邮箱**: your-email@example.com
