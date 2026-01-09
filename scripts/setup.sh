#!/bin/bash
# AI 开发调度服务 - 初始化脚本

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 AI 开发调度服务 - 初始化${NC}"
echo "======================================"
echo ""

# 检查 Python 版本
echo "📋 检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 未找到 Python 3${NC}"
    echo "请先安装 Python 3.11 或更高版本"
    exit 1
fi

# 获取 python3 的完整路径
PYTHON_CMD=$(command -v python3)
PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2 | cut -d'.' -f1,2)

# 检查版本是否符合要求（>= 3.11）
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo -e "${RED}❌ Python 版本不符合要求: ${PYTHON_VERSION}${NC}"
    echo -e "${YELLOW}项目需要 Python 3.11 或更高版本${NC}"
    echo ""
    echo "找到的 Python 路径: $PYTHON_CMD"
    echo ""
    echo "请选择以下方案之一："
    echo "  1. 使用特定版本的 Python: PYTHON_CMD=/path/to/python3.12 ./scripts/setup.sh"
    echo "  2. 安装 Python 3.11+ 并确保其在 PATH 中优先"
    echo "  3. 使用 pyenv 或 conda 管理多个 Python 版本"
    exit 1
fi

echo -e "${GREEN}✅ Python 版本: ${PYTHON_VERSION}${NC}"
echo -e "${GREEN}📍 Python 路径: ${PYTHON_CMD}${NC}"

# 检查是否需要升级 pip
echo ""
echo "📦 检查 pip..."
if [ ! -f "venv/bin/pip" ]; then
    echo "需要创建虚拟环境..."
else
    echo -e "${GREEN}✅ pip 已存在${NC}"
fi

# 创建虚拟环境
echo ""
echo "🔧 创建虚拟环境..."
if [ ! -d "venv" ]; then
    # 使用指定的 Python 命令创建虚拟环境
    # 如果用户设置了 PYTHON_CMD 环境变量，优先使用
    if [ -n "$PYTHON_CMD" ]; then
        $PYTHON_CMD -m venv venv
    else
        python3 -m venv venv
    fi
    echo -e "${GREEN}✅ 虚拟环境创建成功${NC}"
else
    echo -e "${YELLOW}⚠️  虚拟环境已存在，跳过创建${NC}"
    echo -e "${YELLOW}   如需重新创建，请先删除: rm -rf venv${NC}"
fi

# 激活虚拟环境
echo ""
echo "🔌 激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo ""
echo "⬆️  升级 pip..."
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✅ pip 升级完成${NC}"

# 安装依赖
echo ""
echo "📦 安装 Python 依赖..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${RED}❌ 未找到 requirements.txt${NC}"
    exit 1
fi

# 创建必要的目录
echo ""
echo "📁 创建必要的目录..."
mkdir -p logs
mkdir -p config
echo -e "${GREEN}✅ 目录创建完成${NC}"

# 生成 .env 文件
echo ""
if [ ! -f ".env" ]; then
    echo "📝 创建 .env 文件..."
    cat > .env << 'EOF'
# GitHub 配置
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here
GITHUB_TOKEN=ghp_your-token-here
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=your-repo

# 代码仓库路径
REPO_PATH=/path/to/your/local/repo

# Anthropic API Key (Claude Code 需要)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# 基本认证（可选）
BASIC_AUTH_USERNAME=admin
BASIC_AUTH_PASSWORD=your-secure-password

# Slack 通知（可选）
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Telegram 通知（可选）
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id
EOF
    echo -e "${GREEN}✅ .env 文件创建完成${NC}"
else
    echo -e "${YELLOW}⚠️  .env 文件已存在，跳过创建${NC}"
fi

# 检查 Claude Code CLI
echo ""
echo "🔍 检查 Claude Code CLI..."
# 同时检查 claude 和 claude-code 命令
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>&1 || echo "已安装")
    echo -e "${GREEN}✅ Claude Code CLI: ${CLAUDE_VERSION}${NC}"
elif command -v claude-code &> /dev/null; then
    CLAUDE_VERSION=$(claude-code --version 2>&1 || echo "已安装")
    echo -e "${GREEN}✅ Claude Code CLI: ${CLAUDE_VERSION}${NC}"
else
    echo -e "${YELLOW}⚠️  未找到 Claude Code CLI${NC}"
    echo "请使用以下命令安装："
    echo "  npm install -g @anthropic-ai/claude-code"
fi

# 设置脚本权限
echo ""
echo "🔐 设置脚本执行权限..."
chmod +x scripts/*.sh 2>/dev/null || true
echo -e "${GREEN}✅ 权限设置完成${NC}"

# 完成
echo ""
echo "======================================"
echo -e "${GREEN}✅ 初始化完成！${NC}"
echo ""
echo "📝 下一步操作："
echo "  1. 编辑 .env 文件，填写必要的配置信息"
echo "  2. 确保 Claude Code CLI 已安装"
echo "  3. 运行: source venv/bin/activate"
echo "  4. 启动服务: ./scripts/dev.sh"
echo ""
echo "📚 更多信息请参考 README.md"
echo ""
