# AI 开发调度服务 - 完整实施计划

## 项目概述

开发一个基于 Python 的本地服务，用于：
1. 接收 GitHub Webhook 事件（Issue 标签/评论触发）
2. 调用本地 Claude Code CLI 进行 AI 开发
3. 自动化测试、提交、创建 PR

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      系统架构图                              │
└─────────────────────────────────────────────────────────────┘

GitHub Issue (添加标签 'ai-dev' 或评论 '/ai develop')
    ↓
GitHub Webhook (HTTP POST)
    ↓
┌────────────────────────────────────────┐
│     AI 开发调度服务 (本地运行)           │
│  ┌──────────────────────────────────┐  │
│  │  1. FastAPI Webhook Server      │  │
│  │  2. 事件解析器                   │  │
│  │  3. Claude Code CLI 调用器       │  │
│  │  4. Git 操作管理器               │  │
│  │  5. GitHub API 客户端            │  │
│  │  6. 任务状态追踪器               │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
    ↓
Claude Code CLI (本地代码库)
    ↓
AI 生成代码 + 测试 + Git 提交
    ↓
创建 PR + 通知
```

---

## 项目结构

```
ai-dev-scheduler/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置管理
│   ├── models/
│   │   ├── __init__.py
│   │   └── github_events.py    # GitHub 事件数据模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── webhook_handler.py  # Webhook 处理
│   │   ├── claude_service.py   # Claude Code CLI 调用
│   │   ├── git_service.py      # Git 操作
│   │   └── github_service.py   # GitHub API 操作
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py           # 日志工具
│   │   └── validators.py       # Webhook 签名验证
│   └── api/
│       ├── __init__.py
│       └── health.py           # 健康检查端点
├── logs/                        # 日志目录
├── config/
│   └── config.yaml             # 配置文件
├── scripts/
│   ├── setup.sh                # 初始化脚本
│   └── dev.sh                  # 开发启动脚本
├── tests/
│   ├── test_webhook_handler.py
│   ├── test_claude_service.py
│   └── test_git_service.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 核心模块详细设计

### 1. FastAPI Webhook Server (`app/main.py`)

**功能：**
- 接收 GitHub Webhook POST 请求
- 验证 webhook 签名（HMAC-SHA256）
- 路由事件到对应的处理器
- 返回异步处理状态

**关键代码结构：**
```python
from fastapi import FastAPI, Header, Request, HTTPException
from app.services.webhook_handler import WebhookHandler
from app.utils.validators import verify_webhook_signature

app = FastAPI()
handler = WebhookHandler()

@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None)
):
    # 验证签名
    payload = await request.body()
    if not verify_webhook_signature(payload, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # 解析事件
    event_data = await request.json()
    result = await handler.handle_event(x_github_event, event_data)

    return {"status": "processed", "task_id": result.task_id}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

### 2. 事件解析器 (`app/services/webhook_handler.py`)

**功能：**
- 解析 Issue 事件（labeled, issue_comment）
- 检查触发条件（标签 'ai-dev' 或评论 '/ai develop'）
- 提取 Issue 信息和需求描述
- 协调调用其他服务完成开发任务

**关键逻辑：**
```python
class WebhookHandler:
    def __init__(self):
        self.claude_service = ClaudeService()
        self.git_service = GitService()
        self.github_service = GitHubService()

    async def handle_event(self, event_type: str, data: dict):
        if event_type == "issues":
            return await self._handle_issue_event(data)
        elif event_type == "issue_comment":
            return await self._handle_comment_event(data)

    async def _handle_issue_event(self, data: dict):
        # 检查是否添加了 'ai-dev' 标签
        labels = [l['name'] for l in data['issue']['labels']]
        if 'ai-dev' not in labels and 'ai-dev' != data.get('label', {}).get('name'):
            return None

        # 触发 AI 开发
        return await self._trigger_ai_development(data['issue'])

    async def _handle_comment_event(self, data: dict):
        comment_body = data['comment']['body']
        if '/ai develop' not in comment_body.lower():
            return None

        return await self._trigger_ai_development(data['issue'])

    async def _trigger_ai_development(self, issue: dict) -> dict:
        issue_number = issue['number']
        issue_url = issue['html_url']
        issue_title = issue['title']
        issue_body = issue.get('body', '')

        # 1. 创建特性分支
        branch_name = await self.git_service.create_feature_branch(issue_number)

        # 2. 调用 Claude Code 进行开发
        result = await self.claude_service.develop_feature(
            issue_url, issue_body
        )

        if not result['success']:
            raise Exception(f"Claude development failed: {result['errors']}")

        # 3. 提交变更
        await self.git_service.commit_changes(f"AI: {issue_title}")

        # 4. 推送到远程
        await self.git_service.push_to_remote(branch_name)

        # 5. 创建 PR
        pr_info = await self.github_service.create_pull_request(
            repo_name="owner/repo",
            branch_name=branch_name,
            issue_number=issue_number,
            issue_title=issue_title
        )

        return {
            'task_id': f"task-{issue_number}",
            'branch': branch_name,
            'pr_url': pr_info['url']
        }
