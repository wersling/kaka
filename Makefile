.PHONY: help install dev webhook-test test lint format clean coverage docker-build docker-run init test-webhook-live trigger test-webhook-status test-webhook-batch

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

## 🌐 启动 Webhook 测试环境（ngrok）
webhook-test: ## 启动本地 Webhook 测试环境（需要 ngrok）
	@echo "$(BLUE)🌐 启动 Webhook 测试环境...$(NC)"
	@if ! command -v ngrok > /dev/null 2>&1; then \
		echo "$(YELLOW)❌ ngrok 未安装$(NC)"; \
		echo "$(YELLOW)   macOS: brew install ngrok$(NC)"; \
		echo "$(YELLOW)   Linux: 访问 https://ngrok.com/download$(NC)"; \
		exit 1; \
	fi
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)❌ .env 文件不存在$(NC)"; \
		echo "$(YELLOW)   请先运行: cp .env.example .env$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)📡 启动 FastAPI 服务（后台）...$(NC)"
	@./scripts/dev.sh & \
	SERVER_PID=$$!; \
	sleep 3; \
	echo "$(GREEN)🌐 启动 ngrok 隧道...$(NC)"; \
	ngrok http 8000 & \
	NGROK_PID=$$!; \
	trap "kill $$SERVER_PID $$NGROK_PID 2>/dev/null; echo ''; echo '$(YELLOW)🛑 服务已停止$(NC)'; exit 0" INT; \
	wait

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

# 性能测试目标
.PHONY: test-performance test-benchmark test-stress test-concurrency

# 运行所有性能测试
test-performance:
	@echo "运行完整性能测试套件..."
	python -m pytest tests/test_performance.py -v --tb=short --benchmark-skip

# 运行性能基准测试
test-benchmark:
	@echo "运行性能基准测试..."
	python -m pytest tests/test_performance.py::TestPerformanceBaselines \
		-v \
		--benchmark-only \
		--benchmark-columns=min,max,mean,stddev,median,ops,iqr \
		--benchmark-sort=name

# 运行并发测试
test-concurrency:
	@echo "运行并发性能测试..."
	python -m pytest tests/test_performance.py::TestConcurrencyPerformance \
		-v -s --tb=short --benchmark-skip

# 运行压力测试
test-stress:
	@echo "运行压力测试..."
	python -m pytest tests/test_performance.py::TestStressTesting \
		-v -s --tb=short --benchmark-skip

# 生成性能报告
perf-report:
	@echo "生成性能测试报告..."
	python -m pytest tests/test_performance.py::TestPerformanceBaselines \
		--benchmark-only \
		--benchmark-autosave \
		--benchmark-save=data/baseline \
		--benchmark-json=reports/benchmark_results.json
	@echo "✓ 基准数据已保存到 reports/benchmark_results.json"

# 性能回归检测
perf-check:
	@echo "检测性能回归..."
	python -m pytest tests/test_performance.py::TestPerformanceBaselines \
		--benchmark-only \
		--benchmark-compare-fail=mean:5% \
		--benchmark-save=data/baseline \
		|| echo "⚠️  检测到性能退化！"

# 快速性能检查（仅关键指标）
perf-quick:
	@echo "快速性能检查..."
	python -m pytest tests/test_performance.py \
		-k "signature_verification or webhook_event_routing or concurrent_webhook" \
		-v --tb=line --benchmark-skip

# 内存泄漏检测
perf-memory:
	@echo "检测内存泄漏..."
	python -m pytest tests/test_performance.py::TestStressTesting::test_memory_leak_detection \
		-v -s --benchmark-skip

# 真实环境 Webhook 测试
.PHONY: test-webhook-live

# GitHub 仓库配置
GITHUB_OWNER ?= wersling
GITHUB_REPO ?= kaka_test
ISSUE_NUMBER ?= 38
TEST_LABEL ?= ai-dev

# 触发 Webhook（通过重新添加标签）
test-webhook-live: ## 触发真实环境的 Webhook 测试（对 GitHub Issue 添加/删除 ai-dev 标签）
	@echo "$(BLUE)🚀 触发真实环境 Webhook 测试...$(NC)"
	@echo "$(BLUE)📋 目标: $(GITHUB_OWNER)/$(GITHUB_REPO)#$(ISSUE_NUMBER)$(NC)"
	@echo ""
	@if ! command -v gh > /dev/null 2>&1; then \
		echo "$(YELLOW)❌ GitHub CLI 未安装$(NC)"; \
		echo "$(YELLOW)   macOS: brew install gh$(NC)"; \
		echo "$(YELLOW)   Linux: https://github.com/cli/cli$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)🔍 检查认证状态...$(NC)"
	@gh auth status > /dev/null 2>&1 || { \
		echo "$(YELLOW)❌ GitHub CLI 未认证$(NC)"; \
		echo "$(YELLOW)   请运行: gh auth login$(NC)"; \
		exit 1; \
	}
	@echo "$(GREEN)✅ GitHub CLI 已认证$(NC)"
	@echo ""
	@echo "$(BLUE)🏷️  处理标签 '$(TEST_LABEL)'...$(NC)"
	@echo "$(YELLOW)   删除旧标签（如果存在）...$(NC)"
	@GH_TOKEN=$$(grep "^GITHUB_TOKEN=" .env 2>/dev/null | cut -d'=' -f2-) \
		gh issue edit $(ISSUE_NUMBER) \
		--repo $(GITHUB_OWNER)/$(GITHUB_REPO) \
		--remove-label $(TEST_LABEL) 2>/dev/null || echo "     标签不存在，跳过删除"
	@sleep 1
	@echo "$(GREEN)   ✅ 添加标签 '$(TEST_LABEL)'...$(NC)"
	@GH_TOKEN=$$(grep "^GITHUB_TOKEN=" .env 2>/dev/null | cut -d'=' -f2-) \
		gh issue edit $(ISSUE_NUMBER) \
		--repo $(GITHUB_OWNER)/$(GITHUB_REPO) \
		--add-label $(TEST_LABEL)
	@echo ""
	@echo "$(GREEN)✅ Webhook 触发成功！$(NC)"
	@echo "$(BLUE)📊 查看 Issue:$(NC)"
	@echo "   https://github.com/$(GITHUB_OWNER)/$(GITHUB_REPO)/issues/$(ISSUE_NUMBER)"
	@echo ""
	@echo "$(BLUE)💡 提示:$(NC)"
	@echo "   使用 'make logs' 或 'make logs-recent' 查看服务日志"
	@echo "   使用 'make logs-error' 查看错误日志"

