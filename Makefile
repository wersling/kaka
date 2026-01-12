.PHONY: help test lint format clean coverage \
	test-integration-live test-webhook-live trigger test-webhook-status \
	trigger-api test-webhook-batch

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
GREEN  := \033[0;32m
YELLOW := \033[1;33m
BLUE   := \033[0;34m
NC     := \033[0m # No Color

# GitHub 仓库配置（用于 Webhook 测试）
GITHUB_OWNER ?= your-username
GITHUB_REPO ?= your-repo
ISSUE_NUMBER ?= 1
TEST_LABEL ?= ai-dev

## 🎯 帮助信息
help: ## 显示帮助信息
	@echo "$(BLUE)Kaka AI Dev - 开发者命令$(NC)"
	@echo ""
	@echo "$(GREEN)📝 用户命令 (使用 kaka CLI):$(NC)"
	@echo "  kaka start      启动服务"
	@echo "  kaka configure  配置向导"
	@echo "  kaka status     查看状态"
	@echo "  kaka logs       查看日志"
	@echo ""
	@echo "$(GREEN)🧪 测试命令:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)📚 示例:$(NC)"
	@echo "  make test              # 运行所有测试"
	@echo "  make coverage          # 查看测试覆盖率"
	@echo "  make lint              # 代码检查"
	@echo "  make format            # 代码格式化"
	@echo "  make trigger           # 触发 Webhook 测试"

## 🧪 运行测试
test: ## 运行所有测试
	@echo "$(BLUE)🧪 运行测试...$(NC)"
	@python -m pytest tests/ -v

## ⚡ 快速测试（跳过慢速测试）
test-fast: ## 快速运行测试（跳过慢速测试）
	@echo "$(BLUE)⚡ 快速测试...$(NC)"
	@python -m pytest tests/ -v -m "not slow"

## 🔍 运行特定测试文件
test-one: ## 运行特定测试文件（使用: make test-one FILE=tests/test_validators.py）
	@echo "$(BLUE)🔍 运行测试: $(FILE)$(NC)"
	@python -m pytest $(FILE) -v

## 🧪 运行单元测试
test-unit: ## 运行单元测试
	@echo "$(BLUE)🧪 运行单元测试...$(NC)"
	@python -m pytest tests/test_*.py -v --ignore=tests/test_integration.py

## 🧪 运行集成测试
test-integration: ## 运行集成测试
	@echo "$(BLUE)🧪 运行集成测试...$(NC)"
	@python -m pytest tests/test_integration.py -v

## 🧪 真实环境集成测试
test-integration-live: ## 运行真实环境集成测试
	@echo "$(BLUE)🧪 运行真实环境集成测试...$(NC)"
	@$(MAKE) clean
	@python scripts/test_integration_live.py --start-service --stop-service

## 📊 测试覆盖率
coverage: ## 生成测试覆盖率报告
	@echo "$(BLUE)📊 生成覆盖率报告...$(NC)"
	@python -m pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "$(GREEN)✅ 覆盖率报告已生成: htmlcov/index.html$(NC)"

## 📈 查看覆盖率（浏览器）
coverage-open: coverage ## 生成并在浏览器中打开覆盖率报告
	@open htmlcov/index.html 2>/dev/null || true

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
	@echo "$(YELLOW)⚠️  虚拟环境已删除，请运行 'pip install -e .' 重新安装$(NC)"

## 🐳 Docker 构建
docker-build: ## 构建 Docker 镜像
	@echo "$(BLUE)🐳 构建 Docker 镜像...$(NC)"
	@docker build -t kaka:latest .

## 🐳 Docker 运行
docker-run: ## 运行 Docker 容器
	@echo "$(BLUE)🐳 运行 Docker 容器...$(NC)"
	@docker run -d --name kaka -p 8000:8000 \
		--env-file .env kaka:latest

## 🐳 Docker 停止
docker-stop: ## 停止 Docker 容器
	@echo "$(BLUE)🛑 停止 Docker 容器...$(NC)"
	@docker stop kaka 2>/dev/null || true
	@docker rm kaka 2>/dev/null || true

## 🐳 Docker 清理
docker-clean: ## 清理 Docker 镜像和容器
	@echo "$(BLUE)🧹 清理 Docker 资源...$(NC)"
	@docker stop kaka 2>/dev/null || true
	@docker rm kaka 2>/dev/null || true
	@docker rmi kaka:latest 2>/dev/null || true
	@echo "$(GREEN)✅ Docker 清理完成！$(NC)"

# ===== Webhook 测试 =====

## 🚀 触发真实环境 Webhook 测试
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
	@echo "   使用 'kaka logs' 查看服务日志"

## 🎯 触发 Webhook（快捷命令）
trigger: test-webhook-live ## 触发 Webhook 的快捷命令

## 🌐 使用 curl 直接调用 GitHub API
trigger-api: ## 使用 curl 直接调用 GitHub API 添加标签
	@echo "$(BLUE)🚀 通过 API 触发 Webhook...$(NC)"
	@echo "$(BLUE)📋 目标: $(GITHUB_OWNER)/$(GITHUB_REPO)#$(ISSUE_NUMBER)$(NC)"
	@echo ""
	@GITHUB_TOKEN=$$(grep "^GITHUB_TOKEN=" .env 2>/dev/null | cut -d'=' -f2-); \
	if [ -z "$$GITHUB_TOKEN" ]; then \
		echo "$(YELLOW)❌ GITHUB_TOKEN 未设置$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)🏷️  添加标签 '$(TEST_LABEL)'...$(NC)"
	@curl -s -X POST \
		-H "Authorization: token $$GITHUB_TOKEN" \
		-H "Accept: application/vnd.github.v3+json" \
		"https://api.github.com/repos/$(GITHUB_OWNER)/$(GITHUB_REPO)/issues/$(ISSUE_NUMBER)/labels" \
		-d '{"labels":["$(TEST_LABEL)"]}'
	@echo ""
	@echo "$(GREEN)✅ Webhook 触发成功！$(NC)"

## 📋 查看 Webhook 测试 Issue 状态
test-webhook-status: ## 查看测试 Issue 的标签状态
	@echo "$(BLUE)📋 Issue #$(ISSUE_NUMBER) 标签状态:$(NC)"
	@gh issue view $(ISSUE_NUMBER) \
		--repo $(GITHUB_OWNER)/$(GITHUB_REPO) \
		--json title,labels,state,url \
		--jq '"标题: " + .title + "\n状态: " + .state + "\n标签: " + ([.labels[].name] | join(", ")) + "\n链接: " + .url'

## 🔄 批量触发 Webhook
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