```

---

### 3. Claude Code CLI 调用器 (`app/services/claude_service.py`)

**功能：**
- 使用 subprocess 调用 `claude-code` 命令
- 传递 Issue 内容作为 prompt
- 捕获 AI 的输出和代码变更
- 超时控制和错误处理

**实现方案：**
```python
import subprocess
import asyncio
from pathlib import Path
import time

class ClaudeService:
    def __init__(self, repo_path: str = None):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

    async def develop_feature(self, issue_url: str, issue_body: str) -> dict:
        """
        调用 Claude Code CLI 进行开发
        """
        # 构建提示词
        prompt = self._build_prompt(issue_url, issue_body)

        # 调用 claude-code CLI
        cmd = [
            'claude-code',
            '--cwd', str(self.repo_path),
            prompt  # 直接传递 prompt 作为参数
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.repo_path)
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=1800  # 30分钟超时
            )

            return {
                'success': process.returncode == 0,
                'output': stdout.decode(),
                'errors': stderr.decode()
            }

        except asyncio.TimeoutError:
            process.kill()
            raise Exception("Claude Code execution timeout")

    def _build_prompt(self, issue_url: str, issue_body: str) -> str:
        return f"""
请分析以下 GitHub Issue 并完成开发任务：

Issue URL: {issue_url}
Issue 内容:
{issue_body}

任务要求：
1. 分析需求，理解代码库结构
2. 生成或修改代码
3. 运行测试确保功能正常
4. 提交代码（commit message 格式："AI: <Issue标题>"）

请按照以下步骤执行：
- 步骤1: 理解需求
- 步骤2: 探索代码库
- 步骤3: 实现功能
- 步骤4: 运行测试
- 步骤5: 提交变更
"""
```

---

### 4. Git 操作管理器 (`app/services/git_service.py`)

**功能：**
- 创建特性分支（`ai/feature-{issue_number}-{timestamp}`）
- 应用 AI 生成的变更
- 提交代码
- Push 到远程
- 处理冲突

**实现：**
```python
import git
from pathlib import Path
import time

class GitService:
    def __init__(self, repo_path: str = None):
        path = repo_path or Path.cwd()
        self.repo = git.Repo(path)
        self.repo_path = Path(path)

    async def create_feature_branch(self, issue_number: int) -> str:
        """创建特性分支"""
        # 确保在主分支
        self.repo.heads.main.checkout()

        # 拉取最新代码
        origin = self.repo.remotes.origin
        origin.pull()

        # 创建并切换到新分支
        branch_name = f"ai/feature-{issue_number}-{int(time.time())}"
        self.repo.create_head(branch_name)
        self.repo.heads[branch_name].checkout()

        return branch_name

    async def commit_changes(self, message: str):
        """提交变更"""
        self.repo.index.add('*')

        if self.repo.is_dirty():
            self.repo.index.commit(message)
            return True
        return False

    async def push_to_remote(self, branch_name: str):
        """推送到远程"""
        origin = self.repo.remotes.origin
        origin.push(branch_name)

    def has_changes(self) -> bool:
        """检查是否有变更"""
        return self.repo.is_dirty()

    def get_current_branch(self) -> str:
        """获取当前分支名"""
        return self.repo.active_branch.name
