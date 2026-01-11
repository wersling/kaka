# 快速启动指南

5 分钟快速上手 Kaka AI Dev

---

## 📋 前置要求

- Python 3.11+
- Git
- GitHub 账号
- Claude Code CLI（需要单独安装和配置）

---

## 🚀 方式 1：一键安装（推荐）

```bash
# 运行安装脚本
bash scripts/install.sh

# 完成后，配置服务
kaka configure

# 启动服务
kaka start
```

---

## 🚀 方式 2：源码运行（开发者）

### 步骤 1：克隆项目

```bash
git clone https://github.com/your-org/kaka.git
cd kaka
```

### 步骤 2：创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 步骤 3：安装依赖

```bash
pip install -r requirements.txt
```

### 步骤 4：配置环境

编辑 `.env` 文件：

```bash
# GitHub 配置
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=your-repo
GITHUB_WEBHOOK_SECRET=your-secret

# 仓库配置
REPO_PATH=/path/to/your/repo
```

### 步骤 5：启动服务

```bash
# 方式 1：使用 Python
python -m app.main

# 方式 2：使用 CLI
kaka start
```

---

## 🎯 首次使用

### 1. 打开配置向导

服务启动后，访问：
```
http://localhost:8000/config
```

### 2. 填写配置

- **GitHub Token**: [获取地址](https://github.com/settings/tokens)
- **仓库所有者**: 你的 GitHub 用户名
- **仓库名称**: 仓库名称
- **本地仓库路径**: 仓库的绝对路径

### 3. 验证并保存

点击"验证并保存"，系统会自动验证所有配置。

---

## 📊 使用 Dashboard

访问 Dashboard：
```
http://localhost:8000/dashboard
```

### 快捷键

- **R** - 刷新页面
- **C** - 打开配置
- **W** - 复制 Webhook URL
- **?** - 显示帮助
- **ESC** - 关闭模态框

---

## 🔗 配置 GitHub Webhook

### 1. 复制 Webhook URL

在 Dashboard 点击"📋 复制 Webhook URL"

### 2. 在 GitHub 创建 Webhook

1. 进入仓库设置 → `Webhooks` → `Add webhook`
2. 配置：
   - **Payload URL**: 粘贴刚才复制的 URL
   - **Content type**: `application/json`
   - **Secret**: 与 `.env` 中的 `GITHUB_WEBHOOK_SECRET` 一致
   - **Events**: 选择 `Issues` 和 `Issue comments`

### 3. 保存并测试

点击"Add webhook"完成配置。

---

## 🎯 触发 AI 开发

### 方式 1：标签触发

在 GitHub Issue 中添加 `ai-dev` 标签

### 方式 2：评论触发

在 GitHub Issue 中评论 `/ai develop`

---

## 📝 常用命令

```bash
# 查看服务状态
kaka status

# 查看日志
kaka logs

# 导出配置
kaka config export

# 导入配置
kaka config import

# 启动开发服务器（自动重载）
kaka start --reload

# 查看帮助
kaka --help
```

---

## 🐛 故障排查

### 服务无法启动

```bash
# 检查端口占用
lsof -i :8000

# 查看日志
kaka logs
tail -f logs/ai-scheduler.log
```

### 配置验证失败

```bash
# 检查 .env 文件
cat .env

# 重新配置
kaka configure
```

### Webhook 不工作

1. 检查 Webhook Secret 是否一致
2. 查看 GitHub Webhook 交付记录
3. 检查服务日志

---

## 📚 更多文档

- [完整文档](README.md)
- [API 文档](API.md)
- [MVP 方案](docs/mvp-refactor-plan.md)

---

## 💡 提示

- 首次使用建议先运行 `kaka configure`
- 定期运行 `kaka status` 检查服务状态
- 使用 `kaka logs` 查看详细日志
- 保存配置前请确保所有字段都验证通过

---

**开始使用 AI 自动化开发吧！** 🎉
