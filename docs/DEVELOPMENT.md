# 开发指南

本文档面向开发者，说明如何参与 Kaka 的开发。

## 目录

- [本地开发设置](#本地开发设置)
- [常用命令](#常用命令)
- [代码结构](#代码结构)
- [测试](#测试)
- [代码质量](#代码质量)
- [提交规范](#提交规范)

---

## 本地开发设置

### 1. 创建开发环境

```bash
# 克隆项目
git clone https://github.com/wersling/kaka.git
cd kaka

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖（开发模式）
pip install -e .
```

### 2. 配置开发环境变量

复制 `.env.example` 并修改：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入开发环境配置。

### 3. 启动开发服务器

**方式 1: 使用 VSCode 调试器（推荐）**

1. 按 `F5` 或点击侧边栏的"运行和调试"
2. 选择"运行 FastAPI (调试模式)"
3. 服务将在 `http://localhost:8000` 启动
4. 支持断点调试和热重载

**方式 2: 使用 kaka CLI**

```bash
# 配置服务
kaka configure

# 启动服务（开发模式）
kaka start --reload
```

**方式 3: 直接使用 uvicorn**

```bash
# 方式 1: 使用 uvicorn
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 方式 2: 运行主模块
python -m app.main
```

---

## 常用命令

### 用户命令（kaka CLI）

| 命令 | 说明 |
|------|------|
| `kaka start` | 启动服务 |
| `kaka start --reload` | 启动开发服务器（自动重载） |
| `kaka configure` | 打开配置向导 |
| `kaka status` | 查看配置状态 |
| `kaka logs` | 查看日志 |
| `kaka config export` | 导出配置 |
| `kaka config import` | 导入配置 |

### 开发命令（Makefile）

| 命令 | 说明 |
|------|------|
| `make help` | 显示帮助信息 |
| `make test` | 运行所有测试 |
| `make test-fast` | 快速测试（跳过慢速测试） |
| `make coverage` | 生成测试覆盖率报告 |
| `make lint` | 代码检查 |
| `make format` | 代码格式化 |
| `make check` | 代码检查并格式化 |
| `make clean` | 清理临时文件 |
| `make clean-all` | 完全清理（包括虚拟环境） |

---

## 代码结构

### 目录结构

```
kaka/
├── app/                       # 应用主目录
│   ├── main.py               # FastAPI 应用入口
│   ├── config.py             # 配置管理
│   ├── models/               # Pydantic 数据模型
│   │   └── github_events.py  # GitHub 事件模型
│   ├── services/             # 核心业务服务
│   │   ├── webhook_handler.py  # Webhook 处理
│   │   ├── claude_service.py   # Claude Code CLI 调用
│   │   ├── git_service.py      # Git 操作
│   │   └── github_service.py   # GitHub API 操作
│   ├── api/                  # API 路由
│   │   ├── health.py         # 健康检查
│   │   ├── tasks.py          # 任务管理 API
│   │   ├── config.py         # 配置管理 API
│   │   └── dashboard.py      # Dashboard 路由
│   ├── db/                   # 数据库
│   │   ├── database.py       # 数据库连接
│   │   └── models.py         # ORM 模型
│   ├── utils/                # 工具函数
│   │   ├── logger.py         # 日志工具
│   │   ├── validators.py     # Webhook 验证
│   │   └── concurrency.py    # 并发管理
│   └── cli.py                # 命令行工具
├── config/                   # 配置文件
│   └── config.yaml           # 主配置文件
├── scripts/                  # 开发和测试脚本
├── dev_setup.sh              # 开发环境初始化脚本
├── tests/                    # 测试套件
├── logs/                     # 日志文件
├── templates/                # HTML 模板
│   ├── dashboard_enhanced.html
│   └── config_wizard.html
├── requirements.txt          # Python 依赖
├── pyproject.toml           # 项目配置
└── Makefile                  # 开发命令
```

### 核心模块说明

| 模块 | 职责 |
|------|------|
| `app/main.py` | FastAPI 应用入口，路由注册，中间件配置 |
| `app/config.py` | 配置加载和管理，使用 Pydantic Settings |
| `app/models/` | Pydantic 数据模型定义 |
| `app/services/` | 核心业务逻辑实现 |
| `app/api/` | API 路由和端点定义 |
| `app/db/` | 数据库模型和连接 |
| `app/utils/` | 工具函数和辅助类 |
| `app/cli.py` | 命令行工具（kaka CLI） |

---

## 测试

### 运行测试

```bash
# 运行所有测试
make test

# 快速测试（跳过慢速测试）
make test-fast

# 运行特定测试文件
make test-one FILE=tests/test_validators.py

# 运行单元测试
make test-unit

# 运行集成测试
make test-integration
```

### 测试覆盖率

```bash
# 生成覆盖率报告
make coverage

# 在浏览器中打开覆盖率报告
make coverage-open
```

### 测试文件结构

```
tests/
├── test_webhook_handler.py   # Webhook 处理器测试
├── test_validators.py        # 验证器测试
├── test_git_service.py       # Git 服务测试
├── test_claude_service.py    # Claude 服务测试
├── test_github_service.py    # GitHub 服务测试
├── test_api.py               # API 端点测试
└── test_integration.py       # 集成测试
```

### 测试统计

| 指标 | 数值 |
|------|------|
| 总测试数 | 395 个 |
| 代码覆盖率 | 89% |
| 通过率 | 100% |

---

## 代码质量

### 代码检查

```bash
# 运行代码检查
make lint

# 格式化代码
make format

# 代码检查并格式化
make check
```

### 代码质量工具

| 工具 | 用途 |
|------|------|
| **Black** | 代码格式化 |
| **Flake8** | 代码检查 |
| **MyPy** | 类型检查 |
| **Pytest** | 测试框架 |

### 代码风格指南

项目遵循以下规范：

1. **PEP 8** - Python 代码风格指南
2. **Black** - 代码格式化（行长度 100）
3. **类型提示** - 使用 Python 类型提示
4. **文档字符串** - Google 风格文档字符串

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

## 提交规范

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

### 提交前检查

```bash
# 运行测试
make test

# 代码检查
make check

# 查看修改的文件
git status
```

---

## 开发工作流

### 1. 创建功能分支

```bash
git checkout -b feature/your-feature-name
```

### 2. 开发和测试

```bash
# 启动开发服务器
kaka start --reload

# 运行测试
make test

# 代码检查
make check
```

### 3. 提交更改

```bash
git add .
git commit -m "feat: 添加新功能"
```

### 4. 推送到远程

```bash
git push origin feature/your-feature-name
```

### 5. 创建 Pull Request

访问 GitHub 创建 Pull Request。

---

## 调试技巧

### VSCode 调试配置

项目包含完整的 VSCode 调试配置，支持以下调试模式：

1. **运行 FastAPI (调试模式)** - 启用热重载，支持断点调试
2. **运行 FastAPI (无热重载)** - 稳定调试环境
3. **运行 Python 文件** - 调试当前打开的文件
4. **运行 pytest** - 调试测试用例

配置文件：[`.vscode/launch.json`](../.vscode/launch.json)

### 启用调试模式

在 `config/config.yaml` 中设置：

```yaml
logging:
  level: "DEBUG"
```

### 查看日志

服务启动时会显示日志文件地址：

```
📝 日志文件: logs/kaka.log
```

查看日志的方式：

```bash
# 实时查看日志
tail -f logs/kaka.log

# 查看最近 20 行
tail -n 20 logs/kaka.log

# 使用 kaka CLI
kaka logs

# 只看错误日志
grep ERROR logs/kaka.log
```

### 使用 Python 调试器

```python
# 在代码中设置断点
import pdb; pdb.set_trace()

# 或使用 ipdb（需要安装）
pip install ipdb
import ipdb; ipdb.set_trace()
```

---

## 相关文档

- [使用指南](USAGE.md) - 使用说明
- [配置说明](CONFIGURATION.md) - 详细配置
- [部署指南](DEPLOYMENT.md) - 生产部署
- [架构文档](ARCHITECTURE.md) - 系统架构
- [日志系统](LOGGING.md) - 日志配置和使用
- [测试文档](TESTING.md) - 测试策略
