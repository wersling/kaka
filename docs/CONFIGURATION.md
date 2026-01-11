# 配置说明

本文档详细说明 Kaka AI Dev 的配置选项。

## 目录

- [环境变量](#环境变量)
- [config.yaml 配置](#configyaml-配置)
- [GitHub Webhook 配置](#github-webhook-配置)

---

## 环境变量

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

### 获取 GitHub Token

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token" → "Generate new token (classic)"
3. 选择以下权限：
   - `repo` (完整仓库访问权限)
   - `admin:org_hook` (管理 Webhook)
4. 点击生成并复制 Token

### 获取 Anthropic API Key

1. 访问 https://console.anthropic.com/
2. 登录或注册账户
3. 进入 API Keys 页面
4. 点击 "Create Key" 生成新密钥

---

## config.yaml 配置

配置文件位于 `config/config.yaml`，支持以下配置项：

### 服务器配置

```yaml
server:
  host: "0.0.0.0"      # 监听地址
  port: 8000           # 监听端口
  reload: false        # 生产环境设为 false
  workers: 1           # 工作进程数
```

### GitHub 配置

```yaml
github:
  webhook_secret: "${GITHUB_WEBHOOK_SECRET}"  # 从环境变量读取
  token: "${GITHUB_TOKEN}"
  repo_owner: "${GITHUB_REPO_OWNER}"
  repo_name: "${GITHUB_REPO_NAME}"
  trigger_label: "ai-dev"           # 触发标签
  trigger_command: "/ai develop"    # 触发命令
```

### Claude Code 配置

```yaml
claude:
  timeout: 1800          # 执行超时（秒），默认 30 分钟
  max_retries: 2         # 最大重试次数
  auto_test: true        # 是否自动运行测试
  cli_path: "claude-code"  # CLI 路径
  cwd: null              # 工作目录（可选）
```

### 日志配置

```yaml
logging:
  level: "INFO"                     # 日志级别
  file: "logs/ai-scheduler.log"     # 日志文件路径
  max_bytes: 10485760               # 文件大小限制（10MB）
  backup_count: 5                   # 保留的日志文件数
  console: true                     # 是否输出到控制台
  json: false                       # 是否使用 JSON 格式
```

### 安全配置

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

---

## GitHub Webhook 配置

### 创建 Webhook

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

### 生成 Webhook Secret

```bash
# 使用 openssl 生成随机密钥
openssl rand -hex 32

# 或使用 Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 验证 Webhook

在 Dashboard 中点击"复制 Webhook URL"后，使用以下命令测试：

```bash
WEBHOOK_SECRET="your-secret"
PAYLOAD='{"action":"labeled","issue":{"number":1,"title":"Test"}}'
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')

curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=$SIGNATURE" \
  -H "X-GitHub-Event: issues" \
  -d "$PAYLOAD"
```

---

## 配置向导

你也可以使用内置的配置向导来简化配置过程：

```bash
# 启动服务
kaka start

# 打开配置向导
kaka configure
```

然后在浏览器中访问 `http://localhost:8000/config`，配置向导会：

1. 验证所有配置字段
2. 实时显示验证结果
3. 自动生成 Webhook Secret
4. 一键保存配置

---

## 下一步

- [使用指南](USAGE.md) - 了解如何使用系统
- [部署指南](DEPLOYMENT.md) - 生产环境部署