```

---

### 5. GitHub API 客户端 (`app/services/github_service.py`)

**功能：**
- 创建 Pull Request
- 在 Issue/PR 中添加评论
- 更新任务状态

**实现：**
```python
from github import Github
from github.GithubException import GithubException

class GitHubService:
    def __init__(self, token: str = None):
        if token is None:
            import os
            token = os.getenv('GITHUB_TOKEN')
        self.github = Github(token)

    async def create_pull_request(
        self,
        repo_name: str,
        branch_name: str,
        issue_number: int,
        issue_title: str
    ) -> dict:
        """创建 PR"""
        repo = self.github.get_repo(repo_name)

        pr = repo.create_pull(
            title=f"🤖 AI: {issue_title}",
            body=self._build_pr_body(issue_number),
            head=branch_name,
            base='main'
        )

        return {'pr_number': pr.number, 'url': pr.html_url}

    def _build_pr_body(self, issue_number: int) -> str:
        return f"""
## 🤖 AI 自动生成的 Pull Request

**关联 Issue**: #{issue_number}

### 变更说明
本 PR 由 AI 自动分析和生成，已完成以下工作：
- ✅ 需求分析
- ✅ 代码实现
- ✅ 测试验证
- ✅ 代码提交

### 审核要点
请人工审核以下内容：
- 代码质量和安全性
- 功能完整性
- 测试覆盖率
- 是否符合项目规范

@author 请 review 后合并
"""
```

---

### 6. 配置管理 (`config/config.yaml`)

```yaml
# 服务配置
server:
  host: "0.0.0.0"
  port: 8000
  reload: false

# GitHub 配置
github:
  webhook_secret: "${GITHUB_WEBHOOK_SECRET}"  # 从环境变量读取
  token: "${GITHUB_TOKEN}"
  trigger_label: "ai-dev"
  trigger_command: "/ai develop"

# 代码仓库配置
repository:
  path: "/path/to/your/local/repo"  # 固定目录
  default_branch: "main"
  remote_name: "origin"

# Claude Code 配置
claude:
  timeout: 1800  # 30分钟
  max_retries: 2
  auto_test: true

# 日志配置
logging:
  level: "INFO"
  file: "logs/ai-scheduler.log"
  rotation: "10 MB"
```

---

## 部署和配置指南

### Phase 1: 项目初始化

**步骤：**
1. 创建项目目录结构
2. 初始化 Python 虚拟环境
3. 安装依赖
4. 配置环境变量

**依赖文件 (`requirements.txt`)：**
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pygithub==2.1.1
gitpython==3.1.40
pyyaml==6.0.1
python-dotenv==1.0.0
cryptography==41.0.7
pydantic==2.5.0
```

**初始化脚本 (`scripts/setup.sh`)：**
```bash
#!/bin/bash
set -e

echo "🚀 初始化 AI 开发调度服务..."

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "📦 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 创建必要的目录
mkdir -p logs
mkdir -p config

# 生成 .env 文件模板
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# GitHub 配置
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here
GITHUB_TOKEN=ghp_your-token-here
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=your-repo

# 代码仓库路径
REPO_PATH=/path/to/your/local/repo

# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-your-key-here
EOF
    echo "✅ 已创建 .env 文件，请填写配置信息"
fi

echo "✅ 初始化完成！"
echo ""
echo "📝 下一步："
echo "1. 编辑 .env 文件，填写必要的配置"
echo "2. 运行: source venv/bin/activate"
echo "3. 启动服务: ./scripts/dev.sh"
```

