# 并发控制功能说明

## 功能概述

AI 开发调度服务现已支持并发控制功能，通过信号量（Semaphore）机制限制同时执行的任务数量，避免资源竞争和过载。

## 配置

### 1. 配置文件

在 `config/config.yaml` 中配置最大并发数：

```yaml
task:
  max_concurrent: 1  # 最大并发任务数，默认为 1
```

### 2. 环境变量

也可以通过环境变量设置：

```bash
export TASK_MAX_CONCURRENT=2
```

## 工作原理

### 并发管理器（ConcurrencyManager）

- **单例模式**：全局唯一的并发管理器实例
- **信号量机制**：使用 `asyncio.Semaphore` 实现并发控制
- **自动管理**：通过异步上下文管理器自动获取和释放许可

### 执行流程

1. **初始化**：服务启动时根据配置创建信号量
2. **获取许可**：任务开始前自动获取许可（如果已满则等待）
3. **执行任务**：许可获取成功后执行任务
4. **释放许可**：任务完成后自动释放许可

### 示例

假设 `max_concurrent=2`：

```
时间线：
0.0s - 任务1 获取许可 ✅ (1/2)
0.1s - 任务2 获取许可 ✅ (2/2)  # 已满
0.2s - 任务3 尝试获取许可 ⏳ 等待...
0.5s - 任务1 完成，释放许可 🔓 (1/2)
0.5s - 任务3 获取许可 ✅ (2/2)
1.0s - 任务2 完成，释放许可 🔓 (1/1)
1.0s - 任务3 完成，释放许可 🔓 (0/2)
```

## API 端点

### 获取并发状态

**端点**：`GET /api/concurrency/stats`

**响应示例**：

```json
{
  "max_concurrent": 2,
  "current_running": 1,
  "available": 1
}
```

**字段说明**：
- `max_concurrent`：最大并发数
- `current_running`：当前运行中的任务数
- `available`：可用的并发许可数

### 使用示例

```bash
# 获取并发状态
curl http://localhost:8000/api/concurrency/stats

# 响应
{
  "max_concurrent": 2,
  "current_running": 0,
  "available": 2
}
```

## 日志输出

并发控制会在日志中输出关键信息：

```
# 获取许可
[DEBUG] 🔓 获取并发许可 (当前运行: 1/2)

# 释放许可
[DEBUG] 🔒 释放并发许可 (当前运行: 0/2)

# Webhook 处理
[INFO] 🔓 获取并发锁，开始处理 Issue #10
```

## 性能考虑

### 推荐配置

- **开发环境**：`max_concurrent: 1`（避免资源冲突）
- **生产环境**：`max_concurrent: 2-3`（根据机器性能调整）

### 影响因素

1. **CPU 密集型任务**：Claude CLI 执行主要消耗 CPU，建议 `max_concurrent <= CPU 核心数`
2. **内存使用**：每个任务会启动独立的 Claude CLI 进程，需考虑内存限制
3. **GitHub API 限流**：并发过多可能导致 API 限流
4. **Git 操作**：多个任务同时操作同一仓库可能产生冲突

## 测试

运行并发控制测试：

```bash
python scripts/test_concurrency.py
```

测试内容：
- ✅ 并发管理器初始化
- ✅ 许可获取和释放
- ✅ 并发限制（超过限制时自动等待）
- ✅ 上下文管理器
- ✅ 便捷函数
- ✅ 多 Webhook 并发模拟

## 实现细节

### 核心文件

1. **`app/utils/concurrency.py`**：并发管理器实现
2. **`app/main.py`**：并发管理器初始化
3. **`app/services/webhook_handler.py`**：集成并发控制
4. **`app/api/tasks.py`**：并发状态 API 端点

### 代码示例

在 Webhook 处理中使用并发控制：

```python
from app.utils.concurrency import ConcurrencyManager

async def _handle_issue_event(self, data: dict[str, Any]) -> Optional[TaskResult]:
    # ... 验证触发条件 ...

    # 使用并发控制
    async with ConcurrencyManager():
        self.logger.info(f"🔓 获取并发锁，开始处理 Issue #{issue.number}")
        return await self._trigger_ai_development(...)

    # 退出上下文时自动释放许可
```

## 故障排查

### 问题 1：任务一直处于等待状态

**症状**：多个任务同时触发，但只有一个在执行

**原因**：`max_concurrent=1`，其他任务在等待许可

**解决**：
1. 检查并发状态：`curl http://localhost:8000/api/concurrency/stats`
2. 等待当前任务完成
3. 或增加 `max_concurrent` 配置值

### 问题 2：RuntimeError: is bound to a different event loop

**症状**：在测试脚本中遇到事件循环绑定错误

**原因**：信号量绑定到旧的事件循环

**解决**：在新的 `asyncio.run()` 调用前重置并发管理器：

```python
ConcurrencyManager._semaphore = None
ConcurrencyManager._instance = None
```

### 问题 3：并发统计不准确

**症状**：API 返回的 `current_running` 与实际不符

**原因**：异常退出导致未正确释放许可

**解决**：
1. 检查日志中是否有异常退出
2. 确保使用 `async with ConcurrencyManager()` 自动管理许可
3. 重启服务重置状态

## 最佳实践

### 1. 使用上下文管理器

推荐使用 `async with` 语法自动管理许可：

```python
# ✅ 推荐
async with ConcurrencyManager():
    await do_task()

# ❌ 不推荐（可能忘记释放）
await ConcurrencyManager.acquire()
try:
    await do_task()
finally:
    ConcurrencyManager.release()
```

### 2. 合理设置并发数

根据实际情况调整 `max_concurrent`：

```python
# 单机开发
max_concurrent: 1

# 高性能服务器
max_concurrent: 3

# 多服务器部署（每台服务器独立计数）
max_concurrent: 2
```

### 3. 监控并发状态

定期检查并发状态，观察系统负载：

```bash
# 实时监控
watch -n 1 'curl -s http://localhost:8000/api/concurrency/stats'
```

### 4. 日志级别调整

生产环境建议将并发日志级别设为 DEBUG：

```yaml
logging:
  level: INFO  # 并发日志为 DEBUG 级别，不会显示
```

## 未来改进

- [ ] 支持动态调整 `max_concurrent`（无需重启）
- [ ] 添加任务优先级队列
- [ ] 支持按任务类型设置不同的并发限制
- [ ] 分布式并发控制（多服务器共享计数）
- [ ] 并发统计历史记录和图表

## 相关文档

- [配置说明](../config/README.md)
- [API 文档](../api/README.md)
- [监控指南](../monitoring/README.md)
