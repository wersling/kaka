#!/bin/bash
# Kaka Dev 演示脚本
# 用于本地演示和测试

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔═══════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   🎯 Kaka Dev - 演示脚本             ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════╝${NC}"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  虚拟环境不存在，正在创建...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

# 检查配置
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env 文件不存在${NC}"
    echo -e "${YELLOW}   请先运行: kaka-dev configure${NC}"
    exit 1
fi

# 显示菜单
show_menu() {
    echo ""
    echo -e "${GREEN}📋 请选择操作：${NC}"
    echo ""
    echo "  1. 启动服务"
    echo "  2. 打开配置向导"
    echo "  3. 打开 Dashboard"
    echo "  4. 查看服务状态"
    echo "  5. 查看日志"
    echo "  6. 运行测试"
    echo "  7. 生成 Webhook URL"
    echo "  8. 清理并重启"
    echo "  0. 退出"
    echo ""
}

# 启动服务
start_service() {
    echo -e "${BLUE}🚀 启动服务...${NC}"
    python -m app.main
}

# 打开配置向导
open_config() {
    echo -e "${BLUE}⚙️  打开配置向导...${NC}"
    echo ""
    echo "请在浏览器中打开:"
    echo "  http://localhost:8000/config"
    echo ""

    # 在后台启动服务
    python -m app.main &
    SERVER_PID=$!

    # 等待服务启动
    sleep 3

    # 尝试打开浏览器
    if command -v open &> /dev/null; then
        open http://localhost:8000/config
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8000/config
    else
        echo -e "${YELLOW}⚠️  无法自动打开浏览器${NC}"
    fi

    echo ""
    echo "按 Ctrl+C 停止服务"
    wait $SERVER_PID
}

# 打开 Dashboard
open_dashboard() {
    echo -e "${BLUE}📊 打开 Dashboard...${NC}"
    echo ""
    echo "请在浏览器中打开:"
    echo "  http://localhost:8000/dashboard"
    echo ""

    # 在后台启动服务
    python -m app.main &
    SERVER_PID=$!

    # 等待服务启动
    sleep 3

    # 尝试打开浏览器
    if command -v open &> /dev/null; then
        open http://localhost:8000/dashboard
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8000/dashboard
    else
        echo -e "${YELLOW}⚠️  无法自动打开浏览器${NC}"
    fi

    echo ""
    echo "按 Ctrl+C 停止服务"
    wait $SERVER_PID
}

# 查看状态
check_status() {
    echo -e "${BLUE}📋 服务状态：${NC}"
    echo ""

    # 检查进程
    if pgrep -f "python -m app.main" > /dev/null; then
        echo -e "${GREEN}✓${NC} 服务运行中"
        echo ""
        echo "访问地址:"
        echo "  Dashboard: http://localhost:8000/dashboard"
        echo "  API 文档:  http://localhost:8000/docs"
        echo "  配置向导:  http://localhost:8000/config"
    else
        echo -e "${RED}✗${NC} 服务未运行"
    fi
}

# 查看日志
view_logs() {
    echo -e "${BLUE}📋 最近日志：${NC}"
    echo ""

    if [ -f "logs/ai-scheduler.log" ]; then
        tail -n 20 logs/ai-scheduler.log
    else
        echo -e "${YELLOW}⚠️  日志文件不存在${NC}"
    fi
}

# 运行测试
run_tests() {
    echo -e "${BLUE}🧪 运行测试...${NC}"
    echo ""

    if command -v pytest &> /dev/null; then
        pytest tests/ -v --tb=short
    else
        echo -e "${RED}✗ pytest 未安装${NC}"
        echo "  请运行: pip install pytest"
    fi
}

# 生成 Webhook URL
generate_webhook() {
    echo -e "${BLUE}🔗 Webhook URL 生成${NC}"
    echo ""

    # 检查服务是否运行
    if ! pgrep -f "python -m app.main" > /dev/null; then
        echo -e "${YELLOW}⚠️  服务未运行，正在启动...${NC}"
        python -m app.main &
        SERVER_PID=$!
        sleep 3
    fi

    # 获取 URL
    WEBHOOK_URL="http://localhost:8000/webhook/github"

    echo "Webhook URL: ${GREEN}$WEBHOOK_URL${NC}"
    echo ""
    echo "GitHub 配置步骤："
    echo "  1. 进入仓库设置 → Webhooks → Add webhook"
    echo "  2. Payload URL: $WEBHOOK_URL"
    echo "  3. Content type: application/json"
    echo "  4. Secret: (查看 .env 文件中的 GITHUB_WEBHOOK_SECRET)"
    echo "  5. Events: Issues, Issue comments"
    echo ""
    echo "复制 URL 到剪贴板？(y/N)"
    read -r answer

    if [[ $answer =~ ^[Yy]$ ]]; then
        if command -v pbcopy &> /dev/null; then
            echo "$WEBHOOK_URL" | pbcopy
            echo -e "${GREEN}✓ 已复制到剪贴板${NC}"
        elif command -v xclip &> /dev/null; then
            echo "$WEBHOOK_URL" | xclip -selection clipboard
            echo -e "${GREEN}✓ 已复制到剪贴板${NC}"
        else
            echo -e "${YELLOW}⚠️  无法自动复制${NC}"
        fi
    fi
}

# 清理并重启
clean_restart() {
    echo -e "${BLUE}🧹 清理并重启...${NC}"
    echo ""

    # 停止服务
    if pgrep -f "python -m app.main" > /dev/null; then
        echo "停止服务..."
        pkill -f "python -m app.main"
        sleep 1
    fi

    # 清理 Python 缓存
    echo "清理缓存..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true

    echo -e "${GREEN}✓ 清理完成${NC}"
    echo ""

    # 重启服务
    start_service
}

# 主循环
while true; do
    show_menu
    read -p "请输入选项 (0-8): " choice

    case $choice in
        1)
            start_service
            ;;
        2)
            open_config
            ;;
        3)
            open_dashboard
            ;;
        4)
            check_status
            ;;
        5)
            view_logs
            ;;
        6)
            run_tests
            ;;
        7)
            generate_webhook
            ;;
        8)
            clean_restart
            ;;
        0)
            echo -e "${GREEN}👋 再见！${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}✗ 无效选项: $choice${NC}"
            ;;
    esac

    echo ""
    read -p "按 Enter 继续..."
done
