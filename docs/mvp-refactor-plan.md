# AI 开发调度服务 - MVP 快速交付方案

## 文档信息

| 项目 | 内容 |
|------|------|
| **方案名称** | 渐进式增强方案（轻量级 MVP） |
| **版本** | v1.0-mvp |
| **创建日期** | 2026-01-11 |
| **预计周期** | 2-3 周 |
| **技术栈** | Python 3.11+ / FastAPI / Vanilla JS / SQLite |

---

## 目录

1. [执行摘要](#执行摘要)
2. [MVP 功能清单](#mvp-功能清单)
3. [技术栈简化](#技术栈简化)
4. [架构设计](#架构设计)
5. [3 周交付计划](#3-周交付计划)
6. [具体实现方案](#具体实现方案)
7. [与 Plan B 对比](#与-plan-b-对比)
8. [成功指标](#成功指标)

---

## 执行摘要

### 核心策略

**采用渐进式增强，而非完整重构**

通过分析现有代码库，发现项目已具备：
- ✅ 完整的 FastAPI 后端
- ✅ SSE 实时日志流（已实现）
- ✅ HTML Dashboard（已有深色模式、任务列表）
- ✅ SQLite 数据持久化
- ✅ 基础配置管理

**结论：不需要重构，只需要优化！**

### 关键决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 前端框架 | **保留现有 HTML** | 无需 React，Vanilla JS 足够 |
| 构建工具 | **不需要** | 即改即用，无需 Vite |
| 状态管理 | **localStorage** | 简单场景足够 |
| Worktree 并行 | **延后 v1.1** | 单任务足够 MVP |
| 打包方式 | **pip + curl 脚本** | 比 NPX 简单 10x |

### 预期成果

| 指标 | Plan B | MVP 方案 | 改进 |
|------|--------|----------|------|
| 开发时间 | 4 周 | 2-3 周 | -30% |
| 新增代码 | ~6000 行 | ~1000 行 | -83% |
| npm 依赖 | 15+ | 0 | -100% |
| 页面加载 | ~500KB | ~50KB | -90% |
| 技术风险 | 高 | 低 | ✅ |

---

## MVP 功能清单

### 保留（核心功能）

| 功能 | 优先级 | 状态 | 说明 |
|------|--------|------|------|
| GitHub Webhook 接收 | P0 | ✅ 已实现 | 保留现有 |
| 任务状态跟踪（SQLite） | P0 | ✅ 已实现 | 保留现有 |
| SSE 实时日志流 | P0 | ✅ 已实现 | 保留现有 |
| 基础任务监控 Dashboard | P0 | ⚠️ 需优化 | 优化现有 HTML |
| 简化配置向导 | P0 | 🆕 新增 | 单页表单 |
| 一键安装脚本 | P0 | ⚠️ 需优化 | 改进 setup.sh |

### 延后到 v1.1（非核心）

| 功能 | 原计划 | 新计划 | 理由 |
|------|--------|--------|------|
| Git Worktree 并行 | P0 | **P1** | 单任务足够 MVP |
| React 前端 | P0 | **P1** | 现有 HTML 已够用 |
| NPX 打包分发 | P0 | **P1** | pip install 更简单 |
| WebSocket 实时通信 | P0 | **P1** | SSE 已足够 |
| Worktree 管理界面 | P0 | **P1** | 不需要 Worktree |

### 砍掉（过度设计）

| 功能 | 理由 |
|------|------|
| React Query | SSE + 轮询已足够 |
| Zustand | 简单状态不需要全局管理 |
| TailwindCSS | 内联 CSS + CSS 变量更轻量 |
| PyInstaller 打包 | 增加复杂度，用户已有 Python |
| shiv 打包 | 同上 |
| Docker 部署 | 延后，本地运行优先 |

---

## 技术栈简化

### 前端技术栈对比

| 组件 | Plan B（原方案）| **MVP 方案** | 理由 |
|------|----------------|-------------|------|
| 框架 | React 18 + Vite | **Vanilla JS** | 现有 HTML 已够用，无需构建 |
| 状态管理 | Zustand | **无需** | 简单页面，localStorage 即可 |
| 数据获取 | React Query | **fetch + SSE** | 已实现，无需抽象 |
| 样式 | TailwindCSS | **现有 CSS** | 已有 1000+ 行 CSS 足够 |
| 实时通信 | WebSocket | **SSE** | 已实现，单向推送够用 |
| 图标 | Lucide React | **SVG 内联** | 零依赖 |
| 构建步骤 | 需要（npm run build） | **不需要** | 即改即用 |

### 后端技术栈（保持不变）

```
Python 3.11+     # 已有
FastAPI          # 已有
SQLite           # 已有
Uvicorn          # 已有
PyGithub         # 已有
GitPython        # 已有
```

### 安装方式对比

| 方案 | 复杂度 | 用户体验 | 开发成本 | 推荐度 |
|------|--------|---------|---------|-------|
| NPX 打包 | 高 | 中 | 高 | ❌ 否 |
| PyInstaller 单文件 | 中 | 中 | 中 | ❌ 否 |
| **pip install** | **低** | **高** | **低** | ✅ **是** |
| **curl 一键脚本** | **低** | **高** | **低** | ✅ **是** |

---

## 架构设计

### 优化后架构（MVP）

```
┌───────────────────────────────────────────────────────────┐
│                      GitHub Webhook                        │
└───────────────────────────┬───────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────┐
│                    FastAPI Backend                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
│  │ Webhook  │  │  Task    │  │   API    │  │ Config  │  │
│  │ Handler  │  │ Service  │  │  Routes  │  │ Wizard  │  │
│  │  (已有)  │  │  (已有)  │  │  (已有)  │  │ (新增)  │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘  │
│         │              │              │                   │
│  ┌──────▼──────────────▼──────────────▼──────────────┐   │
│  │              SQLite Database                      │   │
│  └───────────────────────────────────────────────────┘   │
└───────────────────────────┬───────────────────────────────┘
                            │ SSE + JSON API
┌───────────────────────────▼───────────────────────────────┐
│         Enhanced HTML Dashboard (无需构建)                │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │
│  │ 任务监控   │  │ 配置向导   │  │   实时日志终端     │  │
│  │ (优化)     │  │ (新增)     │  │   (已有)           │  │
│  └────────────┘  └────────────┘  └────────────────────┘  │
│                                                           │
│  新增功能：                                               │
│  • 配置健康检查         • 一键复制 Webhook URL            │
│  • 错误诊断面板         • 快捷键支持                      │
│  • 任务批量操作         • 移动端适配                      │
└───────────────────────────────────────────────────────────┘
```

### 核心改进点

#### 1. Dashboard 增强

```html
<!-- 顶部栏 -->
<header>
  <div class="status-indicator">
    ✅ 配置正常 | 🔵 3 任务运行中
  </div>
  <button>📋 复制 Webhook URL</button>
  <button>⚙️ 设置</button>
  <button>?</button> <!-- 快捷键提示 -->
</header>

<!-- 任务卡片 -->
<div class="task-card">
  <h3>Issue #123: 实现用户认证</h3>
  <div class="progress">████████░░ 60%</div>
  <div class="meta">
    分支: ai/issue-123 | 开始: 14:30 | 预计: 15:15
  </div>
  <div class="actions">
    <button>查看日志</button>
    <button>取消</button>
  </div>
</div>
```

#### 2. 配置向导（单页）

```html
<div id="config-wizard" class="modal">
  <form>
    <section>
      <label>GitHub Token</label>
      <input type="password" placeholder="ghp_..." required>
      <small><a href="#">如何获取 →</a></small>
    </section>

    <section>
      <label>仓库路径</label>
      <input type="text" placeholder="/path/to/repo" required>
      <button type="button">浏览文件夹</button>
    </section>

    <section>
      <label>Anthropic API Key</label>
      <input type="password" placeholder="sk-ant-..." required>
    </section>

    <button type="submit">✓ 验证并保存</button>
  </form>
</div>
```

#### 3. 一键安装脚本

```bash
#!/bin/bash
# curl -sSL install.kaka.dev | sh

set -e

echo "🚀 Installing Kaka Dev..."

# 检测 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.11+ required"
    exit 1
fi

# 创建虚拟环境
python3 -m venv ~/.kaka-dev
source ~/.kaka-dev/bin/activate

# 安装
pip install kaka-dev

# 启动配置向导
kaka-dev configure

echo "✅ Ready! Run 'kaka-dev start' to begin"
```

---

## 3 周交付计划

### 第 1 周：核心体验优化

**目标**：让现有功能更好用

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 优化现有 Dashboard UI | 2 天 | 前端 | 更美观、响应式的监控页面 |
| 添加配置检测和引导 | 1 天 | 后端 | 首次访问显示配置向导入口 |
| 改进错误提示 | 1 天 | 前端 | 友好的错误信息和解决建议 |
| 优化日志查看器 | 1 天 | 前端 | 自动滚动、高亮、过滤 |

### 第 2 周：简化配置体验

**目标**：5 分钟完成配置

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 内嵌配置向导（单页） | 2 天 | 前端 | 无需跳转的配置表单 |
| 自动验证 GitHub Token | 1 天 | 后端 | 实时验证配置有效性 |
| 自动生成 Webhook Secret | 0.5 天 | 后端 | 一键生成安全密钥 |
| 一键安装脚本 | 1 天 | DevOps | `curl install.kaka.dev \| sh` |
| 配置导入/导出 | 0.5 天 | 后端 | 方便备份和迁移 |

### 第 3 周：打磨和发布

**目标**：生产可用

| 任务 | 工作量 | 负责人 | 产出 |
|------|--------|--------|------|
| 端到端测试 | 2 天 | QA | 完整工作流测试 |
| 文档编写 | 1 天 | 文档 | 简洁的 README 和 FAQ |
| 发布准备 | 1 天 | DevOps | 版本标记、Release notes |
| Demo 视频 | 1 天 | 产品 | 5 分钟使用演示 |

---

## 具体实现方案

### 1. Dashboard UI 优化

#### 1.1 顶部栏增强

```html
<!-- app/templates/dashboard.html -->
<header class="dashboard-header">
  <div class="header-left">
    <h1>🎯 AI 开发调度服务</h1>
    <div class="status-indicator" id="statusIndicator">
      <span class="status-dot"></span>
      <span class="status-text">检查中...</span>
    </div>
  </div>

  <div class="header-right">
    <button onclick="copyWebhookURL()" class="btn-secondary">
      📋 复制 Webhook URL
    </button>
    <button onclick="openSettings()" class="btn-secondary">
      ⚙️ 设置
    </button>
    <button onclick="showHelp()" class="btn-help">?</button>
  </div>
</header>

<script>
// 配置状态检查
async function checkConfigStatus() {
  const response = await fetch('/api/config/status');
  const status = await response.json();

  const indicator = document.getElementById('statusIndicator');
  if (status.configured) {
    indicator.innerHTML = '<span class="status-dot success"></span>配置正常';
  } else {
    indicator.innerHTML = '<span class="status-dot warning"></span>需要配置';
    // 显示配置向导
    setTimeout(() => openConfigWizard(), 1000);
  }
}

// 复制 Webhook URL
async function copyWebhookURL() {
  const response = await fetch('/api/config/webhook-url');
  const data = await response.json();

  await navigator.clipboard.writeText(data.url);
  showToast('✅ Webhook URL 已复制');
}
</script>
```

#### 1.2 任务卡片改进

```html
<div class="task-card" data-task-id="{{ task.id }}">
  <div class="task-header">
    <h3>Issue #{{ task.issue_number }}: {{ task.title }}</h3>
    <span class="task-status status-{{ task.status }}">
      {{ task.status_text }}
    </span>
  </div>

  <div class="task-progress">
    <div class="progress-bar">
      <div class="progress-fill" style="width: {{ task.progress }}%"></div>
    </div>
    <span class="progress-text">{{ task.progress }}%</span>
  </div>

  <div class="task-meta">
    <span>🔀 {{ task.branch }}</span>
    <span>🕐 {{ task.created_at }}</span>
    {% if task.pr_url %}
    <a href="{{ task.pr_url }}" target="_blank">🔗 PR #{{ task.pr_number }}</a>
    {% endif %}
  </div>

  <div class="task-actions">
    <button onclick="viewLogs('{{ task.id }}')" class="btn-primary">
      📋 查看日志
    </button>
    {% if task.status == 'running' %}
    <button onclick="cancelTask('{{ task.id }}')" class="btn-danger">
      ⏹ 取消
    </button>
    {% endif %}
  </div>
</div>
```

#### 1.3 日志查看器增强

```html
<div class="log-viewer" id="logViewer">
  <div class="log-toolbar">
    <select id="logLevelFilter" onchange="filterLogs()">
      <option value="all">全部</option>
      <option value="info">INFO</option>
      <option value="warning">WARNING</option>
      <option value="error">ERROR</option>
    </select>

    <input
      type="text"
      id="logSearch"
      placeholder="搜索日志..."
      oninput="filterLogs()"
    >

    <button onclick="toggleAutoScroll()" class="btn-toggle">
      🔄 自动滚动: <span id="autoScrollStatus">开</span>
    </button>

    <button onclick="exportLogs()" class="btn-secondary">
      📥 导出
    </button>
  </div>

  <div class="log-content" id="logContent">
    <!-- 日志内容通过 SSE 动态加载 -->
  </div>
</div>

<script>
const eventSource = new EventSource('/api/logs/stream');
let autoScroll = true;

eventSource.onmessage = (event) => {
  const log = JSON.parse(event.data);
  appendLog(log);

  if (autoScroll) {
    scrollToBottom();
  }
};

function appendLog(log) {
  const logContent = document.getElementById('logContent');
  const logLine = document.createElement('div');
  logLine.className = `log-line log-${log.level}`;
  logLine.innerHTML = `
    <span class="log-time">${log.timestamp}</span>
    <span class="log-level">${log.level}</span>
    <span class="log-message">${log.message}</span>
  `;
  logContent.appendChild(logLine);
}

function filterLogs() {
  const level = document.getElementById('logLevelFilter').value;
  const search = document.getElementById('logSearch').value.toLowerCase();

  document.querySelectorAll('.log-line').forEach(line => {
    const lineLevel = line.dataset.level;
    const lineMessage = line.dataset.message.toLowerCase();

    const levelMatch = level === 'all' || lineLevel === level;
    const searchMatch = !search || lineMessage.includes(search);

    line.style.display = levelMatch && searchMatch ? 'block' : 'none';
  });
}
</script>
```

### 2. 配置向导实现

#### 2.1 后端 API

```python
# app/api/config.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import secrets

router = APIRouter()

class ConfigRequest(BaseModel):
    github_token: str
    repo_owner: str
    repo_name: str
    repo_path: str
    anthropic_api_key: str

@router.get("/api/config/status")
async def get_config_status():
    """检查配置状态"""
    from app.config import config

    return {
        "configured": config.is_configured(),
        "missing_keys": config.get_missing_keys()
    }

@router.post("/api/config/validate")
async def validate_config(req: ConfigRequest):
    """验证配置"""
    results = {}

    # 验证 GitHub Token
    try:
        from app.services.github_service import GitHubService
        github = GitHubService(req.github_token)
        results["github_token"] = {
            "valid": await github.authenticate(),
            "message": "Token 有效" if await github.authenticate() else "Token 无效"
        }
    except Exception as e:
        results["github_token"] = {"valid": False, "message": str(e)}

    # 验证仓库路径
    from pathlib import Path
    repo_path = Path(req.repo_path)
    results["repo_path"] = {
        "valid": repo_path.exists() and (repo_path / ".git").exists(),
        "message": "有效" if (repo_path / ".git").exists() else "不是 Git 仓库"
    }

    # 验证 API Key
    try:
        from app.services.claude_service import ClaudeService
        claude = ClaudeService(req.anthropic_api_key)
        results["anthropic_api_key"] = {
            "valid": await claude.authenticate(),
            "message": "API Key 有效"
        }
    except Exception as e:
        results["anthropic_api_key"] = {"valid": False, "message": str(e)}

    return results

@router.post("/api/config/save")
async def save_config(req: ConfigRequest):
    """保存配置"""
    # 先验证
    validation = await validate_config(req)

    if not all(r["valid"] for r in validation.values()):
        raise HTTPException(400, detail=validation)

    # 保存到环境变量或配置文件
    from app.config import config
    await config.update(req.dict())

    return {"success": True, "message": "配置已保存"}

@router.get("/api/config/webhook-url")
async def get_webhook_url():
    """获取 Webhook URL"""
    from app.config import config
    from app.utils.webhook import generate_webhook_url

    return {
        "url": generate_webhook_url(config),
        "secret": config.webhook_secret
    }
```

#### 2.2 前端配置向导

```html
<!-- app/templates/config_wizard.html -->
<div id="configWizard" class="modal-overlay">
  <div class="modal-content">
    <div class="modal-header">
      <h2>🔧 首次使用配置</h2>
      <button onclick="closeConfigWizard()" class="btn-close">×</button>
    </div>

    <form id="configForm" onsubmit="submitConfig(event)">
      <!-- GitHub Token -->
      <div class="form-group">
        <label>GitHub Personal Access Token</label>
        <input
          type="password"
          name="github_token"
          placeholder="ghp_xxxxxxxxxxxx"
          required
          onblur="validateField('github_token')"
        >
        <small class="help-text">
          <a href="https://github.com/settings/tokens" target="_blank">
            如何获取 Token →
          </a>
        </small>
        <div class="field-status" id="status-github_token"></div>
      </div>

      <!-- 仓库信息 -->
      <div class="form-row">
        <div class="form-group">
          <label>仓库所有者</label>
          <input
            type="text"
            name="repo_owner"
            placeholder="your-username"
            required
          >
        </div>

        <div class="form-group">
          <label>仓库名称</label>
          <input
            type="text"
            name="repo_name"
            placeholder="your-repo"
            required
          >
        </div>
      </div>

      <!-- 仓库路径 -->
      <div class="form-group">
        <label>本地仓库路径</label>
        <div class="input-group">
          <input
            type="text"
            name="repo_path"
            placeholder="/path/to/your/repo"
            required
            onblur="validateField('repo_path')"
          >
          <button type="button" onclick="browseFolder()">浏览</button>
        </div>
        <div class="field-status" id="status-repo_path"></div>
      </div>

      <!-- Anthropic API Key -->
      <div class="form-group">
        <label>Anthropic API Key</label>
        <input
          type="password"
          name="anthropic_api_key"
          placeholder="sk-ant-xxxxxxxxxxxx"
          required
          onblur="validateField('anthropic_api_key')"
        >
        <small class="help-text">
          <a href="https://console.anthropic.com/" target="_blank">
            如何获取 API Key →
          </a>
        </small>
        <div class="field-status" id="status-anthropic_api_key"></div>
      </div>

      <div class="form-actions">
        <button type="submit" class="btn-primary" id="submitBtn">
          ✓ 验证并保存
        </button>
      </div>
    </form>
  </div>
</div>

<script>
async function validateField(fieldName) {
  const form = document.getElementById('configForm');
  const formData = new FormData(form);
  const data = Object.fromEntries(formData);

  const response = await fetch('/api/config/validate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  });

  const result = await response.json();

  // 更新状态显示
  const statusEl = document.getElementById(`status-${fieldName}`);
  if (result[fieldName].valid) {
    statusEl.innerHTML = `<span class="status-success">✓ ${result[fieldName].message}</span>`;
  } else {
    statusEl.innerHTML = `<span class="status-error">✗ ${result[fieldName].message}</span>`;
  }
}

async function submitConfig(event) {
  event.preventDefault();

  const form = event.target;
  const formData = new FormData(form);
  const data = Object.fromEntries(formData);

  const submitBtn = document.getElementById('submitBtn');
  submitBtn.disabled = true;
  submitBtn.textContent = '验证中...';

  try {
    const response = await fetch('/api/config/save', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    });

    if (response.ok) {
      showToast('✅ 配置已保存！');
      closeConfigWizard();
      // 刷新页面
      setTimeout(() => location.reload(), 1000);
    } else {
      const error = await response.json();
      showToast('❌ 配置失败：' + error.detail);
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = '✓ 验证并保存';
  }
}

function browseFolder() {
  // 提示用户输入路径
  const path = prompt('请输入仓库的绝对路径：');
  if (path) {
    document.querySelector('[name="repo_path"]').value = path;
    validateField('repo_path');
  }
}
</script>
```

### 3. 一键安装脚本

#### 3.1 安装脚本

```bash
#!/bin/bash
# scripts/install.sh
set -e

echo "🚀 Installing Kaka Dev..."
echo ""

# 检测 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.11+ is required"
    echo "Please install Python 3.11 or later from https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Found Python $PYTHON_VERSION"

# 检查版本
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "❌ Python 3.11+ is required (found $PYTHON_VERSION)"
    exit 1
fi

# 创建虚拟环境
echo ""
echo "Creating virtual environment..."
python3 -m venv ~/.kaka-dev

# 激活虚拟环境
source ~/.kaka-dev/bin/activate

# 升级 pip
echo "Upgrading pip..."
pip install --upgrade pip > /dev/null

# 安装
echo "Installing kaka-dev..."
pip install kaka-dev

# 运行配置向导
echo ""
echo "✅ Installation complete!"
echo ""
echo "Launching configuration wizard..."
kaka-dev configure

echo ""
echo "🎉 Ready!"
echo ""
echo "To start the service:"
echo "  kaka-dev start"
echo ""
echo "To configure later:"
echo "  kaka-dev configure"
```

#### 3.2 Python CLI 入口

```python
# app/cli.py
import click
from pathlib import Path

@click.group()
def cli():
    """AI 开发调度服务 CLI"""
    pass

@cli.command()
def start():
    """启动服务"""
    import uvicorn
    from app.main import app

    click.echo("🚀 Starting Kaka Dev...")
    click.echo(f"📍 Dashboard: http://localhost:8000")
    click.echo(f"📍 Webhook: http://localhost:8000/webhook/github")
    click.echo("")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

@cli.command()
def configure():
    """打开配置向导"""
    import webbrowser
    from app.config import config

    # 启动服务
    import threading
    import uvicorn

    def run_server():
        from app.main import app
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

    server = threading.Thread(target=run_server, daemon=True)
    server.start()

    # 等待服务启动
    import time
    time.sleep(2)

    # 打开浏览器
    url = "http://localhost:8000/config"
    click.echo(f"🌐 Opening {url}")
    webbrowser.open(url)

    # 保持运行
    click.echo("Configuration wizard is running. Press Ctrl+C to exit.")
    server.join()

@cli.command()
@click.argument('action', type=click.Choice(['export', 'import']))
def config(action):
    """导出或导入配置"""
    import json

    if action == 'export':
        from app.config import config
        data = config.export()

        config_file = Path.home() / 'kaka-dev-config.json'
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)

        click.echo(f"✅ Configuration exported to {config_file}")

    elif action == 'import':
        config_file = Path.home() / 'kaka-dev-config.json'

        if not config_file.exists():
            click.echo("❌ Configuration file not found")
            return

        with open(config_file) as f:
            data = json.load(f)

        from app.config import config
        config.import_data(data)

        click.echo("✅ Configuration imported")

if __name__ == '__main__':
    cli()
```

#### 3.3 pyproject.toml 配置

```toml
[project]
name = "kaka-dev"
version = "1.0.0"
description = "AI 开发调度服务"
authors = [{name = "Your Name"}]
license = {text = "MIT"}
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.5.0",
    "pygithub>=1.59.0",
    "gitpython>=3.1.0",
    "loguru>=0.7.0",
    "click>=8.1.0",
]

[project.scripts]
kaka-dev = "app.cli:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## 与 Plan B 对比

### 架构对比

| 方面 | Plan B（完整重构） | MVP 方案（渐进增强） |
|------|-------------------|---------------------|
| 前端框架 | React 18 + Vite | Vanilla JS（现有） |
| 构建工具 | Vite | 无需构建 |
| 状态管理 | Zustand | localStorage |
| 样式方案 | TailwindCSS | 现有 CSS |
| 实时通信 | WebSocket | SSE（已有） |
| 并行方案 | Git Worktree | 单任务（MVP） |
| 打包方式 | NPX + PyInstaller | pip + curl 脚本 |
| 配置向导 | 多步向导 | 单页表单 |

### 开发工作量对比

| 任务 | Plan B | MVP 方案 | 节省 |
|------|--------|----------|------|
| 前端开发 | 2 周 | 3 天 | 70% |
| 后端开发 | 1.5 周 | 1 周 | 33% |
| 打包配置 | 1 周 | 2 天 | 70% |
| 测试 | 1 周 | 2 天 | 70% |
| **总计** | **5.5 周** | **2.5 周** | **55%** |

### 代码量对比

| 类型 | Plan B | MVP 方案 | 减少 |
|------|--------|----------|------|
| 前端代码 | ~5000 行 | ~1500 行 | -70% |
| 后端代码 | +2000 行 | +500 行 | -75% |
| 配置文件 | +500 行 | +100 行 | -80% |
| npm 依赖 | 15+ | 0 | -100% |
| 构建配置 | 复杂 | 无需 | ✅ |

---

## 成功指标

### 用户体验指标

| 指标 | Plan B 目标 | MVP 目标 | 检测方式 |
|------|-----------|---------|---------|
| 首次配置时间 | 5 分钟 | **3 分钟** | 计时测试 |
| 安装步骤数 | 1 命令 | **1 命令** | 文档验证 |
| 配置错误率 | <10% | **<5%** | 实时验证 |
| 页面首次加载 | <2s | **<500ms** | 性能测试 |
| 日志实时延迟 | <500ms | **<300ms** | SSE 测试 |

### 技术指标

| 指标 | Plan B 目标 | MVP 目标 |
|------|-----------|---------|
| 代码覆盖率 | >80% | >70% |
| API 响应时间 | <200ms | <100ms |
| 内存使用（空闲） | <500MB | <200MB |
| 包体积 | ~500MB | ~50MB（pip） |

### 质量指标

| 指标 | 目标 |
|------|------|
| 配置完成率 | >90% |
| 首次运行成功率 | >95% |
| 用户满意度（NPS） | >50 |

---

## 风险管理

### 技术风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| Vanilla JS 维护困难 | 中 | 低 | 保持代码简单，充分注释 |
| XSS 攻击 | 低 | 中 | Jinja2 自动转义，CSP 策略 |
| SSE 兼容性 | 低 | 低 | 广泛支持，有降级方案 |
| 安装脚本失败 | 中 | 高 | 充分测试，详细错误提示 |

### 产品风险

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 用户期望 React UI | 低 | 低 | 现有 UI 已美观 |
| 单任务不够用 | 低 | 中 | v1.1 添加并行支持 |
| 配置复杂度高 | 中 | 高 | 实时验证，详细提示 |

---

## 后续版本规划

### v1.1（1-2 个月后）

- [ ] Git Worktree 并行支持
- [ ] 多任务并发控制
- [ ] 任务优先级队列
- [ ] Docker 部署支持

### v1.2（3-4 个月后）

- [ ] React 前端重构（可选）
- [ ] WebSocket 替代 SSE
- [ ] 完整的任务历史记录
- [ ] 统计分析面板

### v2.0（6 个月后）

- [ ] 分布式任务调度
- [ ] 多租户支持
- [ ] 插件系统
- [ ] 自定义 AI 模型

---

## 总结

### 核心原则

1. **快速交付**：2-3 周而非 4 周
2. **渐进增强**：优化现有，而非重写
3. **用户体验优先**：配置简单，界面美观
4. **技术风险最小化**：使用成熟技术，避免过度工程

### 关键决策

```
✅ 保留：FastAPI、SQLite、SSE、现有 HTML
❌ 放弃：React、Worktree、NPX、WebSocket
⏳ 延后：并行任务、Docker、高级功能
```

### 一句话总结

> **用现有架构 + 优化 UI + 简化配置 = 2 周内交付用户可用的产品**

---

**文档版本**: v1.0
**创建日期**: 2026-01-11
**维护者**: Kaka Dev Team