**开发启动脚本 (`scripts/dev.sh`)：**
```bash
#!/bin/bash
set -e

# 加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 启动服务
echo "🚀 启动 AI 开发调度服务..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### Phase 2: GitHub 配置

#### 2.1 创建 GitHub Personal Access Token

1. 访问：https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 设置权限：
   - ✅ `repo` (full control of private repositories)
   - ✅ `issues` (read/write)
4. 复制生成的 token，保存到 `.env` 文件

#### 2.2 配置 Webhook

1. 进入目标仓库的 Settings → Webhooks → Add webhook
2. 配置如下：
   - **Payload URL**: `https://your-domain.com/webhook/github`
     - 开发时使用 ngrok: `https://abc123.ngrok.io/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: 设置一个强密码（保存到 `.env` 的 `GITHUB_WEBHOOK_SECRET`）
   - **Events**: 选择以下事件
     - ✅ Issues
     - ✅ Issue comments
3. 点击 "Add webhook"

#### 2.3 设置环境变量

创建 `.env` 文件：
```bash
# GitHub 配置
GITHUB_WEBHOOK_SECRET=your-webhook-secret
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=your-repo-name

# 代码仓库路径（本地克隆的目录）
REPO_PATH=/Users/yourname/projects/your-repo

# Anthropic API Key（Claude Code 需要）
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
```

---

### Phase 3: 本地开发与测试

#### 3.1 启动服务

```bash
# 激活虚拟环境
source venv/bin/activate

# 开发模式（自动重载）
./scripts/dev.sh

# 或直接使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3.2 使用 ngrok 暴露本地服务（开发测试）

```bash
# 安装 ngrok（如果还没安装）
# macOS: brew install ngrok

# 启动 ngrok 隧道
ngrok http 8000

# 输出示例：
# Forwarding  https://abc123.ngrok.io -> http://localhost:8000

# 将 https://abc123.ngrok.io/webhook/github 配置到 GitHub Webhook
```

#### 3.3 健康检查

```bash
# 测试服务是否正常运行
curl http://localhost:8000/health

# 预期响应：
# {"status":"healthy"}
```

---

### Phase 4: 完整工作流测试

#### 测试场景 1: 标签触发

1. 在 GitHub 仓库创建新 Issue
2. 添加标签 `ai-dev`
3. 观察本地服务日志
4. 检查是否创建了新的分支和 PR

**观察日志：**
```bash
# 服务应该输出类似日志：
INFO: Received 'issues' event
INFO: Trigger label 'ai-dev' detected
INFO: Creating feature branch: ai/feature-123-1234567890
INFO: Calling Claude Code CLI...
INFO: Development completed successfully
INFO: Created PR: https://github.com/owner/repo/pull/456
```

#### 测试场景 2: 评论触发

1. 在任意 Issue 中评论：`/ai develop`
2. 观察服务日志
3. 验证 AI 生成的代码和 PR

---

## 运行时工作流详解

```
┌─────────────────────────────────────────────────────────────┐
│                    完整工作流程                               │
└─────────────────────────────────────────────────────────────┘

1. 用户触发
   ├─ 在 Issue 添加 'ai-dev' 标签
   └─ 或在 Issue 评论 '/ai develop'

2. GitHub Webhook
   ├─ 发送 POST 请求到本地服务
   └─ 携带事件数据和签名

3. 服务处理（app/main.py）
   ├─ 验证 webhook 签名
   ├─ 解析事件类型和数据
   └─ 调用 WebhookHandler

4. WebhookHandler 处理（app/services/webhook_handler.py）
   ├─ 检查触发条件
   ├─ 提取 Issue 信息
   └─ 启动 AI 开发流程

5. Git 操作（app/services/git_service.py）
   ├─ 切换到 main 分支
   ├─ 拉取最新代码
   └─ 创建特性分支 ai/feature-{issue_number}-{timestamp}

6. Claude Code 开发（app/services/claude_service.py）
   ├─ 构建提示词
   ├─ 调用 claude-code CLI
   ├─ AI 分析需求
   ├─ AI 探索代码库
   ├─ AI 生成/修改代码
   ├─ AI 运行测试
   └─ AI 提交变更

7. Git 提交和推送
   ├─ 提交代码变更
   └─ 推送到远程分支

8. 创建 PR（app/services/github_service.py）
   ├─ 调用 GitHub API
   ├─ 创建 Pull Request
   └─ 添加 PR 描述

9. 通知用户
   └─ PR 创建成功，通知相关人员

10. 人工审核
    ├─ 开发人员 review PR
    ├─ 检查代码质量
    └─ 测试功能

11. 合并部署
    ├─ 合并 PR 到 main
    ├─ 触发 CI/CD
    └─ 自动部署到生产环境
```

