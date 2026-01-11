# API 文档

Kaka AI Dev 完整 API 参考

---

## 基础信息

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`
- **API 版本**: v0.2.0

---

## 📋 目录

- [配置 API](#配置-api)
- [任务 API](#任务-api)
- [日志 API](#日志-api)
- [健康检查](#健康检查)
- [Webhook](#webhook)

---

## 配置 API

### GET /api/config/status

获取配置状态

**响应**:
```json
{
  "configured": true,
  "missing_keys": [],
  "webhook_url": "http://localhost:8000/webhook/github",
  "repo_info": {
    "repo_full_name": "owner/repo",
    "repo_path": "/path/to/repo",
    "default_branch": "main"
  }
}
```

### POST /api/config/validate

验证配置

**请求**:
```json
{
  "github_token": "ghp_xxxxxxxxxxxx",
  "repo_owner": "owner",
  "repo_name": "repo",
  "repo_path": "/path/to/repo"
}
```

**响应**:
```json
{
  "github_token": {
    "valid": true,
    "message": "Token 有效"
  },
  "github_repository": {
    "valid": true,
    "message": "仓库存在"
  },
  "repo_path": {
    "valid": true,
    "message": "有效: /path/to/repo"
  },
  "anthropic_api_key": {
    "valid": true,
    "message": "API Key 格式有效"
  }
}
```

### POST /api/config/save

保存配置到 .env 文件

**请求**:
```json
{
  "github_token": "ghp_xxxxxxxxxxxx",
  "repo_owner": "owner",
  "repo_name": "repo",
  "repo_path": "/path/to/repo",
  "anthropic_api_key": "sk-ant-xxxxxxxxxxxx",
  "webhook_secret": null
}
```

**响应**:
```json
{
  "success": true,
  "message": "配置已保存",
  "webhook_secret": "generated-secret"
}
```

### GET /api/config/webhook-url

获取 Webhook URL

**响应**:
```json
{
  "url": "http://localhost:8000/webhook/github",
  "secret": "your-webhook-secret"
}
```

### POST /api/config/generate-secret

生成新的 Webhook Secret

**响应**:
```json
{
  "secret": "random-secret-string",
  "message": "请将此密钥保存到 .env 文件的 GITHUB_WEBHOOK_SECRET 变量中"
}
```

---

## 任务 API

### GET /api/tasks

获取任务列表

**查询参数**:
- `status` (可选): 任务状态筛选 (`pending|running|completed|failed|cancelled`)
- `limit` (可选): 返回数量限制 (1-1000)，默认 100
- `offset` (可选): 偏移量，默认 0

**响应**:
```json
{
  "tasks": [
    {
      "task_id": "task-abc123",
      "issue_number": 123,
      "issue_title": "修复登录 Bug",
      "status": "running",
      "branch_name": "ai/feature-123-1704685847",
      "created_at": "2024-01-08T10:30:45Z",
      "updated_at": "2024-01-08T10:35:20Z",
      "execution_time": 45.2,
      "progress": 60
    }
  ],
  "total": 1,
  "stats": {
    "total": 10,
    "pending": 2,
    "running": 1,
    "completed": 6,
    "failed": 1,
    "cancelled": 0
  }
}
```

### GET /api/tasks/stats

获取任务统计

**响应**:
```json
{
  "total": 10,
  "pending": 2,
  "running": 1,
  "completed": 6,
  "failed": 1,
  "cancelled": 0
}
```

### GET /api/tasks/{task_id}

获取任务详情

**响应**:
```json
{
  "task": {
    "task_id": "task-abc123",
    "issue_number": 123,
    "issue_title": "修复登录 Bug",
    "status": "running",
    "branch_name": "ai/feature-123-1704685847",
    "created_at": "2024-01-08T10:30:45Z",
    "updated_at": "2024-01-08T10:35:20Z",
    "execution_time": 45.2,
    "retry_count": 0,
    "max_retries": 2
  },
  "logs": [
    {
      "id": 1,
      "task_id": "task-abc123",
      "level": "INFO",
      "message": "开始处理 Issue #123",
      "timestamp": "2024-01-08T10:30:46Z"
    }
  ]
}
```

### POST /api/tasks/{task_id}/cancel

取消任务

**响应**:
```json
{
  "success": true,
  "message": "任务已取消，进程已终止",
  "task": {
    "task_id": "task-abc123",
    "status": "cancelled"
  },
  "process_terminated": true
}
```

### POST /api/tasks/{task_id}/retry

重试失败任务

**响应**:
```json
{
  "success": true,
  "message": "任务已重新加入队列 (第 1 次重试)，正在后台执行...",
  "task": {
    "task_id": "task-abc123",
    "retry_count": 1
  }
}
```

### GET /api/concurrency/stats

获取并发状态

**响应**:
```json
{
  "max_concurrent": 3,
  "current_running": 1,
  "available": 2
}
```

---

## 日志 API

### GET /api/tasks/{task_id}/logs/stream

SSE 日志流（Server-Sent Events）

**事件类型**:
- `message` - 日志消息
- `done` - 任务完成

**示例**:
```javascript
const eventSource = new EventSource('/api/tasks/task-abc123/logs/stream');

