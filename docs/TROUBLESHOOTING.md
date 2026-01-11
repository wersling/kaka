# 故障排查

本文档提供常见问题的解决方案。

## 目录

- [Webhook 问题](#webhook-问题)
- [Claude CLI 问题](#claude-cli-问题)
- [Git 操作问题](#git-操作问题)
- [端口问题](#端口问题)
- [依赖问题](#依赖问题)
- [调试技巧](#调试技巧)

---

## Webhook 问题

### 症状: Webhook 签名验证失败

**日志信息**:
```
ERROR: Webhook 签名验证失败
```

**解决方案**:

```bash
# 1. 检查 .env 中的 WEBHOOK_SECRET
grep GITHUB_WEBHOOK_SECRET .env

# 2. 重新生成密钥
python -c "import secrets; print(secrets.token_hex(32))"

# 3. 在 GitHub Webhook 设置中更新 Secret
# 访问: https://github.com/your-repo/settings/hooks
```

### 症状: Webhook 未接收

**可能原因**:
1. GitHub Webhook URL 配置错误
2. 防火墙阻止请求
3. 服务未启动

**排查步骤**:

```bash
# 1. 检查服务是否运行
curl http://localhost:8000/health

# 2. 检查端口是否监听
lsof -i :8000

# 3. 查看服务日志
tail -f logs/ai-scheduler.log
```

---

## Claude CLI 问题

### 症状: claude-code: command not found

**解决方案**:

```bash
# 1. 检查 Claude Code 是否已安装
which claude-code

# 2. 重新安装
npm install -g @anthropic/claude-code

# 3. 验证安装
claude-code --version
```

### 症状: Claude Code 超时

**日志信息**:
```
ERROR: Claude Code CLI 执行超时
```

**解决方案**:

在 `config/config.yaml` 中增加超时时间：

```yaml
claude:
  timeout: 3600  # 增加到 1 小时
```

---

## Git 操作问题

### 症状: Git command failed

**日志信息**:
```
ERROR: Git command failed
```

**解决方案**:

```bash
# 1. 检查仓库路径是否正确
ls -la $REPO_PATH

# 2. 检查 Git 远程仓库
cd $REPO_PATH
git remote -v

# 3. 确保 GitHub Token 有权限
curl -H "Authorization: token $GITHUB_TOKEN" \
     https://api.github.com/user/repos

# 4. 检查 Git 配置
git config --list
```

---

## 端口问题

### 症状: Address already in use

**日志信息**:
```
ERROR: [Errno 48] Address already in use
```

**解决方案**:

```bash
# 1. 查找占用端口的进程
lsof -i :8000

# 2. 终止进程
kill -9 <PID>

# 3. 或使用其他端口
uvicorn app.main:app --port 8001
```

---

## 依赖问题

### 症状: Could not find a version that satisfies

**解决方案**:

```bash
# 1. 升级 pip
pip install --upgrade pip

# 2. 清理缓存
pip cache purge

# 3. 重新安装依赖
pip install -r requirements.txt
```

### 症状: ModuleNotFoundError

**解决方案**:

```bash
# 1. 确保虚拟环境已激活
source venv/bin/activate

# 2. 重新安装依赖
pip install -r requirements.txt

# 3. 检查 Python 版本
python --version  # 需要 Python 3.11+
```

---

## 调试技巧

### 1. 启用调试模式

在 `config/config.yaml` 中设置：

```yaml
logging:
  level: "DEBUG"
```

### 2. 查看详细请求日志

```bash
# 使用 curl 测试 Webhook
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: labeled" \
  -d '{"action":"labeled","issue":{"number":123}}'
```

### 3. 使用 Python 调试器

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

### 4. 检查环境变量

```bash
# 查看所有环境变量
env | grep GITHUB

# 或在 Python 中
import os
print(os.environ.get('GITHUB_TOKEN'))
```

---

## 日志位置

| 日志类型 | 位置 | 说明 |
|---------|------|------|
| 应用日志 | `logs/ai-scheduler.log` | 主要应用日志 |
| 错误日志 | `logs/ai-scheduler.log` | 错误和异常信息 |
| Git 日志 | `logs/git.log` | Git 操作日志 |
| Claude 日志 | `logs/claude.log` | Claude CLI 调用日志 |

### 查看日志命令

```bash
# 实时查看日志
tail -f logs/ai-scheduler.log

# 查看最近 20 行
tail -n 20 logs/ai-scheduler.log

# 查看错误日志
grep ERROR logs/ai-scheduler.log

# 查看特定时间段的日志
grep "2024-01-08 10:" logs/ai-scheduler.log
```

---

## 获取帮助

如果以上方法都无法解决问题：

1. 查看 [完整文档](../README.md)
2. 搜索 [已有 Issues](https://github.com/wersling/kaka/issues)
3. 创建新的 Issue，包含：
   - 详细的错误描述
   - 完整的日志信息
   - 环境信息（操作系统、Python 版本等）

---

## 下一步

- [配置说明](CONFIGURATION.md) - 配置指南
- [安全建议](SECURITY.md) - 安全加固
