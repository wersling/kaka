#!/bin/bash
# Kaka Dev 一键安装脚本
# curl -sSL https://install.kaka.dev | sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════╗"
echo "║   🚀 Kaka Dev - AI 开发调度服务      ║"
echo "║   一键安装脚本                        ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# 检测 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3.11+ 未安装${NC}"
    echo "请先安装 Python 3.11 或更高版本:"
    echo "  - macOS: brew install python@3.11"
    echo "  - Ubuntu: sudo apt-get install python3.11"
    echo "  - 下载: https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓${NC} 找到 Python $PYTHON_VERSION"

# 检查版本
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo -e "${RED}❌ Python 3.11+ 是必需的 (当前: $PYTHON_VERSION)${NC}"
    exit 1
fi

# 检测 pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${YELLOW}⚠️  pip3 未找到，尝试安装...${NC}"

    # 尝试安装 pip
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3-pip
    elif command -v brew &> /dev/null; then
        brew install python3-pip
    else
        echo -e "${RED}❌ 无法自动安装 pip，请手动安装${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓${NC} pip3 已安装"
echo ""

# 检测 Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git 未安装${NC}"
    echo "请先安装 Git:"
    echo "  - macOS: brew install git"
    echo "  - Ubuntu: sudo apt-get install git"
    exit 1
fi

echo -e "${GREEN}✓${NC} Git 已安装"
echo ""

# 创建虚拟环境
VENV_DIR="$HOME/.kaka-dev"
echo -e "${BLUE}📦 创建虚拟环境: $VENV_DIR${NC}"

if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  虚拟环境已存在，跳过创建${NC}"
else
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓${NC} 虚拟环境创建完成"
fi

# 激活虚拟环境
echo -e "${BLUE}🔄 激活虚拟环境${NC}"
source "$VENV_DIR/bin/activate"

# 升级 pip
echo -e "${BLUE}⬆️  升级 pip${NC}"
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓${NC} pip 已升级"
echo ""

# 克隆仓库
REPO_DIR="$HOME/kaka-dev"
if [ -d "$REPO_DIR" ]; then
    echo -e "${YELLOW}⚠️  仓库目录已存在: $REPO_DIR${NC}"
    read -p "是否更新? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$REPO_DIR"
        git pull origin main
    fi
else
    echo -e "${BLUE}📥 克隆仓库${NC}"
    git clone https://github.com/your-username/kaka.git "$REPO_DIR"
    echo -e "${GREEN}✓${NC} 仓库克隆完成"
fi

# 安装依赖
echo ""
echo -e "${BLUE}📦 安装依赖${NC}"
cd "$REPO_DIR"
pip install -r requirements.txt
echo -e "${GREEN}✓${NC} 依赖安装完成"
echo ""

# 创建 .env 文件
if [ ! -f "$REPO_DIR/.env" ]; then
    echo -e "${BLUE}📝 创建配置文件${NC}"
    cat > "$REPO_DIR/.env" << EOF
# Kaka Dev 配置文件
# 请运行: kaka-dev configure 完成配置

# GitHub 配置
GITHUB_TOKEN=
GITHUB_REPO_OWNER=
GITHUB_REPO_NAME=
GITHUB_WEBHOOK_SECRET=

# 仓库配置
REPO_PATH=

# Anthropic API
ANTHROPIC_API_KEY=
EOF
    echo -e "${GREEN}✓${NC} 配置文件已创建: $REPO_DIR/.env"
fi

# 创建启动脚本
echo -e "${BLUE}📜 创建启动脚本${NC}"
cat > "$HOME/kaka-dev" << 'EOF'
#!/bin/bash
source $HOME/.kaka-dev/bin/activate
cd $HOME/kaka-dev
kaka-dev "$@"
EOF

chmod +x "$HOME/kaka-dev"
echo -e "${GREEN}✓${NC} 启动脚本已创建: $HOME/kaka-dev"
echo ""

# 完成
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}   ${GREEN}✅ 安装完成！${NC}                        ${GREEN}║${NC}"
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo ""
echo "📝 下一步:"
echo ""
echo "  1. 配置服务:"
echo -e "     ${BLUE}kaka-dev configure${NC}"
echo ""
echo "  2. 启动服务:"
echo -e "     ${BLUE}kaka-dev start${NC}"
echo ""
echo "  3. 查看状态:"
echo -e "     ${BLUE}kaka-dev status${NC}"
echo ""
echo "  4. 查看日志:"
echo -e "     ${BLUE}kaka-dev logs${NC}"
echo ""
echo "📚 文档:"
echo "   https://github.com/your-username/kaka"
echo ""
