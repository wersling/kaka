# 变更日志

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，
项目遵循 [语义化版本](https://semver.org/spec/v2.0.0.html) 规范。

## [0.1.1] - 2025-01-12

### 修复
- 修复 `kaka configure` 命令在 pip 安装后不可用的问题
- 将 `setup_env.py` 移至 `app/` 包内，确保在 pip 安装后可用
- 更新 CLI 和 dev_setup.sh 脚本，支持从包内或项目根目录查找配置脚本
- 删除 `install.sh`，简化为单一安装方式（pip）
- 删除 `scripts/dev.sh`，统一使用 `kaka start` 命令启动服务
- 简化 `dev_setup.sh`，专注于开发环境初始化（从 263 行精简到 118 行）
- 将 `setup.sh` 重命名为 `dev_setup.sh`，名称更清晰地反映其用途
- 调整脚本颜色为莫兰迪深色系，提升视觉体验

### 变更
- 配置脚本现在可以通过 `kaka configure` 命令直接调用
- 改进了配置脚本的路径查找逻辑，兼容开发模式和安装模式
- 删除 `requirements.txt`，统一使用 `pyproject.toml` 管理依赖
- 清理 `scripts/` 目录，仅保留开发和测试脚本
- 统一服务启动方式为 `kaka start`，移除冗余的 `dev.sh` 脚本

## [0.1.0] - 2025-01-12

### 新增
- 初始发布到 PyPI，包名 `kaka-auto`
- GitHub Webhook 集成，支持触发 AI 开发
- Claude Code CLI 自动化支持
- 实时监控的 Dashboard UI
- CLI 工具（kaka）
- 配置向导，简化设置流程
- Git 自动化（创建分支、提交、推送）
- 自动创建 Pull Request
- 支持多种触发方式（标签和评论）
- 完整的日志和监控功能
- 使用 slowapi 实现速率限制
- 使用 SQLAlchemy ORM 的 SQLite 数据库
