.PHONY: help install dev test lint format clean coverage docker-build docker-run init

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
GREEN  := \033[0;32m
YELLOW := \033[1;33m
BLUE   := \033[0;34m
NC     := \033[0m # No Color

## 🎯 帮助信息
help: ## 显示帮助信息
	@echo "$(BLUE)AI 开发调度服务 - 常用命令$(NC)"
	@echo ""
	@echo "$(GREEN)开发命令:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)示例:$(NC)"
	@echo "  make install       # 安装依赖"
	@echo "  make dev           # 启动开发服务器"
	@echo "  make test          # 运行测试"
	@echo "  make coverage      # 查看测试覆盖率"

## 📦 项目初始化
init: ## 初始化项目（创建虚拟环境、安装依赖）
	@echo "$(BLUE)🚀 初始化项目...$(NC)"
	@./scripts/setup.sh

## 📥 安装依赖
install: ## 安装项目依赖
	@echo "$(BLUE)📦 安装依赖...$(NC)"
	@pip install -r requirements.txt

## 🔄 更新依赖
update: ## 更新依赖到最新版本
	@echo "$(BLUE)⬆️  更新依赖...$(NC)"
	@pip install --upgrade -r requirements.txt

## 🚀 启动开发服务器
dev: ## 启动开发服务器
	@echo "$(BLUE)🚀 启动开发服务器...$(NC)"
	@./scripts/dev.sh

## 🧪 运行测试
test: ## 运行所有测试
	@echo "$(BLUE)🧪 运行测试...$(NC)"
	@python -m pytest tests/ -v

## 🎯 快速测试（跳过慢速测试）
test-fast: ## 快速运行测试（跳过慢速测试）
	@echo "$(BLUE)⚡ 快速测试...$(NC)"
	@python -m pytest tests/ -v -m "not slow"

## 🔍 运行特定测试
test-one: ## 运行特定测试文件（使用: make test-one FILE=tests/test_validators.py）
	@echo "$(BLUE)🔍 运行测试: $(FILE)$(NC)"
	@python -m pytest $(FILE) -v

## 📊 测试覆盖率
coverage: ## 生成测试覆盖率报告
	@echo "$(BLUE)📊 生成覆盖率报告...$(NC)"
	@python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "$(GREEN)✅ 覆盖率报告已生成: htmlcov/index.html$(NC)"

## 📈 查看覆盖率（浏览器）
coverage-open: coverage ## 生成并在浏览器中打开覆盖率报告
	@open htmlcov/index.html 2>/dev/null || python -m webbrowser htmlcov/index.html

## 🔍 代码检查
lint: ## 运行代码检查（flake8）
	@echo "$(BLUE)🔍 运行代码检查...$(NC)"
	@flake8 app/ tests/ --max-line-length=100 --extend-ignore=E203,W503

## 🎨 代码格式化
format: ## 格式化代码（black）
	@echo "$(BLUE)🎨 格式化代码...$(NC)"
	@black app/ tests/ --line-length=100

## ✅ 代码检查并格式化
check: lint format ## 运行所有代码质量检查
	@echo "$(GREEN)✅ 代码质量检查完成！$(NC)"

## 🧹 清理临时文件
clean: ## 清理临时文件和缓存
	@echo "$(BLUE)🧹 清理临时文件...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .coverage 2>/dev/null || true
	@rm -rf logs/*.log 2>/dev/null || true
	@echo "$(GREEN)✅ 清理完成！$(NC)"

## 🗑️ 完全清理（包括虚拟环境）
clean-all: clean ## 完全清理项目（包括虚拟环境）
	@echo "$(BLUE)🗑️  完全清理项目...$(NC)"
	@rm -rf venv/ 2>/dev/null || true
	@echo "$(YELLOW)⚠️  虚拟环境已删除，请运行 'make init' 重新初始化$(NC)"

## 🐳 Docker 构建
docker-build: ## 构建 Docker 镜像
	@echo "$(BLUE)🐳 构建 Docker 镜像...$(NC)"
	@docker build -t ai-dev-scheduler:latest .

## 🐳 Docker 运行
docker-run: ## 运行 Docker 容器
	@echo "$(BLUE)🐳 运行 Docker 容器...$(NC)"
	@docker run -d --name ai-dev-scheduler -p 8000:8000 \
		--env-file .env ai-dev-scheduler:latest

## 🐳 Docker 停止
docker-stop: ## 停止 Docker 容器
	@echo "$(BLUE)🛑 停止 Docker 容器...$(NC)"
	@docker stop ai-dev-scheduler 2>/dev/null || true
	@docker rm ai-dev-scheduler 2>/dev/null || true

## 🐳 Docker 清理
docker-clean: ## 清理 Docker 镜像和容器
	@echo "$(BLUE)🧹 清理 Docker 资源...$(NC)"
	@docker stop ai-dev-scheduler 2>/dev/null || true
	@docker rm ai-dev-scheduler 2>/dev/null || true
	@docker rmi ai-dev-scheduler:latest 2>/dev/null || true
	@echo "$(GREEN)✅ Docker 清理完成！$(NC)"

## 📋 查看日志
logs: ## 查看应用日志
	@echo "$(BLUE)📋 查看日志...$(NC)"
	@tail -f logs/ai-scheduler.log 2>/dev/null || echo "$(YELLOW)⚠️  日志文件不存在$(NC)"

## 📊 查看最近日志
logs-recent: ## 查看最近50行日志
	@echo "$(BLUE)📋 查看最近日志...$(NC)"
	@tail -n 50 logs/ai-scheduler.log 2>/dev/null || echo "$(YELLOW)⚠️  日志文件不存在$(NC)"

## 🔍 查看错误日志
logs-error: ## 查看错误日志
	@echo "$(BLUE)🔍 查看错误日志...$(NC)"
	@grep -i error logs/ai-scheduler.log 2>/dev/null || echo "$(YELLOW)⚠️  未发现错误日志$(NC)"

## 📝 查看环境变量
env: ## 显示环境变量配置
	@echo "$(BLUE)📝 环境变量配置:$(NC)"
	@if [ -f .env ]; then \
		grep -v "^#" .env | grep -v "^$$"; \
	else \
		echo "$(YELLOW)⚠️  .env 文件不存在，请运行 'make init' 创建$(NC)"; \
	fi

## 🔐 验证配置
validate: ## 验证配置文件
	@echo "$(BLUE)🔍 验证配置...$(NC)"
	@python -c "from app.config import load_config; load_config()" && \
		echo "$(GREEN)✅ 配置文件有效！$(NC)" || \
		echo "$(YELLOW)⚠️  配置文件有问题，请检查$(NC)"

## 🧪 运行集成测试
test-integration: ## 运行集成测试
	@echo "$(BLUE)🧪 运行集成测试...$(NC)"
	@python -m pytest tests/test_integration.py -v

## 🧪 运行单元测试
test-unit: ## 运行单元测试
	@echo "$(BLUE)🧪 运行单元测试...$(NC)"
	@python -m pytest tests/test_*.py -v --ignore=tests/test_integration.py

## 📊 测试报告
report: coverage ## 生成完整的测试报告
	@echo "$(BLUE)📊 生成测试报告...$(NC)"
	@python -m pytest tests/ --cov=app --cov-report=html --cov-report=term --cov-report=xml
	@echo "$(GREEN)✅ 测试报告已生成：$(NC)"
	@echo "  - HTML: htmlcov/index.html"
	@echo "  - XML: coverage.xml"

## 🚀 快速开始（安装+验证）
quickstart: install validate test-fast ## 快速开始：安装依赖、验证配置、运行快速测试
	@echo "$(GREEN)✅ 快速开始完成！运行 'make dev' 启动开发服务器$(NC)"

## 📚 项目信息
info: ## 显示项目信息
	@echo "$(BLUE)📚 项目信息:$(NC)"
	@echo "  项目名称: AI 开发调度服务"
	@echo "  版本: 0.1.0"
	@echo "  Python: $(shell python3 --version)"
	@echo "  工作目录: $(shell pwd)"
	@echo ""
	@echo "$(BLUE)📊 代码统计:$(NC)"
	@echo "  Python 文件: $(shell find app -name "*.py" | wc -l | xargs)"
	@echo "  测试文件: $(shell find tests -name "test_*.py" | wc -l | xargs)"
	@echo "  测试用例: $(shell python -m pytest tests/ --collect-only -q 2>/dev/null | tail -1 | awk '{print $$1}')"

## 🔄 重置项目
reset: clean-all init ## 重置项目（完全清理+重新初始化）
	@echo "$(GREEN)✅ 项目已重置！$(NC)"

## 📖 文档
docs: ## 在浏览器中打开文档
	@echo "$(BLUE)📖 打开文档...$(NC)"
	@open README.md 2>/dev/null || python -m webbrowser README.md
