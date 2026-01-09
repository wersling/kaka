#!/usr/bin/env python3
"""
性能测试报告生成器

解析 pytest-benchmark 的 JSON 输出，生成 Markdown 报告和图表
"""

import json
import sys
from pathlib import Path


def load_benchmark_data(json_path: str) -> dict:
    """加载基准测试 JSON 数据"""
    with open(json_path, 'r') as f:
        return json.load(f)


def format_time(ns: float) -> str:
    """格式化时间为可读字符串"""
    if ns < 1000:
        return f"{ns:.2f} ns"
    elif ns < 1_000_000:
        return f"{ns/1000:.2f} μs"
    elif ns < 1_000_000_000:
        return f"{ns/1_000_000:.2f} ms"
    else:
        return f"{ns/1_000_000_000:.2f} s"


def generate_summary_table(benchmarks: dict) -> str:
    """生成性能摘要表"""
    lines = []
    lines.append("## 性能基准摘要\n")
    lines.append("| 测试项 | 最小值 | 平均值 | 中位数 | 最大值 | 吞吐量 |")
    lines.append("|--------|--------|--------|--------|--------|--------|")
    
    for bench in benchmarks.get('benchmarks', []):
        name = bench['name']
        stats = bench['stats']
        
        min_time = format_time(stats['min'])
        mean_time = format_time(stats['mean'])
        median_time = format_time(stats['median'])
        max_time = format_time(stats['max'])
        ops = f"{stats['ops']:,.0f}"
        
        lines.append(f"| {name} | {min_time} | {mean_time} | {median_time} | {max_time} | {ops} |")
    
    return '\n'.join(lines)


def compare_with_baseline(current: dict, baseline: dict) -> str:
    """对比当前数据与基线数据"""
    lines = []
    lines.append("## 性能回归分析\n")
    lines.append("| 测试项 | 基线平均值 | 当前平均值 | 变化 | 状态 |")
    lines.append("|--------|------------|------------|------|------|")
    
    baseline_benches = {b['name']: b for b in baseline.get('benchmarks', [])}
    
    for current_bench in current.get('benchmarks', []):
        name = current_bench['name']
        
        if name not in baseline_benches:
            continue
        
        baseline_mean = baseline_benches[name]['stats']['mean']
        current_mean = current_bench['stats']['mean']
        
        change_pct = ((current_mean - baseline_mean) / baseline_mean) * 100
        
        if abs(change_pct) < 5:
            status = "✅ 稳定"
        elif change_pct > 0:
            status = "⚠️ 退化"
        else:
            status = "✅ 改进"
        
        baseline_str = format_time(baseline_mean)
        current_str = format_time(current_mean)
        
        lines.append(f"| {name} | {baseline_str} | {current_str} | {change_pct:+.2f}% | {status} |")
    
    return '\n'.join(lines)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python generate_performance_report.py <benchmark_results.json>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    data = load_benchmark_data(json_path)
    
    # 生成报告
    report = []
    report.append("# 性能测试报告\n")
    report.append(f"**机器信息**: {data['machine_info']['processor']}")
    report.append(f"**Python 版本**: {data['machine_info']['python_version']}")
    report.append(f"**测试时间**: {data['datetime']}\n")
    
    report.append(generate_summary_table(data))
    
    output = '\n'.join(report)
    print(output)
    
    # 写入文件
    output_path = Path(json_path).parent / 'performance_report.md'
    with open(output_path, 'w') as f:
        f.write(output)
    
    print(f"\n✓ 报告已保存到: {output_path}")


if __name__ == '__main__':
    main()