---

## 核心文件清单

### Python 源代码文件

1. **`app/main.py`** - FastAPI 应用入口
   - Webhook 端点
   - 健康检查端点
   - 中间件配置

2. **`app/config.py`** - 配置加载器
   - YAML 配置解析
   - 环境变量注入
   - 配置验证

3. **`app/services/webhook_handler.py`** - Webhook 处理核心
   - 事件路由
   - 触发条件检查
   - AI 开发流程编排

4. **`app/services/claude_service.py`** - Claude CLI 调用
   - CLI 命令构建
   - 异步进程管理
   - 超时控制

5. **`app/services/git_service.py`** - Git 操作
   - 分支管理
   - 提交推送
   - 变更检测

6. **`app/services/github_service.py`** - GitHub API
   - PR 创建
   - 评论管理
   - Issue 关联

7. **`app/utils/validators.py`** - Webhook 签名验证
   - HMAC-SHA256 验证
   - 安全检查

8. **`app/utils/logger.py`** - 日志工具
   - 日志配置
   - 文件轮转
   - 结构化输出

### 配置文件

9. **`config/config.yaml`** - 服务配置
   - 服务端口
   - GitHub 配置
   - 仓库路径
   - 日志设置

10. **`requirements.txt`** - Python 依赖
    - FastAPI
    - PyGithub
    - GitPython
    - 其他依赖

11. **`.env`** - 环境变量（不提交到 Git）
    - GitHub Token
    - Webhook Secret
    - API Keys

### 脚本文件

12. **`scripts/setup.sh`** - 初始化脚本
    - 创建虚拟环境
    - 安装依赖
    - 生成配置模板

13. **`scripts/dev.sh`** - 开发启动脚本
    - 加载环境变量
    - 启动开发服务器

### 文档

14. **`README.md`** - 项目文档
    - 快速开始
    - 配置说明
    - 使用指南

---

## 测试方案

### 单元测试

**`tests/test_webhook_handler.py`**
```python
import pytest
from app.services.webhook_handler import WebhookHandler

@pytest.mark.asyncio
async def test_handle_issue_event_with_trigger_label():
    handler = WebhookHandler()
    data = {
        "action": "labeled",
        "label": {"name": "ai-dev"},
        "issue": {
            "number": 123,
            "title": "Test Issue",
            "body": "Test description",
            "html_url": "https://github.com/owner/repo/issues/123"
        }
    }

    result = await handler._handle_issue_event(data)
    assert result is not None
    assert "branch" in result
```

**`tests/test_git_service.py`**
```python
import pytest
from app.services.git_service import GitService

@pytest.mark.asyncio
async def test_create_feature_branch():
    git_service = GitService("/path/to/test/repo")
    branch_name = await git_service.create_feature_branch(123)

    assert branch_name.startswith("ai/feature-123-")
    assert git_service.get_current_branch() == branch_name
```

### 集成测试

```bash
# 1. 启动服务
./scripts/dev.sh

# 2. 模拟 GitHub Webhook 请求
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=计算出的签名" \
  -d '{
    "action": "labeled",
    "label": {"name": "ai-dev"},
    "issue": {
      "number": 1,
      "title": "Test Issue",
      "body": "请实现一个新功能",
      "html_url": "https://github.com/owner/repo/issues/1"
    }
  }'
```

### 端到端测试

1. **准备测试仓库**
   - 创建一个测试 GitHub 仓库
   - Clone 到本地
   - 配置到 `.env` 的 `REPO_PATH`

2. **配置 Webhook**
   - 使用 ngrok 暴露本地服务
   - 配置 GitHub Webhook

3. **执行测试**
   - 创建测试 Issue
   - 添加 `ai-dev` 标签
   - 观察服务日志
   - 验证生成的 PR
   - 检查代码质量

---

## 安全最佳实践

### 1. Webhook 签名验证

