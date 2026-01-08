#!/bin/bash
# AI 开发调度服务 - 开发启动脚本

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ 虚拟环境不存在${NC}"
    echo "请先运行: ./scripts/setup.sh"
    exit 1
fi

# 激活虚拟环境
echo -e "${BLUE}🔌 激活虚拟环境...${NC}"
source venv/bin/activate

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env 文件不存在${NC}"
    echo "请先运行: ./scripts/setup.sh"
    exit 1
fi

# 加载环境变量
echo -e "${BLUE}📝 加载环境变量...${NC}"
export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)

# 验证必需的环境变量
echo ""
echo "🔍 验证配置..."
MISSING_VARS=0

if [ -z "$GITHUB_WEBHOOK_SECRET" ] || [ "$GITHUB_WEBHOOK_SECRET" = "your-webhook-secret-here" ]; then
    echo -e "${YELLOW}⚠️  警告: GITHUB_WEBHOOK_SECRET 未设置${NC}"
    MISSING_VARS=1
fi

if [ -z "$GITHUB_TOKEN" ] || [ "$GITHUB_TOKEN" = "ghp_your-token-here" ]; then
    echo -e "${YELLOW}⚠️  警告: GITHUB_TOKEN 未设置${NC}"
    MISSING_VARS=1
fi

if [ -z "$REPO_PATH" ] || [ "$REPO_PATH" = "/path/to/your/local/repo" ]; then
    echo -e "${YELLOW}⚠️  警告: REPO_PATH 未设置${NC}"
    MISSING_VARS=1
fi

if [ $MISSING_VARS -eq 1 ]; then
    echo ""
    echo -e "${RED}❌ 请先在 .env 文件中配置必要的环境变量${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 配置验证通过${NC}"

# 确保日志目录存在
mkdir -p logs

# 启动服务
echo ""
echo "======================================"
echo -e "${GREEN}🚀 启动 AI 开发调度服务...${NC}"
echo "======================================"
echo ""
echo -e "${BLUE}📍 服务地址:${NC} http://localhost:8000"
echo -e "${BLUE}📖 API 文档:${NC} http://localhost:8000/docs"
echo -e "${BLUE}🔍 健康检查:${NC} http://localhost:8000/health"
echo ""
echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"
echo ""

# 启动 uvicorn
uvicorn app.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
