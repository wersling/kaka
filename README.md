# Kaka AI Dev

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

> 🚀 **一键安装，开箱即用** - 通过 GitHub Webhook 触发 Claude Code CLI 进行 AI 开发，实现从 Issue 到 PR 的完整自动化流程。

## ✨ 特性

- **智能 Webhook 接收** - 接收并验证 GitHub Webhook 事件
- **多种触发方式** - 支持标签触发（`ai-dev`）和评论触发（`/ai develop`）
- **AI 开发调度** - 自动调用本地 Claude Code CLI 进行开发任务
- **Git 自动化** - 自动创建分支、提交代码、推送到远程仓库
- **智能 PR 创建** - 根据开发内容自动生成 Pull Request
- **实时监控** - 美观的 Dashboard 界面，实时追踪任务状态
- **配置向导** - 5 分钟完成配置，无需复杂操作

## 🚀 快速开始

### 方式 1：一键安装（推荐）

```bash
# 运行安装脚本
bash scripts/install.sh

# 配置服务
kaka configure

# 启动服务
kaka start
```

### 方式 2：源码运行

```bash
# 克隆项目
git clone https://github.com/wersling/kaka.git
cd kaka

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -e .

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件填入配置

# 启动服务
kaka start
```

### 配置 GitHub Webhook

1. 访问 Dashboard：`http://localhost:8000/dashboard`
2. 点击"📋 复制 Webhook URL"
3. 在 GitHub 仓库设置中创建 Webhook：
   - **Payload URL**: 粘贴复制的 URL
   - **Content type**: `application/json`
   - **Secret**: 与 `.env` 中的 `GITHUB_WEBHOOK_SECRET` 一致
   - **Events**: 选择 `Issues` 和 `Issue comments`

### 触发 AI 开发

**方式 1**：在 GitHub Issue 中添加 `ai-dev` 标签

**方式 2**：在 GitHub Issue 中评论 `/ai develop`

## 📚 文档

- [快速启动指南](QUICKSTART.md) - 5 分钟上手教程
- [API 文档](API.md) - 完整 API 参考
- [配置说明](docs/CONFIGURATION.md) - 详细配置指南
- [使用指南](docs/USAGE.md) - 使用说明和示例
- [开发指南](docs/DEVELOPMENT.md) - 开发者文档
- [部署指南](docs/DEPLOYMENT.md) - 生产环境部署
- [故障排查](docs/TROUBLESHOOTING.md) - 常见问题解决


## 📝 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

**⭐ 如果这个项目对您有帮助，请给我们一个 Star！**

**Made with ❤️ by AI Development Team**