**必须验证所有请求的 HMAC 签名：**
```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    secret = os.getenv('GITHUB_WEBHOOK_SECRET').encode()
    expected_signature = 'sha256=' + hmac.new(
        secret,
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)
```

### 2. 敏感信息保护

- ✅ 使用环境变量存储 token
- ✅ 将 `.env` 添加到 `.gitignore`
- ✅ 不要在日志中记录敏感信息
- ✅ 定期轮换 API keys

### 3. 权限最小化

**GitHub Token 权限：**
- ✅ 只授予必要的 `repo` 和 `issues` 权限
- ❌ 不要授予 `admin`、`delete_repo` 等高权限

### 4. 访问控制

**如果暴露到公网，建议添加基本认证：**
```python
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

async def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.getenv("BASIC_AUTH_USERNAME")
    correct_password = os.getenv("BASIC_AUTH_PASSWORD")

    if credentials.username != correct_username or credentials.password != correct_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return credentials
```

---

## 故障排查指南

### 常见问题及解决方案

#### 1. Claude Code CLI 未找到

**错误信息：**
```
FileNotFoundError: [Errno 2] No such file or directory: 'claude-code'
```

**解决方案：**
```bash
# 检查 claude-code 是否安装
which claude-code

# 如果未安装，执行：
npm install -g @anthropic/claude-code

# 检查 PATH 环境变量
echo $PATH
```

#### 2. Git 操作失败

**错误信息：**
```
GitError: Can't find remote 'origin'
```

**解决方案：**
```bash
# 检查远程仓库配置
cd /path/to/your/repo
git remote -v

# 如果没有 origin，添加：
git remote add origin git@github.com:owner/repo.git
```

#### 3. Webhook 验证失败

**错误信息：**
```
HTTPException: Invalid signature
```

**解决方案：**
```bash
# 检查环境变量
echo $GITHUB_WEBHOOK_SECRET

# 确保与 GitHub Webhook 配置的 Secret 完全一致
# 大小写敏感！
```

#### 4. GitHub API 限流

**错误信息：**
```
GithubException: 403 {"message": "API rate limit exceeded"}
```

**解决方案：**
```python
# 在 github_service.py 中添加重试逻辑
from time import sleep

async def create_pull_request_with_retry(self, ...):
    max_retries = 3
    for i in range(max_retries):
        try:
            return await self.create_pull_request(...)
        except GithubException as e:
            if e.status == 403 and i < max_retries - 1:
                sleep(60)  # 等待 1 分钟后重试
            else:
                raise
```

#### 5. Claude API 超时

**解决方案：**
```yaml
# 在 config.yaml 中增加超时时间
claude:
  timeout: 3600  # 增加到 60 分钟
```

---

## 监控与日志

### 日志配置

**`app/utils/logger.py`**
```python
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(name: str = "ai-scheduler"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 文件处理器（带轮转）
    file_handler = RotatingFileHandler(
        'logs/ai-scheduler.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
```

### 关键监控指标

1. **Webhook 接收成功率**
   ```python
   webhook_received_total = Counter("webhook_received_total")
   webhook_success_total = Counter("webhook_success_total")
   ```

2. **Claude Code 执行成功率**
   ```python
   claude_execution_total = Counter("claude_execution_total", ["status"])
   ```

3. **PR 创建成功率**
   ```python
   pr_created_total = Counter("pr_created_total")
   pr_failed_total = Counter("pr_failed_total")
   ```

4. **平均执行时间**
   ```python
   development_duration = Histogram("development_duration_seconds")
   ```

### 日志分析

**使用 grep 分析关键事件：**
```bash
# 查看所有 webhook 请求
grep "Received.*event" logs/ai-scheduler.log

# 查看失败的 AI 开发
grep "Claude development failed" logs/ai-scheduler.log

# 查看 PR 创建记录
grep "Created PR:" logs/ai-scheduler.log

# 统计成功率
grep -c "Development completed successfully" logs/ai-scheduler.log
```

---

## 性能优化建议

### 1. 并发处理

