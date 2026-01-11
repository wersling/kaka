#!/bin/bash

# E2E 测试执行脚本
#
# 用法:
#   ./scripts/run_e2e_tests.sh              # 运行所有 E2E 测试
#   ./scripts/run_e2e_tests.sh p0           # 只运行 P0 测试
#   ./scripts/run_e2e_tests.sh p1           # 只运行 P1 测试
#   ./scripts/run_e2e_tests.sh report       # 生成测试报告
#   ./scripts/run_e2e_tests.sh coverage     # 生成覆盖率报告

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    if ! command -v python &> /dev/null; then
        log_error "Python 未安装"
        exit 1
    fi

    if ! command -v pytest &> /dev/null; then
        log_error "pytest 未安装，正在安装..."
        pip install pytest pytest-asyncio pytest-mock pytest-cov
    fi

    log_success "依赖检查完成"
}

# 设置测试环境
setup_test_env() {
    log_info "设置测试环境..."

    # 设置测试环境变量
    export GITHUB_WEBHOOK_SECRET="test_secret_12345"
    export GITHUB_TOKEN="ghp_test_token_12345"
    export GITHUB_REPO_OWNER="testowner"
    export GITHUB_REPO_NAME="testrepo"
    export REPO_PATH="/tmp/test_repo"

    # 创建测试仓库目录
    mkdir -p "$REPO_PATH"

    log_success "测试环境设置完成"
}

# 清理测试环境
cleanup_test_env() {
    log_info "清理测试环境..."

    # 清理临时仓库
    if [ -d "/tmp/test_repo" ]; then
        rm -rf "/tmp/test_repo"
    fi

    # 清理其他临时文件
    find /tmp -name "e2e_test_repo_*" -type d -mtime +1 -exec rm -rf {} + 2>/dev/null || true

    log_success "测试环境清理完成"
}

# 运行所有 E2E 测试
run_all_e2e_tests() {
    log_info "运行所有 E2E 测试..."

    pytest \
        tests/test_e2e_scenarios.py \
        -v \
        --tb=short \
        --strict-markers \
        -m e2e \
        "$@"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "所有 E2E 测试通过！"
    else
        log_error "部分 E2E 测试失败"
    fi

    return $exit_code
}

# 运行 P0 测试
run_p0_tests() {
    log_info "运行 P0 优先级测试（必须通过）..."

    pytest \
        tests/test_e2e_scenarios.py \
        -v \
        --tb=short \
        -k "ScenarioA or ScenarioB or ScenarioC or ScenarioD or ScenarioE" \
        "$@"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "所有 P0 测试通过！"
    else
        log_error "部分 P0 测试失败"
    fi

    return $exit_code
}

# 运行 P1 测试
run_p1_tests() {
    log_info "运行 P1 优先级测试（重要）..."

    pytest \
        tests/test_e2e_scenarios.py \
        -v \
        --tb=short \
        -k "ScenarioF or ScenarioG or ScenarioH or ScenarioI or ScenarioJ" \
        "$@"

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "所有 P1 测试通过！"
    else
        log_error "部分 P1 测试失败"
    fi

    return $exit_code
}

# 生成测试报告
generate_test_report() {
    log_info "生成 E2E 测试报告..."

    local report_dir="test_reports"
    mkdir -p "$report_dir"

    pytest \
        tests/test_e2e_scenarios.py \
        -v \
        --tb=short \
        --html="$report_dir/e2e_test_report.html" \
        --self-contained-html \
        --cov=app \
        --cov-report=html:"$report_dir/e2e_coverage_report" \
        --cov-report=term-missing \
        -m e2e

    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_success "测试报告生成完成！"
        log_info "报告位置:"
        echo "  - HTML 测试报告: $report_dir/e2e_test_report.html"
        echo "  - 覆盖率报告: $report_dir/e2e_coverage_report/index.html"

        # 在 macOS 上自动打开报告
        if [[ "$OSTYPE" == "darwin"* ]]; then
            log_info "正在打开测试报告..."
            open "$report_dir/e2e_test_report.html" 2>/dev/null || true
        fi
    else
        log_error "测试报告生成失败"
    fi

    return $exit_code
}

# 运行特定场景
run_specific_scenario() {
    local scenario=$1

    if [ -z "$scenario" ]; then
        log_error "请指定场景名称，例如: ScenarioA"
        return 1
    fi

    log_info "运行场景: $scenario..."

    pytest \
        tests/test_e2e_scenarios.py \
        -v \
        --tb=short \
        -k "$scenario" \
        "$@"

    return $?
}

# 显示帮助信息
show_help() {
    cat << EOF
E2E 测试执行脚本

用法:
  $0 [命令] [pytest选项]

命令:
  (无)        运行所有 E2E 测试
  p0          运行 P0 优先级测试（必须通过）
  p1          运行 P1 优先级测试（重要）
  report      生成测试报告和覆盖率报告
  coverage    生成覆盖率报告（同 report）
  scenario<X> 运行特定场景（例如: ScenarioA）
  help        显示此帮助信息

示例:
  $0                              # 运行所有 E2E 测试
  $0 p0                            # 只运行 P0 测试
  $0 p1                            # 只运行 P1 测试
  $0 report                        # 生成测试报告
  $0 ScenarioA                     # 运行场景 A
  $0 ScenarioA -v -s               # 运行场景 A（详细输出）

场景列表:
  ScenarioA - 标签触发工作流
  ScenarioB - 评论触发工作流
  ScenarioC - Claude 开发失败
  ScenarioD - Git 冲突处理
  ScenarioE - GitHub API 失败
  ScenarioF - 空 Issue 内容
  ScenarioG - 超长 Issue 内容
  ScenarioH - 特殊字符处理
  ScenarioI - 并发 Issue 处理
  ScenarioJ - 外部服务集成

EOF
}

# 主函数
main() {
    local command=${1:-}
    shift || true

    # 检查依赖
    check_dependencies

    # 设置测试环境
    setup_test_env

    # 清理函数
    trap cleanup_test_env EXIT INT TERM

    # 执行命令
    case $command in
        p0)
            run_p0_tests "$@"
            ;;
        p1)
            run_p1_tests "$@"
            ;;
        report|coverage)
            generate_test_report "$@"
            ;;
        Scenario*)
            run_specific_scenario "$command" "$@"
            ;;
        help|--help|-h)
            show_help
            ;;
        "")
            run_all_e2e_tests "$@"
            ;;
        *)
            log_error "未知命令: $command"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
