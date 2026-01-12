# 技术架构

本文档详细说明 Kaka 的系统架构设计。

## 目录

- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [项目结构](#项目结构)
- [数据流](#数据流)
- [并发模型](#并发模型)

---

## 技术栈

### 核心技术

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **Web 框架** | FastAPI | ≥0.104.1 | 高性能异步 Web 框架 |
| **服务器** | Uvicorn | ≥0.24.0 | ASGI 服务器 |
| **GitHub API** | PyGithub | ≥2.1.1 | GitHub API 客户端 |
| **Git 操作** | GitPython | ≥3.1.40 | Git 库 |
| **配置管理** | PyYAML + Pydantic | ≥2.5.0 | 配置和验证 |
| **安全加密** | Cryptography | ≥41.0.7 | 加密和签名验证 |
| **日志** | Structlog | ≥23.2.0 | 结构化日志 |

### 依赖库

- `pydantic` - 数据验证
- `python-dotenv` - 环境变量管理
- `structlog` - 结构化日志
- `pytest` - 测试框架

---

## 系统架构

### 整体架构

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

### 组件说明

#### 1. Webhook Handler

- 接收 GitHub Webhook 请求
- 验证签名（HMAC-SHA256）
- 解析事件类型和数据
- 验证触发条件

#### 2. GitHub Service

- 与 GitHub API 交互
- 获取 Issue 信息
- 创建 Pull Request
- 发送评论通知

#### 3. Git Service

- 本地 Git 操作
- 创建分支
- 提交代码
- 推送到远程

#### 4. Claude Service

- 调用 Claude Code CLI
- 管理执行进程
- 处理超时和错误

---

## 项目结构

### 目录结构

```
kaka/
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
│   │   ├── health.py           # 健康检查端点
│   │   ├── tasks.py            # 任务管理 API
│   │   ├── config.py           # 配置管理 API
│   │   └── dashboard.py        # Dashboard 路由
│   ├── db/                     # 数据库
│   │   ├── database.py         # 数据库连接
│   │   └── models.py           # ORM 模型
│   ├── core/                   # 核心功能
│   │   └── error_handlers.py   # 统一异常处理
│   └── utils/                  # 工具函数
│       ├── logger.py           # 日志工具
│       ├── validators.py       # Webhook 验证器
│       └── concurrency.py      # 并发管理器
├── config/
│   └── config.yaml             # 配置文件
├── scripts/                    # 开发和测试脚本
├── dev_setup.sh                # 开发环境初始化脚本
├── tests/                      # 测试套件
├── logs/                       # 日志文件目录
├── templates/                  # HTML 模板
│   ├── dashboard_enhanced.html
│   └── config_wizard.html
├── .vscode/                    # VSCode 配置
│   ├── settings.json           # 编辑器设置
│   └── launch.json             # 调试配置
├── requirements.txt            # Python 依赖
├── pyproject.toml             # 项目配置
└── Makefile                    # 自动化命令
```

### 模块说明

| 模块 | 职责 |
|------|------|
| `app/main.py` | FastAPI 应用入口，路由注册，中间件配置，生命周期管理 |
| `app/config.py` | 配置加载和管理，使用 Pydantic Settings |
| `app/models/` | Pydantic 数据模型定义 |
| `app/services/` | 核心业务逻辑实现 |
| `app/api/` | API 路由和端点定义 |
| `app/db/` | 数据库模型和连接管理 |
| `app/core/` | 核心功能模块（异常处理等） |
| `app/utils/` | 工具函数和辅助类（日志、验证、并发） |

---

## 数据流

### Webhook 处理流程

```
1. GitHub 发送 Webhook
   ↓
2. FastAPI 接收请求
   ↓
3. 验证签名（validators.py）
   ↓
4. 解析事件（webhook_handler.py）
   ↓
5. 检查触发条件
   ↓
6. 创建任务（db/models.py）
   ↓
7. 加入队列（concurrency.py）
   ↓
8. 执行开发任务
   ├─ Git 操作（git_service.py）
   ├─ Claude CLI（claude_service.py）
   └─ GitHub API（github_service.py）
   ↓
9. 更新任务状态
   ↓
10. 返回结果
```

---

## 并发模型

### 任务队列

- 使用 SQLAlchemy 实现任务持久化
- 支持任务状态跟踪
- 支持任务重试机制

### 并发控制

```python
class ConcurrencyManager:
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def acquire(self):
        await self.semaphore.acquire()

    def release(self):
        self.semaphore.release()
```

### 任务状态

| 状态 | 说明 |
|------|------|
| `pending` | 待处理 |
| `running` | 运行中 |
| `completed` | 已完成 |
| `failed` | 失败 |
| `cancelled` | 已取消 |

---

## 数据模型

### Task 模型

```python
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    task_id = Column(String, unique=True, nullable=False)
    issue_number = Column(Integer, nullable=False)
    issue_title = Column(String, nullable=False)
    issue_url = Column(String, nullable=False)
    branch_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    success = Column(Boolean)
    error_message = Column(Text)
    execution_time = Column(Float)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=2)
```

---

## 扩展性

### 添加新的触发方式

1. 在 `webhook_handler.py` 中添加新的触发条件
2. 更新配置文件 `config.yaml`
3. 添加相应的测试

### 添加新的服务

1. 在 `app/services/` 中创建新文件
2. 继承 `BaseService` 类
3. 实现服务逻辑
4. 在 `webhook_handler.py` 中调用

### 添加新的 API 端点

1. 在 `app/api/` 中创建新路由文件
2. 定义 FastAPI 路由
3. 在 `app/main.py` 中注册路由

---

## 性能考虑

### 异步处理

- 使用 FastAPI 的异步支持
- 长时间运行的任务使用后台任务
- 避免阻塞主线程

### 数据库优化

- 使用连接池
- 适当使用索引
- 定期清理旧数据

### 缓存策略

- 配置缓存（可选）
- API 响应缓存（可选）

---

## 相关文档

- [使用指南](USAGE.md) - 使用说明
- [开发指南](DEVELOPMENT.md) - 开发文档
- [日志系统](LOGGING.md) - 日志配置和使用
