# 日志系统

本文档详细说明 Kaka 的日志系统设计和使用。

## 目录

- [日志配置](#日志配置)
- [日志级别](#日志级别)
- [日志位置](#日志位置)
- [日志格式](#日志格式)
- [查看日志](#查看日志)
- [日志架构](#日志架构)

---

## 日志配置

### 配置文件

日志配置位于 `config/config.yaml`：

```yaml
logging:
  level: "INFO"           # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "logs/kaka.log"   # 日志文件路径
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  console: true           # 是否输出到控制台
  json: false             # 是否使用 JSON 格式
  max_bytes: 10485760     # 单个日志文件最大 10MB
  backup_count: 5         # 保留 5 个日志备份
```

### 环境变量

可以通过环境变量覆盖配置：

```bash
export LOG_LEVEL=DEBUG
export LOG_FILE=logs/debug.log
```

---

## 日志级别

| 级别 | 说明 | 使用场景 |
|------|------|----------|
| **DEBUG** | 详细调试信息 | 开发调试 |
| **INFO** | 一般信息 | 正常运行（默认） |
| **WARNING** | 警告信息 | 潜在问题 |
| **ERROR** | 错误信息 | 错误但可继续 |
| **CRITICAL** | 严重错误 | 系统无法继续 |

### 修改日志级别

**方式 1: 修改配置文件**

编辑 `config/config.yaml`：

```yaml
logging:
  level: "DEBUG"
```

**方式 2: 使用环境变量**

```bash
export LOG_LEVEL=DEBUG
kaka start
```

**方式 3: 临时修改**

```bash
LOG_LEVEL=DEBUG kaka start
```

---

## 日志位置

### 服务启动时显示

服务启动时会显示日志文件地址：

```
============================================================
🚀 AI 开发调度服务启动中...
============================================================
✅ 配置加载成功
✅ 配置验证通过
✅ 日志系统初始化完成 (级别: INFO)
✅ 数据库初始化完成
✅ 并发管理器初始化完成 (最大并发: 1)
📋 仓库: your-repo
📂 本地路径: /path/to/repo
🏷️  触发标签: ai-dev
💬 触发命令: /ai develop
📝 日志文件: logs/kaka.log          ← 日志文件地址
============================================================
✅ 服务启动完成
============================================================
```

### 日志文件结构

```
logs/
├── kaka.log           # 当前日志文件
├── kaka.log.1         # 第 1 个备份
├── kaka.log.2         # 第 2 个备份
├── kaka.log.3         # 第 3 个备份
├── kaka.log.4         # 第 4 个备份
└── kaka.log.5         # 第 5 个备份
```

日志文件自动轮转：
- 单个文件最大 10MB
- 保留最近 5 个备份
- 自动清理旧日志

---

## 日志格式

### 标准格式

```
2026-01-12 21:13:45,248 - app.main - INFO - ✅ 服务启动完成
```

格式：`时间戳 - 模块名 - 级别 - 消息`

### 模块分类

| 模块前缀 | 说明 | 示例 |
|----------|------|------|
| `app.main` | 应用主入口 | 启动、关闭、配置 |
| `app.api.health` | 健康检查 API | `/health` 请求 |
| `app.api.tasks` | 任务管理 API | 任务 CRUD 操作 |
| `app.db.database` | 数据库操作 | 数据库初始化 |
| `app.utils.concurrency` | 并发管理 | 任务调度 |
| `app.services.webhook_handler` | Webhook 处理 | GitHub 事件处理 |
| `app.services.github_service` | GitHub API | PR 创建、评论 |
| `app.services.git_service` | Git 操作 | 分支、提交、推送 |
| `uvicorn` | Uvicorn 服务器 | HTTP 请求日志 |
| `uvicorn.access` | 访问日志 | HTTP 访问记录 |
| `uvicorn.error` | 错误日志 | Uvicorn 错误 |

---

## 查看日志

### 实时监控

```bash
# 实时查看所有日志
tail -f logs/kaka.log

# 实时查看并高亮错误
tail -f logs/kaka.log | grep --color=auto ERROR
```

### 查看最近日志

```bash
# 查看最近 20 行
tail -n 20 logs/kaka.log

# 查看最近 50 行
tail -n 50 logs/kaka.log
```

### 按级别过滤

```bash
# 只看错误日志
grep ERROR logs/kaka.log

# 只看警告和错误
grep -E "WARNING|ERROR" logs/kaka.log

# 排除 DEBUG 信息
grep -v DEBUG logs/kaka.log
```

### 按模块过滤

```bash
# 只看 Webhook 相关日志
grep webhook_handler logs/kaka.log

# 只看数据库相关日志
grep database logs/kaka.log

# 只看 API 相关日志
grep "app.api" logs/kaka.log
```

### 按时间过滤

```bash
# 查看今天的日志
grep "2026-01-12" logs/kaka.log

# 查看特定时间段的日志
grep "2026-01-12 21:" logs/kaka.log
```

### 使用 CLI 工具

```bash
# 使用 kaka CLI 查看日志
kaka logs

# 实时查看
kaka logs --follow

# 只看错误
kaka logs --level error
```

---

## 日志架构

### 日志系统设计

```
┌─────────────────────────────────────────────────────────────┐
│                        日志系统架构                          │
└─────────────────────────────────────────────────────────────┘

1. 根记录器 (Root Logger)
   ├─ 文件处理器 (RotatingFileHandler)
   │  ├─ 输出到: logs/kaka.log
   │  ├─ 最大文件: 10MB
   │  └─ 备份数量: 5
   │
   └─ 控制台处理器 (StreamHandler)
      ├─ 输出到: stdout
      └─ 级别: 从配置读取

2. 应用模块日志
   ├─ app.main → 传播到根记录器
   ├─ app.api.* → 传播到根记录器
   ├─ app.services.* → 传播到根记录器
   └─ app.utils.* → 传播到根记录器

3. 第三方库日志
   ├─ uvicorn → 传播到根记录器
   ├─ uvicorn.access → 传播到根记录器
   └─ uvicorn.error → 传播到根记录器
```

### 日志传播机制

```python
# app/main.py
logger = logging.getLogger(__name__)  # app.main
logger.info("这条日志会传播到根记录器")

# 根记录器配置
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)    # 文件输出
root_logger.addHandler(console_handler) # 控制台输出
```

**设计原则**：

1. **统一输出**：所有日志统一由根记录器处理
2. **模块独立**：各模块使用自己的 logger，互不干扰
3. **自动传播**：模块日志自动传播到根记录器
4. **灵活配置**：通过配置文件统一管理日志行为

### 日志初始化流程

```python
# 1. 模块加载时创建临时 logger
logger = logging.getLogger(__name__)

# 2. 应用启动时初始化日志系统
setup_logging()

# 3. 配置根记录器
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# 4. 配置第三方库日志
for name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
    logging.getLogger(name).propagate = True

# 5. 应用生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时记录
    logger.info("✅ 服务启动完成")
    yield
    # 关闭时记录
    logger.info("🛑 服务关闭中...")
```

---

## 调试技巧

### 1. 启用 DEBUG 模式

```yaml
# config/config.yaml
logging:
  level: "DEBUG"
```

### 2. 追踪特定模块

```bash
# 追踪 Webhook 处理
grep "webhook_handler" logs/kaka.log

# 追溯完整请求链
grep -E "POST /webhook|webhook_handler|github_service" logs/kaka.log
```

### 3. 分析性能问题

```bash
# 查看包含处理时间的日志
grep "process_time" logs/kaka.log
```

### 4. 错误诊断

```bash
# 查看最近的错误
tail -n 100 logs/kaka.log | grep -A 10 ERROR
```

---

## 最佳实践

### 1. 代码中使用日志

```python
from app.utils.logger import get_logger

logger = get_logger(__name__)

# DEBUG - 详细调试信息
logger.debug(f"处理配置: {config}")

# INFO - 一般信息
logger.info("✅ 任务创建成功")

# WARNING - 警告信息
logger.warning("⚠️  配置文件未找到，使用默认值")

# ERROR - 错误信息
logger.error(f"❌ 处理失败: {error}", exc_info=True)

# CRITICAL - 严重错误
logger.critical("💥 数据库连接失败")
```

### 2. 日志消息规范

- **✅ 使用 emoji 标记状态**：`✅` 成功、`❌` 失败、`⚠️` 警告
- **📋 使用清晰的描述**：说明发生了什么
- **🔍 包含上下文信息**：提供足够的调试信息
- **⚡ 避免过度日志**：不要记录敏感信息

### 3. 错误日志示例

```python
try:
    process_webhook(event)
except Exception as e:
    logger.error(
        f"Webhook 处理失败: delivery={delivery_id}, event={event_type}",
        exc_info=True  # 包含完整的 traceback
    )
```

---

## 相关文档

- [开发指南](DEVELOPMENT.md) - 开发者文档
- [架构文档](ARCHITECTURE.md) - 系统架构
- [配置说明](CONFIGURATION.md) - 详细配置