# 快速触发 Webhook（别名）
trigger: test-webhook-live ## 触发 Webhook 的快捷命令

# 使用 curl 直接调用 GitHub API（备用方案）
trigger-api: ## 使用 curl 直接调用 GitHub API 添加标签（需要 .env 中的 GITHUB_TOKEN 有足够权限）
	@echo "$(BLUE)🚀 通过 API 触发 Webhook...$(NC)"
	@echo "$(BLUE)📋 目标: $(GITHUB_OWNER)/$(GITHUB_REPO)#$(ISSUE_NUMBER)$(NC)"
	@echo ""
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)❌ .env 文件不存在$(NC)"; \
		exit 1; \
	fi
	@GITHUB_TOKEN=$$(grep "^GITHUB_TOKEN=" .env | cut -d'=' -f2-); \
	if [ -z "$$GITHUB_TOKEN" ]; then \
		echo "$(YELLOW)❌ GITHUB_TOKEN 未设置$(NC)"; \
		exit 1; \
	fi; \
	echo "$(BLUE)🏷️  处理标签 '$(TEST_LABEL)'...$(NC)"; \
	echo "$(YELLOW)   获取当前标签...$(NC)"; \
	LABELS=$$(curl -s -H "Authorization: token $$GITHUB_TOKEN" \
		-H "Accept: application/vnd.github.v3+json" \
		"https://api.github.com/repos/$(GITHUB_OWNER)/$(GITHUB_REPO)/issues/$(ISSUE_NUMBER)" \
		| jq -r '.labels | map(.name) | join(",")'); \
	echo "     当前标签: $$LABELS"; \
	echo "$(YELLOW)   删除旧标签（如果存在）...$(NC)"; \
	curl -s -X DELETE \
		-H "Authorization: token $$GITHUB_TOKEN" \
		-H "Accept: application/vnd.github.v3+json" \
		"https://api.github.com/repos/$(GITHUB_OWNER)/$(GITHUB_REPO)/issues/$(ISSUE_NUMBER)/labels/$(TEST_LABEL)" \
		> /dev/null 2>&1 || echo "     标签不存在，跳过删除"; \
	sleep 1; \
	echo "$(GREEN)   ✅ 添加标签 '$(TEST_LABEL)'...$(NC)"; \
	curl -s -X POST \
		-H "Authorization: token $$GITHUB_TOKEN" \
		-H "Accept: application/vnd.github.v3+json" \
		"https://api.github.com/repos/$(GITHUB_OWNER)/$(GITHUB_REPO)/issues/$(ISSUE_NUMBER)/labels" \
		-d '{"labels":["$(TEST_LABEL)"]}' \
		| jq -r '.[] | "     添加成功: " + .name'; \
	echo ""; \
	echo "$(GREEN)✅ Webhook 触发成功！$(NC)"; \
	echo "$(BLUE)📊 查看 Issue:$(NC)"; \
	echo "   https://github.com/$(GITHUB_OWNER)/$(GITHUB_REPO)/issues/$(ISSUE_NUMBER)"

# 查看测试 Issue 状态
test-webhook-status: ## 查看测试 Issue 的标签状态
	@echo "$(BLUE)📋 Issue #$(ISSUE_NUMBER) 标签状态:$(NC)"
	@gh issue view $(ISSUE_NUMBER) \
		--repo $(GITHUB_OWNER)/$(GITHUB_REPO) \
		--json title,labels,state,url \
		--jq '"标题: " + .title + "\n状态: " + .state + "\n标签: " + ([.labels[].name] | join(", ")) + "\n链接: " + .url'

# 批量触发 Webhook（多次测试）
test-webhook-batch: ## 批量触发 Webhook（使用: make test-webhook-batch COUNT=3）
	@echo "$(BLUE)🔄 批量触发 Webhook ($(COUNT) 次)...$(NC)"
	@for i in $$(seq 1 $(COUNT)); do \
		echo "$(BLUE)第 $$i 次触发...$(NC)"; \
		$(MAKE) test-webhook-live; \
		if [ $$i -lt $(COUNT) ]; then \
			echo "$(YELLOW)⏳ 等待 3 秒...$(NC)"; \
			sleep 3; \
		fi; \
	done
	@echo "$(GREEN)✅ 批量触发完成！$(NC)"
