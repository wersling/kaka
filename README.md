# AI 开发调度服务 (ai-dev-scheduler)

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://img.shields.io/badge/tests-395%20passed-success.svg)](https://github.com/your-org/ai-dev-scheduler)
[![Coverage](https://img.shields.io/badge/coverage-89%25-brightgreen.svg)](https://github.com/your-org/ai-dev-scheduler)

> 基于 FastAPI 的自动化开发工作流系统 - 通过 GitHub Webhook 触发 Claude Code CLI 进行 AI 开发，实现从 Issue 到 PR 的完整自动化流程。

---

## 目录

- [功能特性](#-功能特性)
- [测试覆盖](#-测试覆盖)
- [技术架构](#-技术架构)
- [快速开始](#-快速开始)
- [配置说明](#-配置说明)
- [使用指南](#-使用指南)
- [开发指南](#-开发指南)
  - [本地 Webhook 测试](#-本地-webhook-测试)
- [API 文档](#-api-文档)
- [部署指南](#-部署指南)
- [故障排查](#-故障排查)
- [安全建议](#-安全建议)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## 功能特性

### 核心功能

- **智能 Webhook 接收** - 接收并验证 GitHub Webhook 事件（Issues、Issue Comments）
- **多种触发方式** - 支持标签触发（`ai-dev`）和评论触发（`/ai develop`）
- **AI 开发调度** - 自动调用本地 Claude Code CLI 进行开发任务
- **Git 自动化** - 自动创建分支、提交代码、推送到远程仓库
- **智能 PR 创建** - 根据开发内容自动生成 Pull Request
- **并发任务管理** - 支持任务队列和并发控制
- **完整日志追踪** - 详细的日志记录和任务状态追踪

### 技术亮点

- 异步处理架构（FastAPI + asyncio）
- HMAC-SHA256 Webhook 签名验证
- 结构化日志记录
- 灵活的配置管理（YAML + 环境变量）
- Pydantic 数据验证
- 优雅的错误处理和异常恢复

---

## 测试覆盖

### 测试统计

| 指标 | 数值 | 说明 |
|------|------|------|
| **总测试数** | 395 个 | 单元测试 + 集成测试 |
| **代码覆盖率** | 89% | 超过目标（85%） |
| **测试文件** | 7 个 | 覆盖所有核心模块 |
| **通过率** | 100% | 394 passed, 1 skipped |

### 测试套件详情

#### 单元测试（364 个测试）

| 测试文件 | 测试数量 | 覆盖模块 | 覆盖率 |
|---------|---------|---------|--------|
| `test_webhook_handler.py` | 96 个 | Webhook 处理器 | 100% |
| `test_validators.py` | 78 个 | 验证器（签名验证） | 100% |
| `test_git_service.py` | 69 个 | Git 操作服务 | 100% |
| `test_claude_service.py` | 57 个 | Claude Code CLI 服务 | 98% |
| `test_github_service.py` | 32 个 | GitHub API 服务 | 94% |
| `test_api.py` | 32 个 | API 端点 | 70-94% |

#### 集成测试（31 个测试）

| 测试文件 | 测试数量 | 覆盖场景 |
|---------|---------|---------|
| `test_integration.py` | 31 个 | 端到端工作流测试 |

### 测试覆盖详情

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

### 运行测试

```bash
# 运行所有测试
make test

# 生成覆盖率报告
make coverage

# 在浏览器中查看覆盖率
make coverage-open

# 运行特定测试文件
pytest tests/test_webhook_handler.py -v

# 运行特定测试函数
pytest tests/test_webhook_handler.py::test_handle_labeled_event -v
```

---

## 技术架构

### 技术栈

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **Web 框架** | FastAPI | ≥0.104.1 | 高性能异步 Web 框架 |
| **服务器** | Uvicorn | ≥0.24.0 | ASGI 服务器 |
| **GitHub API** | PyGithub | ≥2.1.1 | GitHub API 客户端 |
| **Git 操作** | GitPython | ≥3.1.40 | Git 库 |
| **配置管理** | PyYAML + Pydantic | ≥2.5.0 | 配置和验证 |
| **安全加密** | Cryptography | ≥41.0.7 | 加密和签名验证 |
| **日志** | Structlog | ≥23.2.0 | 结构化日志 |
| **测试** | Pytest | ≥7.4.3 | 测试框架 |

### 系统架构

```
┌─────────────┐      Webhook      ┌──────────────┐
│   GitHub    │ ─────────────────▶│ AI Scheduler │
└─────────────┘                   └──────┬───────┘
                                         │
                              ┌──────────▼──────────┐
                              │  Webhook Handler    │
                              └──────────┬──────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
            ┌───────▼───────┐    ┌──────▼──────┐    ┌───────▼───────┐
            │ GitHub Service│    │ Git Service │    │Claude Service │
            └───────────────┘    └─────────────┘    └───────────────┘
                    │                    │                    │
            ┌───────▼───────┐    ┌──────▼──────┐    ┌───────▼───────┐
            │   GitHub API  │    │   Local Git │    │Claude Code CLI│
            └───────────────┘    └─────────────┘    └───────────────┘
```

### 项目结构

```
ai-dev-scheduler/
├── app/
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── models/                 # Pydantic 数据模型
│   │   └── github_events.py    # GitHub 事件模型
│   ├── services/               # 核心业务服务
│   │   ├── webhook_handler.py  # Webhook 处理器
│   │   ├── claude_service.py   # Claude Code CLI 服务
│   │   ├── git_service.py      # Git 操作服务
│   │   └── github_service.py   # GitHub API 服务
│   ├── api/                    # API 路由
│   │   └── health.py           # 健康检查端点
│   └── utils/                  # 工具函数
│       ├── logger.py           # 日志工具
│       └── validators.py       # Webhook 验证器
├── config/
│   └── config.yaml             # 配置文件
├── scripts/
│   ├── setup.sh                # 初始化脚本
│   └── dev.sh                  # 开发启动脚本
├── tests/                      # 测试套件
│   ├── test_api.py             # API 端点测试（32 个）
│   ├── test_webhook_handler.py # Webhook 处理器测试（96 个）
│   ├── test_validators.py      # 验证器测试（78 个）
│   ├── test_git_service.py     # Git 服务测试（69 个）
│   ├── test_claude_service.py  # Claude 服务测试（57 个）
│   ├── test_github_service.py  # GitHub 服务测试（32 个）
│   └── test_integration.py     # 集成测试（31 个）
├── logs/                       # 日志文件目录
├── requirements.txt            # Python 依赖
├── pyproject.toml             # 项目配置
├── Makefile                    # 自动化命令
├── .env                       # 环境变量（需手动创建）
└── README.md                  # 本文档
```

---

## 快速开始

### 前置要求

确保您的系统已安装以下软件：

- **Python**: 3.11 或更高版本
- **Node.js**: 18+ （用于安装 Claude Code CLI）
- **Git**: 2.0+ （用于版本控制）
- **pip**: 最新版本

```bash
# 检查 Python 版本
python3 --version

# 检查 Node.js 版本
node --version

# 检查 Git 版本
git --version
```

### 安装步骤

#### 方式一：使用 Makefile（推荐）

```bash
# 1. 查看所有可用命令
make help

# 2. 快速开始（自动安装依赖、验证配置、运行测试）
make quickstart

# 3. 启动开发服务器
make dev
```

#### 方式二：手动安装

##### 1. 克隆项目

```bash
git clone https://github.com/your-org/ai-dev-scheduler.git
cd ai-dev-scheduler
```

#### 2. 运行初始化脚本

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

该脚本会自动：
- 检查 Python 版本
- 创建虚拟环境
- 安装 Python 依赖
- 创建必要的目录（`logs/`、`config/`）
- 生成 `.env` 配置文件模板
- 设置脚本执行权限

#### 3. 安装 Claude Code CLI

```bash
npm install -g @anthropic/claude-code
```

验证安装：

```bash
claude-code --version
```

#### 4. 配置环境变量

编辑项目根目录下的 `.env` 文件：

```bash
# GitHub 配置
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here
GITHUB_TOKEN=ghp_your-token-here
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=your-repo

# 代码仓库路径（绝对路径）
REPO_PATH=/path/to/your/local/repo

# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-your-key-here

# 可选：基本认证
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=your-secure-password
```

#### 5. 启动服务

```bash
# 激活虚拟环境
source venv/bin/activate

# 启动开发服务器
./scripts/dev.sh
```

或直接运行：

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 6. 验证安装

服务启动后，访问以下 URL：

- **API 文档 (Swagger UI)**: http://localhost:8000/docs
- **替代文档 (ReDoc)**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health
- **根端点**: http://localhost:8000/

预期输出：

```json
{
  "service": "AI 开发调度服务",
  "version": "0.1.0",
  "status": "running",
  "docs": "/docs",
  "health": "/health"
}
```

---

## 配置说明

### 环境变量

创建 `.env` 文件并配置以下变量：

| 变量名 | 必需 | 说明 | 示例 |
|--------|------|------|------|
| `GITHUB_WEBHOOK_SECRET` | ✅ | GitHub Webhook 密钥 | `random-secret-string` |
| `GITHUB_TOKEN` | ✅ | GitHub Personal Access Token | `ghp_xxxxxxxxxxxx` |
| `GITHUB_REPO_OWNER` | ✅ | GitHub 仓库所有者 | `your-username` |
| `GITHUB_REPO_NAME` | ✅ | GitHub 仓库名称 | `your-repo` |
| `REPO_PATH` | ✅ | 本地仓库绝对路径 | `/Users/you/projects/repo` |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API 密钥 | `sk-ant-xxxxxxxxxxxx` |
| `BASIC_AUTH_USERNAME` | ❌ | 基本认证用户名 | `admin` |
| `BASIC_AUTH_PASSWORD` | ❌ | 基本认证密码 | `secure-password` |
| `SLACK_WEBHOOK_URL` | ❌ | Slack 通知 Webhook | `https://hooks.slack.com/...` |
| `TELEGRAM_BOT_TOKEN` | ❌ | Telegram Bot Token | `your-bot-token` |
| `TELEGRAM_CHAT_ID` | ❌ | Telegram Chat ID | `your-chat-id` |

### config.yaml 配置

配置文件位于 `config/config.yaml`，支持以下配置项：

#### 服务器配置

```yaml
server:
  host: "0.0.0.0"      # 监听地址
  port: 8000           # 监听端口
  reload: false        # 生产环境设为 false
  workers: 1           # 工作进程数
```

#### GitHub 配置

```yaml
github:
  webhook_secret: "${GITHUB_WEBHOOK_SECRET}"  # 从环境变量读取
  token: "${GITHUB_TOKEN}"
  repo_owner: "${GITHUB_REPO_OWNER}"
  repo_name: "${GITHUB_REPO_NAME}"
  trigger_label: "ai-dev"           # 触发标签
  trigger_command: "/ai develop"    # 触发命令
```

#### Claude Code 配置

```yaml
claude:
  timeout: 1800          # 执行超时（秒），默认 30 分钟
  max_retries: 2         # 最大重试次数
  auto_test: true        # 是否自动运行测试
  cli_path: "claude-code"  # CLI 路径
  cwd: null              # 工作目录（可选）
```

#### 日志配置

```yaml
logging:
  level: "INFO"                     # 日志级别
  file: "logs/ai-scheduler.log"     # 日志文件路径
  max_bytes: 10485760               # 文件大小限制（10MB）
  backup_count: 5                   # 保留的日志文件数
  console: true                     # 是否输出到控制台
  json: false                       # 是否使用 JSON 格式
```

#### 安全配置

```yaml
security:
  enable_basic_auth: false                # 是否启用基本认证
  basic_auth_username: "${BASIC_AUTH_USERNAME:}"
  basic_auth_password: "${BASIC_AUTH_PASSWORD:}"
  ip_whitelist: []                        # IP 白名单（可选）
  cors_origins:                           # CORS 允许的来源
    - "http://localhost:3000"
    - "http://localhost:8000"
```

### GitHub Webhook 配置

#### 创建 Webhook

1. 进入 GitHub 仓库设置页面：`Settings` → `Webhooks` → `Add webhook`
2. 配置以下参数：

| 参数 | 值 |
|------|-----|
| **Payload URL** | `https://your-domain.com/webhook/github` |
| **Content type** | `application/json` |
| **Secret** | 与 `GITHUB_WEBHOOK_SECRET` 相同 |
| **Events** | 选择以下事件： |
| | • Issues |
| | • Issue comments |

3. 点击 "Add webhook" 完成创建

#### 生成 Webhook Secret

```bash
# 使用 openssl 生成随机密钥
openssl rand -hex 32

# 或使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 使用指南

### 触发方式

#### 方式 1: 标签触发（推荐）

1. 在 GitHub Issue 中添加 `ai-dev` 标签
2. 系统自动接收 Webhook 并开始处理

```
Issue #123: 修复登录 Bug
Labels: ai-dev, bug
```

#### 方式 2: 评论触发

1. 在 GitHub Issue 中评论 `/ai develop`
2. 系统自动接收评论事件并开始处理

```
User123: /ai develop
```

### 工作流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                        自动化开发流程                                │
└─────────────────────────────────────────────────────────────────────┘

1. 触发事件
   ├─ 标签触发: 添加 ai-dev 标签
   └─ 评论触发: 发送 /ai develop 命令

2. Webhook 接收
   ├─ 验证签名（HMAC-SHA256）
   ├─ 解析事件类型和数据
   └─ 验证触发条件

3. 任务创建
   ├─ 生成分支名: ai/feature-{issue_number}-{timestamp}
   ├─ 创建 Commit 信息
   └─ 初始化任务队列

4. AI 开发
   ├─ Claude Code CLI 分析需求
   ├─ 自动编写代码
   ├─ 运行测试（如果启用）
   └─ 提交代码

5. Git 操作
   ├─ 创建新分支
   ├─ 提交代码
   └─ 推送到远程仓库

6. PR 创建
   ├─ 生成 PR 标题和描述
   ├─ 关联原 Issue
   └─ 通知相关人员

7. 完成
   └─ 返回任务结果和日志
```

### 查看日志

#### 实时日志

```bash
# 查看实时日志
tail -f logs/ai-scheduler.log

# 或使用开发模式启动（日志输出到控制台）
./scripts/dev.sh
```

#### 日志级别

日志级别在 `config/config.yaml` 中配置：

- `DEBUG`: 详细的调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

#### 日志格式

```
2024-01-08 10:30:45 - app.main - INFO - ➤ POST /webhook/github
2024-01-08 10:30:45 - app.services.webhook_handler - INFO - 收到 Webhook: delivery=123456-7890, event=labeled
2024-01-08 10:30:46 - app.services.github_service - INFO - Issue #123: 修复登录 Bug
2024-01-08 10:30:47 - app.services.git_service - INFO - 创建分支: ai/feature-123-1704685847
```

---

## 开发指南

### 常用命令（Makefile）

项目提供了 Makefile 来简化常见操作。使用 `make help` 查看所有可用命令。

#### 开发相关

| 命令 | 说明 |
|------|------|
| `make help` | 显示帮助信息 |
| `make quickstart` | 快速开始（安装+验证+测试） |
| `make init` | 初始化项目 |
| `make install` | 安装依赖 |
| `make dev` | 启动开发服务器 |
| `make validate` | 验证配置文件 |
| `make info` | 显示项目信息 |

#### 测试相关

| 命令 | 说明 |
|------|------|
| `make test` | 运行所有测试 |
| `make test-fast` | 快速测试（跳过慢速测试） |
| `make test-unit` | 运行单元测试 |
| `make test-integration` | 运行集成测试 |
| `make test-one FILE=tests/test_xxx.py` | 运行特定测试文件 |
| `make coverage` | 生成测试覆盖率报告 |
| `make coverage-open` | 在浏览器中查看覆盖率 |
| `make report` | 生成完整测试报告 |

#### 代码质量

| 命令 | 说明 |
|------|------|
| `make lint` | 运行代码检查（flake8） |
| `make format` | 格式化代码（black） |
| `make check` | 运行所有代码质量检查 |

#### 日志相关

| 命令 | 说明 |
|------|------|
| `make logs` | 查看应用日志（实时） |
| `make logs-recent` | 查看最近50行日志 |
| `make logs-error` | 查看错误日志 |
| `make env` | 显示环境变量配置 |

#### 清理相关

| 命令 | 说明 |
|------|------|
| `make clean` | 清理临时文件和缓存 |
| `make clean-all` | 完全清理（包括虚拟环境） |
| `make reset` | 重置项目（清理+重新初始化） |

#### Docker 相关

| 命令 | 说明 |
|------|------|
| `make docker-build` | 构建 Docker 镜像 |
| `make docker-run` | 运行 Docker 容器 |
| `make docker-stop` | 停止 Docker 容器 |
| `make docker-clean` | 清理 Docker 资源 |

### 本地开发设置

#### 1. 创建开发环境

**推荐方式（使用 Makefile）**：

```bash
# 快速开始
make quickstart

# 启动开发服务器
make dev
```

**传统方式**：

```bash
# 克隆项目
git clone https://github.com/your-org/ai-dev-scheduler.git
cd ai-dev-scheduler

# 运行初始化脚本
./scripts/setup.sh

# 激活虚拟环境
source venv/bin/activate
```

#### 2. 配置开发环境变量

复制 `.env.example` 并修改：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入开发环境配置。

#### 3. 启动开发服务器

**使用 Makefile**：

```bash
make dev
```

**或直接使用脚本**：

```bash
# 方式 1: 使用开发脚本
./scripts/dev.sh

# 方式 2: 直接使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 方式 3: 运行主模块
python -m app.main
```

### 本地 Webhook 测试

在生产环境中，GitHub Webhook 需要一个公网 URL。本地开发时，我们使用 **ngrok** 创建一个安全的隧道。

#### 什么是 ngrok？

ngrok 是一个反向代理，可以将本地端口暴露到公网，无需配置路由器或防火墙。

#### 安装 ngrok

```bash
# macOS
brew install ngrok

# Linux
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# 或访问 https://ngrok.com/download 下载
```

#### 配置 ngrok（首次使用）

```bash
# 1. 注册 ngrok 账户
# 访问 https://ngrok.com/signup

# 2. 获取 authtoken
# 访问 https://dashboard.ngrok.com/get-started/your-authtoken

# 3. 配置 authtoken
ngrok config add-authtoken YOUR_NGROK_AUTH_TOKEN
```

#### 本地测试流程

**步骤 1: 启动 FastAPI 服务**

```bash
# 终端 1: 启动开发服务器
./scripts/dev.sh

# 或使用 Makefile
make dev

# 输出示例：
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**步骤 2: 启动 ngrok 隧道**

```bash
# 终端 2: 启动 ngrok
ngrok http 8000

# 输出示例：
# ngrok by @inconshreveable
# Session Status                online
# Forwarding    https://abc123.ngrok-free.app -> http://localhost:8000
#               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#               记住这个 URL！
# Web Interface                 http://127.0.0.1:4040
```

**步骤 3: 配置 GitHub Webhook**

1. 访问你的 GitHub 仓库设置页面
   ```
   https://github.com/your-username/your-repo/settings/hooks
   ```

2. 点击 "Add webhook"

3. 填写配置：
   ```
   Payload URL: https://abc123.ngrok-free.app/webhook/github
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
               替换为你的 ngrok URL

   Content type: application/json

   Secret: (你生成的 GITHUB_WEBHOOK_SECRET)

   Which events would you like to trigger this webhook?
   ✅ Let me select individual events
   ✅ Issues
   ✅ Issue comments
   ```

4. 点击 "Add webhook"

**步骤 4: 测试 Webhook**

```bash
# 在 GitHub Issue 中添加 "ai-dev" 标签
# 或在 Issue 中评论 "/ai develop"

# 查看终端 1 的日志输出
# 应该看到类似：
# INFO:     10.0.0.1:54321 - "POST /webhook/github HTTP/1.1" 202 Accepted
# INFO:     app.services.webhook_handler - 收到 GitHub event: issues
# INFO:     app.services.webhook_handler - 触发条件满足，开始 AI 开发
```

**步骤 5: 查看 ngrok 请求详情**

```bash
# 访问 ngrok Web 界面
open http://127.0.0.1:4040

# 你可以看到：
# - 所有传入请求
# - 请求头、请求体
# - 响应状态
# - 响应时间
```

#### 一键启动脚本

创建 `scripts/test-webhook.sh` 用于快速启动：

```bash
#!/bin/bash

echo "🚀 启动本地 Webhook 测试环境..."

# 检查 ngrok
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok 未安装"
    echo "   macOS: brew install ngrok"
    echo "   Linux: 访问 https://ngrok.com/download"
    exit 1
fi

# 检查 .env
if [ ! -f .env ]; then
    echo "❌ .env 文件不存在"
    echo "   请先运行: cp .env.example .env"
    exit 1
fi

# 启动服务
echo "📡 启动 FastAPI 服务..."
./scripts/dev.sh &
SERVER_PID=$!
sleep 3

# 启动 ngrok
echo "🌐 启动 ngrok 隧道..."
ngrok http 8000 &
NGROK_PID=$!

echo ""
echo "✅ 服务已启动！"
echo ""
echo "📝 下一步："
echo "   1. 复制上面的 ngrok URL"
echo "   2. 在 GitHub Webhook 设置中添加: https://xxx.ngrok-free.app/webhook/github"
echo "   3. 访问 ngrok Web 界面: http://127.0.0.1:4040"
echo ""
echo "⚠️  按 Ctrl+C 停止所有服务"

trap "kill $SERVER_PID $NGROK_PID 2>/dev/null; echo ''; echo '🛑 服务已停止'; exit 0" INT

wait
```

使用方法：

```bash
chmod +x scripts/test-webhook.sh
./scripts/test-webhook.sh
```

#### 调试技巧

**查看 Webhook 签名验证**

```bash
# 查看最近的 Webhook 交付
# 在 GitHub Webhook 页面点击 "Recent Deliveries"

# 点击具体的交付查看详情：
# - Request headers
# - Request payload
# - Response status
# - Response body
```

**重新发送 Webhook**

```bash
# 在 GitHub Webhook 页面
# 1. 找到最近的交付
# 2. 点击 "Redeliver" 按钮
# 3. 确认重新发送
```

**手动测试 Webhook**

```bash
# 使用 curl 发送测试请求
WEBHOOK_SECRET="your-secret"
PAYLOAD='{"action":"labeled","issue":{"number":1,"title":"Test"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')

curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -H "X-GitHub-Event: issues" \
  -d "$PAYLOAD"
```

#### 常见问题

**问题 1: ngrok URL 每次启动都变化**

```
原因: ngrok 免费版使用随机 URL

解决方案:
- 使用付费版 ngrok（固定子域名）
- 或每次测试后更新 GitHub Webhook URL
```

**问题 2: Webhook 验证失败**

```bash
# 检查 .env 中的 GITHUB_WEBHOOK_SECRET
grep GITHUB_WEBHOOK_SECRET .env

# 确保 GitHub Webhook 配置中的 Secret 与之一致
```

**问题 3: ngrok 连接超时**

```bash
# 检查本地服务是否正常运行
curl http://localhost:8000/health

# 检查 ngrok 是否正常
curl https://abc123.ngrok-free.app/health
```

#### 其他测试方案

除了 ngrok，还有其他选择：

**方案 A: localtunnel**

```bash
npm install -g localtunnel
lt --port 8000 --subdomain your-name

# Payload URL: https://your-name.loca.lt/webhook/github
```

**方案 B: Smee.io（GitHub 官方推荐）**

```bash
npm install -g smee-client
smee_client https://smee.io/abc123 http://localhost:8000/webhook/github

# Payload URL: https://smee.io/abc123
```

**方案 C: GitHub CLI（无需公网 URL）**

```bash
# 安装 GitHub CLI
brew install gh  # macOS

# 登录
gh auth login

# 模拟 webhook 事件
gh webhook testing --repo owner/repo --issues --payload @test-payload.json
```

推荐使用 **ngrok**，它是最稳定和最常用的解决方案。

### 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html

# 运行特定测试文件
pytest tests/test_webhook_handler.py

# 运行特定测试函数
pytest tests/test_webhook_handler.py::test_handle_labeled_event

# 查看详细输出
pytest -v

# 仅运行失败的测试
pytest --lf
```

### 代码质量工具

#### 格式化代码 (Black)

```bash
# 格式化所有代码
black .

# 检查格式（不修改）
black --check .
```

#### 代码检查 (Flake8)

```bash
# 运行 flake8
flake8 app/

# 仅显示错误
flake8 app/ --select=E
```

#### 类型检查 (MyPy)

```bash
# 运行类型检查
mypy app/

# 严格模式
mypy app/ --strict
```

#### Pre-commit 钩子

```bash
# 安装 pre-commit 钩子
pre-commit install

# 手动运行所有钩子
pre-commit run --all-files
```

### 代码结构说明

#### 模块职责

| 模块 | 职责 |
|------|------|
| `app/main.py` | FastAPI 应用入口，路由注册，中间件配置 |
| `app/config.py` | 配置加载和管理，使用 Pydantic Settings |
| `app/models/` | Pydantic 数据模型定义 |
| `app/services/` | 核心业务逻辑实现 |
| `app/api/` | API 路由和端点定义 |
| `app/utils/` | 工具函数和辅助类 |

#### 服务层设计

```python
# 服务基类
class BaseService(LoggerMixin):
    """所有服务的基类，提供日志功能"""
    pass

# 示例：创建新服务
class MyService(BaseService):
    def __init__(self):
        self.logger.info("服务初始化")

    def do_something(self) -> Result:
        # 业务逻辑
        pass
```

#### 异步编程模式

```python
# 异步服务方法
async def handle_webhook(request: Request) -> Response:
    # 异步处理
    payload = await request.json()
    result = await process_async(payload)
    return result

# 后台任务
async def background_task():
    # 长时间运行的任务
    await asyncio.create_task(long_running_operation())
```

### 开发最佳实践

1. **使用类型提示**
   ```python
   def process_issue(issue: Issue) -> TaskResult:
       pass
   ```

2. **编写文档字符串**
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

3. **使用结构化日志**
   ```python
   self.logger.info("处理 Issue", extra={
       "issue_number": issue.number,
       "title": issue.title,
       "labels": [label.name for label in issue.labels]
   })
   ```

4. **异常处理**
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

## API 文档

### 端点列表

| 方法 | 端点 | 描述 | 认证 |
|------|------|------|------|
| GET | `/` | 根端点，返回服务信息 | 无 |
| GET | `/health` | 健康检查 | 无 |
| POST | `/webhook/github` | GitHub Webhook 接收 | Webhook 签名 |
| GET | `/docs` | Swagger UI 文档 | 无 |
| GET | `/redoc` | ReDoc 文档 | 无 |
| GET | `/openapi.json` | OpenAPI 规范 | 无 |

### 根端点

**请求**
```http
GET /
```

**响应**
```json
{
  "service": "AI 开发调度服务",
  "version": "0.1.0",
  "status": "running",
  "docs": "/docs",
  "health": "/health"
}
```

### 健康检查

**请求**
```http
GET /health
```

**响应**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-08T10:30:45Z",
  "version": "0.1.0",
  "dependencies": {
    "github_api": "ok",
    "git_repository": "ok",
    "claude_cli": "ok"
  }
}
```

### GitHub Webhook

**请求**
```http
POST /webhook/github
Content-Type: application/json
X-Hub-Signature-256: sha256=<signature>
X-GitHub-Event: issues
X-GitHub-Delivery: <delivery-id>

{
  "action": "labeled",
  "issue": {
    "id": 123456789,
    "number": 123,
    "title": "修复登录 Bug",
    "body": "用户无法登录..."
  },
  "label": {
    "name": "ai-dev"
  }
}
```

**响应**
```json
{
  "status": "accepted",
  "message": "Webhook 已接收，正在后台处理",
  "delivery_id": "123456-7890-1234-5678",
  "event_type": "labeled"
}
```

### 访问 Swagger UI

启动服务后，访问以下地址查看交互式 API 文档：

```
http://localhost:8000/docs
```

功能：
- 查看所有 API 端点
- 查看请求/响应模式
- 在线测试 API
- 下载 OpenAPI 规范

---

## 部署指南

### Docker 部署

#### 1. 创建 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# 安装 Claude Code CLI
RUN npm install -g @anthropic/claude-code

# 复制项目文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 创建日志目录
RUN mkdir -p logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  ai-scheduler:
    build: .
    container_name: ai-dev-scheduler
    ports:
      - "8000:8000"
    environment:
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
      - GITHUB_REPO_OWNER=${GITHUB_REPO_OWNER}
      - GITHUB_REPO_NAME=${GITHUB_REPO_NAME}
      - REPO_PATH=/app/repo
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./repo:/app/repo
    restart: unless-stopped
```

#### 3. 构建和运行

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 生产环境配置

#### 1. 使用进程管理器（Supervisor）

创建 `/etc/supervisor/conf.d/ai-scheduler.conf`：

```ini
[program:ai-scheduler]
command=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
directory=/path/to/ai-dev-scheduler
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/ai-scheduler.log
```

启动服务：

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start ai-scheduler
```

#### 2. 使用 Systemd

创建 `/etc/systemd/system/ai-scheduler.service`：

```ini
[Unit]
Description=AI Dev Scheduler Service
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/ai-dev-scheduler
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-scheduler
sudo systemctl start ai-scheduler
sudo systemctl status ai-scheduler
```

#### 3. 配置 Nginx 反向代理

创建 `/etc/nginx/sites-available/ai-scheduler`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /webhook/github {
        proxy_pass http://127.0.0.1:8000/webhook/github;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/ai-scheduler /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 性能优化建议

1. **使用 Gunicorn + Uvicorn Workers**

```bash
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

2. **启用缓存**

在 `config.yaml` 中：

```yaml
performance:
  enable_cache: true
  cache_ttl: 3600
```

3. **调整日志级别**

生产环境使用 `INFO` 或 `WARNING`：

```yaml
logging:
  level: "INFO"
```

4. **配置 CORS 限制**

仅允许特定域名：

```yaml
security:
  cors_origins:
    - "https://your-domain.com"
```

---

## 故障排查

### 常见问题

#### 1. Webhook 签名验证失败

**症状**: 日志显示 "Webhook 签名验证失败"

**解决方案**:
```bash
# 检查 .env 中的 WEBHOOK_SECRET 是否与 GitHub 配置一致
grep GITHUB_WEBHOOK_SECRET .env

# 重新生成密钥
python -c "import secrets; print(secrets.token_hex(32))"

# 在 GitHub Webhook 设置中更新 Secret
```

#### 2. Claude Code CLI 未找到

**症状**: "claude-code: command not found"

**解决方案**:
```bash
# 检查 Claude Code 是否已安装
which claude-code

# 重新安装
npm install -g @anthropic/claude-code

# 验证安装
claude-code --version
```

#### 3. Git 操作失败

**症状**: "Git command failed"

**解决方案**:
```bash
# 检查仓库路径是否正确
ls -la $REPO_PATH

# 检查 Git 远程仓库
cd $REPO_PATH
git remote -v

# 确保 GitHub Token 有权限
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/user/repos
```

#### 4. 端口已被占用

**症状**: "Address already in use"

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 终止进程
kill -9 <PID>

# 或使用其他端口
uvicorn app.main:app --port 8001
```

#### 5. 依赖安装失败

**症状**: "Could not find a version that satisfies the requirement"

**解决方案**:
```bash
# 升级 pip
pip install --upgrade pip

# 清理缓存
pip cache purge

# 重新安装依赖
pip install -r requirements.txt
```

### 日志位置

| 日志类型 | 位置 | 说明 |
|---------|------|------|
| 应用日志 | `logs/ai-scheduler.log` | 主要应用日志 |
| 错误日志 | `logs/ai-scheduler.log` | 错误和异常信息 |
| Git 日志 | `logs/git.log` | Git 操作日志 |
| Claude 日志 | `logs/claude.log` | Claude CLI 调用日志 |

### 调试技巧

#### 1. 启用调试模式

在 `config.yaml` 中设置：

```yaml
logging:
  level: "DEBUG"
```

#### 2. 查看详细请求日志

```bash
# 使用 curl 测试 Webhook
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: labeled" \
  -d '{"action":"labeled","issue":{"number":123}}'
```

#### 3. 使用 Python 调试器

```python
import pdb; pdb.set_trace()  # 设置断点
```

或使用 `ipdb`：

```bash
pip install ipdb
```

```python
import ipdb; ipdb.set_trace()
```

#### 4. 检查环境变量

```bash
# 查看所有环境变量
env | grep GITHUB

# 或在 Python 中
import os
print(os.environ.get('GITHUB_TOKEN'))
```

---

## 安全建议

### Webhook 安全

1. **始终验证签名**
   - 使用 HMAC-SHA256 验证所有 Webhook 请求
   - 不要禁用签名验证（仅限开发环境）

2. **使用强密钥**
   ```bash
   # 生成 64 字符的随机密钥
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

3. **限制 IP 白名单**（可选）
   ```yaml
   security:
     ip_whitelist:
       - "192.168.1.0/24"
       - "10.0.0.0/8"
   ```

### API 安全

1. **使用最小权限原则**
   - GitHub Token 仅授予必要的权限
   - 使用专用服务账号

2. **启用基本认证**（可选）
   ```yaml
   security:
     enable_basic_auth: true
     basic_auth_username: "${BASIC_AUTH_USERNAME}"
     basic_auth_password: "${BASIC_AUTH_PASSWORD}"
   ```

3. **限制 CORS 来源**
   ```yaml
   security:
     cors_origins:
       - "https://your-domain.com"
   ```

### 数据安全

1. **保护敏感信息**
   - 使用环境变量存储密钥
   - 不要将 `.env` 文件提交到版本控制
   - 使用 `.gitignore` 排除敏感文件

2. **定期轮换密钥**
   - 每 90 天轮换 GitHub Token
   - 每 90 天轮换 Webhook Secret
   - 每 180 天轮换 API 密钥

3. **加密日志**（可选）
   ```yaml
   logging:
     format: "%(asctime)s - %(name)s - %(levelname)s - [ENCRYPTED]"
   ```

### 网络安全

1. **使用 HTTPS**
   - 在生产环境中使用 SSL/TLS 证书
   - 使用 Let's Encrypt 获取免费证书

2. **配置防火墙**
   ```bash
   # 仅允许特定端口
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

3. **使用 VPN**（可选）
   - 限制管理后台仅能通过 VPN 访问

---

## 贡献指南

### 如何贡献

我们欢迎各种形式的贡献！

#### 报告 Bug

1. 在 Issues 中搜索现有问题
2. 创建新的 Issue，包含：
   - 清晰的标题和描述
   - 复现步骤
   - 预期行为和实际行为
   - 环境信息（Python 版本、操作系统等）

#### 提交代码

1. **Fork 项目**
   ```bash
   # Fork 并克隆你的 fork
   git clone https://github.com/your-username/ai-dev-scheduler.git
   cd ai-dev-scheduler
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **编写代码**
   - 遵循现有代码风格
   - 添加类型提示
   - 编写文档字符串
   - 添加测试

4. **运行测试**
   ```bash
   pytest
   black --check .
   flake8 app/
   mypy app/
   ```

5. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"
   ```

6. **推送到 Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **创建 Pull Request**
   - 填写 PR 模板
   - 关联相关 Issue
   - 等待代码审查

#### 代码审查准则

- 代码通过所有测试
- 代码覆盖率不降低
- 遵循代码风格指南
- 文档完整且准确
- 无安全漏洞

### 开发规范

#### Git 提交信息格式

使用 Conventional Commits 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

类型（type）：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 代码重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建/工具链相关

示例：

```bash
feat(webhook): 支持 Pull Request 事件

添加对 PR 打开和更新事件的处理

- 添加 PR 事件模型
- 实现 PR 处理器
- 添加单元测试

Closes #123
```

#### 代码风格

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

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

```
MIT License

Copyright (c) 2024 AI Development Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Web 框架
- [Claude Code](https://claude.ai/code) - AI 开发工具
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API 库
- [GitPython](https://github.com/gitpython-developers/GitPython) - Git 操作库

---

## 联系方式

- **项目主页**: https://github.com/your-org/ai-dev-scheduler
- **问题反馈**: https://github.com/your-org/ai-dev-scheduler/issues
- **文档**: https://github.com/your-org/ai-dev-scheduler/wiki
- **邮箱**: your-email@example.com

---

## 更新日志

### v0.2.0 (2026-01-09)

测试和代码质量提升

- ✅ 补充 300+ 新测试用例
- ✅ 代码测试覆盖率达到 89%（目标 85%）
- ✅ 修复 P0/P1 优先级问题
- ✅ 改进异常处理和日志记录
- ✅ 统一类型提示
- ✅ 增强签名验证日志

### v0.1.0 (2024-01-08)

初始版本发布

- ✅ GitHub Webhook 接收和验证
- ✅ 标签和评论触发支持
- ✅ Claude Code CLI 集成
- ✅ 自动化 Git 操作
- ✅ Pull Request 自动创建
- ✅ 完整的日志系统
- ✅ 配置管理
- ✅ API 文档（Swagger UI）

---

**⭐ 如果这个项目对您有帮助，请给我们一个 Star！**

**Made with ❤️ by AI Development Team**
