# Kaka

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![PyPI Version](https://img.shields.io/pypi/v/kaka-auto.svg)](https://pypi.org/project/kaka-auto/)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)

> 🚀 **一键安装，开箱即用** - 通过 GitHub Webhook 触发 Claude Code CLI 进行 AI 开发，实现从 Issue 到 PR 的完整自动化流程。

## 特性

- **智能 Webhook 接收** - 接收并验证 GitHub Webhook 事件
- **多种触发方式** - 支持标签触发（`ai-dev`）和评论触发（`/ai develop`）
- **AI 开发调度** - 自动调用本地 Claude Code CLI 进行开发任务
- **Git 自动化** - 自动创建分支、提交代码、推送到远程仓库
- **智能 PR 创建** - 根据开发内容自动生成 Pull Request
- **实时监控** - 美观的 Dashboard 界面，实时追踪任务状态
- **配置向导** - 5 分钟完成配置，无需复杂操作

## 快速开始

### 方式 1：pip 安装（推荐）

```bash
# 直接安装
pip install kaka-auto

# 或带开发依赖
pip install kaka-auto[dev]

# 配置服务
kaka configure

# 启动服务
kaka start
```

📦 **PyPI 页面**: https://pypi.org/project/kaka-auto/

### 方式 2：从源码安装（开发模式）

```bash
# 克隆项目
git clone https://github.com/wersling/kaka.git
cd kaka

# 运行初始化脚本（推荐）
# ✅ 自动创建 venv
# ✅ 自动安装所有依赖（开发工具 + 发布工具）
# ✅ 自动创建必要目录
# ✅ 引导配置环境
./dev_setup.sh

# 启动服务
kaka start
```

**或手动安装**：

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装（包含所有工具）
pip install -e ".[all]"

# 或只安装开发工具
pip install -e ".[dev]"

# 配置环境
kaka configure

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

## 文档

- [API 文档](docs/API.md) - 完整 API 参考
- [使用指南](docs/USAGE.md) - 使用说明和示例
- [开发指南](docs/DEVELOPMENT.md) - 开发者文档
- [架构文档](docs/ARCHITECTURE.md) - 系统架构设计
- [日志系统](docs/LOGGING.md) - 日志配置和使用

## 开发调试

项目已配置完整的 VSCode 调试环境：

1. 按 `F5` 启动调试
2. 支持断点调试、热重载
3. 多种调试模式可选

详见 [`.vscode/launch.json`](.vscode/launch.json)


## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

**⭐ 如果这个项目对您有帮助，请给我们一个 Star！**

**Made with ❤️ by AI Development Team**