eventSource.onmessage = (event) => {
  const log = JSON.parse(event.data);
  console.log(log);
};

eventSource.addEventListener('done', (event) => {
  console.log('Task completed');
  eventSource.close();
});
```

---

## 健康检查

### GET /health

健康检查端点

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-08T10:30:45Z",
  "version": "0.2.0"
}
```

### GET /

根端点

**响应**:
```json
{
  "service": "AI 开发调度服务",
  "version": "0.2.0",
  "status": "running",
  "docs": "/docs",
  "health": "/health"
}
```

---

## Webhook

### POST /webhook/github

GitHub Webhook 接收端点

**请求头**:
```
Content-Type: application/json
X-Hub-Signature-256: sha256=<signature>
X-GitHub-Event: issues
X-GitHub-Delivery: <delivery-id>
```

**请求体** (示例):
```json
{
  "action": "labeled",
  "issue": {
    "id": 123456789,
    "number": 123,
    "title": "修复登录 Bug",
    "body": "用户无法登录系统...",
    "html_url": "https://github.com/owner/repo/issues/123"
  },
  "label": {
    "name": "ai-dev"
  },
  "repository": {
    "full_name": "owner/repo"
  },
  "sender": {
    "login": "username"
  }
}
```

**响应**:
```json
{
  "status": "accepted",
  "message": "Webhook 已接收，正在后台处理",
  "delivery_id": "123456-7890-1234-5678",
  "event_type": "labeled"
}
```

**触发条件**:

1. 标签触发:
   - Issue 添加 `ai-dev` 标签

2. 评论触发:
   - Issue 评论包含 `/ai develop`

---

## 错误响应

所有错误返回统一格式：

```json
{
  "detail": "错误描述信息"
}
```

**HTTP 状态码**:
- `400` - 请求参数错误
- `401` - 签名验证失败
- `404` - 资源不存在
- `500` - 服务器内部错误

---

## 速率限制

所有 API 端点受速率限制保护：

- **默认限制**: 60 次/分钟
- **Webhook 限制**: 10 次/分钟

超出限制时返回 `429 Too Many Requests`

---

## 交互式文档

### Swagger UI

访问 `/docs` 查看交互式 API 文档

### ReDoc

访问 `/redoc` 查看替代文档

---

## 示例代码

### Python

```python
import requests

# 获取任务列表
response = requests.get('http://localhost:8000/api/tasks')
tasks = response.json()

# 取消任务
response = requests.post('http://localhost:8000/api/tasks/task-abc123/cancel')
result = response.json()
```

### JavaScript

```javascript
// 获取任务列表
const response = await fetch('http://localhost:8000/api/tasks');
const data = await response.json();

// 取消任务
await fetch('http://localhost:8000/api/tasks/task-abc123/cancel', {
  method: 'POST'
});
```

### cURL

```bash
# 获取任务列表
curl http://localhost:8000/api/tasks

# 获取任务统计
curl http://localhost:8000/api/tasks/stats

# 取消任务
curl -X POST http://localhost:8000/api/tasks/task-abc123/cancel

# 获取配置状态
curl http://localhost:8000/api/config/status
```

---

## 更新日志

### v0.2.0 (2026-01-11)

新增：
- 配置 API (`/api/config/*`)
- 增强 Dashboard UI
- CLI 命令支持
- 一键安装脚本

### v0.1.0 (2024-01-08)

初始版本

---

## 支持

如有问题，请访问 [GitHub Issues](https://github.com/your-org/kaka/issues)