**使用 asyncio 并发执行多个 Issue：**
```python
import asyncio

async def process_multiple_issues(issues: list):
    tasks = [process_issue(issue) for issue in issues]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### 2. 缓存优化

**缓存 GitHub API 调用：**
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_repo_info(repo_name: str):
    # 缓存仓库信息
    return github.get_repo(repo_name)
```

### 3. 队列系统（进阶）

**使用 Celery + Redis 处理长时间任务：**
```python
from celery import Celery

app = Celery('ai-scheduler', broker='redis://localhost:6379/0')

@app.task
def develop_feature_async(issue_data):
    # 异步执行 AI 开发
    ...
```

---

## 下一步优化方向

### 短期优化（1-2 周）
- [ ] 添加任务状态持久化（SQLite）
- [ ] 实现 Web UI 监控面板
- [ ] 添加 Slack/Telegram 通知
- [ ] 完善单元测试覆盖率

### 中期优化（1-2 个月）
- [ ] 集成 Celery 任务队列
- [ ] 支持多仓库配置
- [ ] 实现增量部署（只推送变更的文件）
- [ ] 添加性能监控面板

### 长期优化（3-6 个月）
- [ ] 支持自定义 AI 模型
- [ ] 实现 A/B 测试机制
- [ ] 添加代码审查 AI 辅助
- [ ] 构建完整的 DevOps 平台

---

## 快速参考

### 启动服务
```bash
# 开发模式
./scripts/dev.sh

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 查看日志
```bash
# 实时查看
tail -f logs/ai-scheduler.log

# 查看错误
grep ERROR logs/ai-scheduler.log
```

### 测试 Webhook
```bash
# 健康检查
curl http://localhost:8000/health

# 模拟 Webhook
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

### GitHub Webhook 配置
- URL: `https://your-domain.com/webhook/github`
- Content type: `application/json`
- Secret: `<your-webhook-secret>`
- Events: `Issues`, `Issue comments`

---

## 附录

### A. 环境变量清单

| 变量名 | 说明 | 必需 | 示例 |
|--------|------|------|------|
| `GITHUB_WEBHOOK_SECRET` | Webhook 签名密钥 | ✅ | `random-secret-string` |
| `GITHUB_TOKEN` | GitHub Personal Access Token | ✅ | `ghp_xxxxxxxxxxxx` |
| `GITHUB_REPO_OWNER` | 仓库所有者 | ✅ | `username` |
| `GITHUB_REPO_NAME` | 仓库名称 | ✅ | `repo-name` |
| `REPO_PATH` | 本地仓库路径 | ✅ | `/path/to/repo` |
| `ANTHROPIC_API_KEY` | Anthropic API Key | ✅ | `sk-ant-xxxxxx` |
| `BASIC_AUTH_USERNAME` | 基础认证用户名 | ❌ | `admin` |
| `BASIC_AUTH_PASSWORD` | 基础认证密码 | ❌ | `password` |

### B. 支持的 GitHub 事件

| 事件类型 | 触发条件 | 说明 |
|---------|---------|------|
| `issues` | 添加 `ai-dev` 标签 | Issue 被打上特定标签时触发 |
| `issue_comment` | 评论包含 `/ai develop` | Issue 收到特定评论时触发 |

### C. Claude Code CLI 参数参考

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--cwd` | 工作目录 | 当前目录 |
| `--prompt` | 提示词 | - |
| `--auto-commit` | 自动提交 | false |
| `--timeout` | 超时时间（秒） | 1800 |

---

## 总结

本文档提供了 AI 开发调度服务的完整实施指南，包括：

✅ 技术架构设计
✅ 项目结构规划
✅ 核心模块实现
✅ 部署配置流程
✅ 测试验证方案
✅ 安全最佳实践
✅ 故障排查指南
✅ 性能优化建议

按照本文档的步骤，你可以快速搭建一个从 GitHub Issue 到自动部署的完整 AI 开发流程。

**预计开发时间：** 1-2 周
**难度等级：** 中等
**技术栈：** Python, FastAPI, Claude Code, GitHub API

---

*文档版本：* v1.0
*最后更新：* 2025-01-08
*维护者：* AI Development Team
