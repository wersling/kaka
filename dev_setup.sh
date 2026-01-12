#!/bin/bash
# Kaka Auto - 开发环境初始化脚本

set -e  # 遇到错误立即退出

# 莫兰迪深色系
GREEN='\033[0;38;5;71m'      # #5F8700 - 深橄榄绿
BLUE='\033[0;38;5;25m'       # #005F87 - 深海蓝
YELLOW='\033[0;38;5;136m'    # #AF8700 - 深芥末黄
GRAY='\033[0;38;5;245m'      # #8A8A8A - 中性灰
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════╗"
echo "║   🚀 Kaka Auto - 开发环境初始化      ║"
echo "╚═══════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# 检查 Python 版本
echo "📋 检查 Python 版本..."
if ! command -v python &> /dev/null; then
    echo -e "${YELLOW}❌ 未找到 Python 3${NC}"
    echo "请先安装 Python 3.11 或更高版本"
    exit 1
fi

# 获取 python 的完整路径
PYTHON_CMD=$(command -v python)
PYTHON_VERSION=$($PYTHON_CMD --version | cut -d' ' -f2 | cut -d'.' -f1,2)

# 检查版本是否符合要求（>= 3.11）
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo -e "${YELLOW}❌ Python 版本不符合要求: ${PYTHON_VERSION}${NC}"
    echo -e "${YELLOW}项目需要 Python 3.11 或更高版本${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python 版本: ${PYTHON_VERSION}${NC}"
echo ""

# 创建虚拟环境
echo "🔧 创建虚拟环境..."
if [ -d "venv" ]; then
    echo -e "${YELLOW}⚠️  虚拟环境已存在，跳过创建${NC}"
    echo -e "${YELLOW}   如需重新创建，请先删除: rm -rf venv${NC}"
else
    python -m venv venv
    echo -e "${GREEN}✅ 虚拟环境创建成功${NC}"
fi

# 激活虚拟环境
echo ""
echo "🔌 激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo "⬆️  升级 pip..."
pip install --upgrade pip -q
echo -e "${GREEN}✅ pip 升级完成${NC}"

# 安装项目（开发模式）
echo ""
echo "📦 安装项目（开发模式）..."
pip install -e ".[dev]"
echo -e "${GREEN}✅ 项目安装完成（含开发依赖）${NC}"

# 创建必要的目录
echo ""
echo "📁 创建必要的目录..."
mkdir -p logs config data
echo -e "${GREEN}✅ 目录创建完成${NC}"

# 完成
echo ""
echo "╔═══════════════════════════════════════╗"
echo -e "${GREEN}║${NC}   ${GREEN}✅ 初始化完成！${NC}                ${GREEN}║${NC}"
echo "╚═══════════════════════════════════════╝"
echo ""

# 检查是否需要配置
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  未找到 .env 文件${NC}"
    echo ""
    read -p "是否现在运行配置向导？ [Y/n]: " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo ""
        echo "🚀 启动配置向导..."
        kaka configure
    else
        echo ""
        echo "您可以稍后运行: kaka configure"
    fi
else
    echo -e "${GREEN}✅ 配置文件已存在${NC}"
fi

echo ""
echo "📝 下一步操作:"
echo ""
echo "  1. 激活虚拟环境（如果还没激活）:"
echo -e "     ${BLUE}source venv/bin/activate${NC}"
echo ""
echo "  2. 启动开发服务器:"
echo -e "     ${BLUE}kaka start${NC}"
echo ""
echo "  3. 运行测试:"
echo -e "     ${BLUE}make test${NC}"
echo ""
echo "📚 更多信息请参考 README.md"
echo ""
