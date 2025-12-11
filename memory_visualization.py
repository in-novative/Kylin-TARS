#!/usr/bin/env python3
"""
记忆轨迹可视化模块

功能：
1. 使用networkx绘制轨迹关联图
2. 支持按时间范围/工具类型/智能体筛选
3. 生成可视化HTML

作者：GUI Agent Team
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

# 尝试导入可视化库
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    print("提示: networkx 未安装，可视化功能不可用")
    print("安装命令: pip install networkx")

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # 非交互式后端
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("提示: matplotlib 未安装，可视化功能不可用")

from memory_store import list_trajectories, STORAGE_DIR


def build_trajectory_graph(
    trajectories: List[Dict],
    filter_agent: Optional[str] = None,
    filter_tool: Optional[str] = None,
    time_range_days: Optional[int] = None
) -> Optional[object]:
    """
    构建轨迹关联图
    
    Args:
        trajectories: 轨迹列表
        filter_agent: 筛选智能体（可选）
        filter_tool: 筛选工具（可选）
        time_range_days: 时间范围（天数，可选）
    
    Returns:
        NetworkX图对象
    """
    if not HAS_NETWORKX:
        return None
    
    G = nx.DiGraph()  # 有向图
    
    # 时间筛选
    if time_range_days:
        cutoff_time = datetime.now() - timedelta(days=time_range_days)
        cutoff_timestamp = int(cutoff_time.timestamp())
        trajectories = [t for t in trajectories if t.get("timestamp_unix", 0) >= cutoff_timestamp]
    
    for traj in trajectories:
        task = traj.get("task", "")
        task_hash = traj.get("task_hash", "")
        agents = traj.get("agents_involved", [])
        reasoning_chain = traj.get("reasoning_chain", {})
        execution_plan = reasoning_chain.get("execution_plan", [])
        
        # 智能体筛选
        if filter_agent and filter_agent not in agents:
            continue
        
        # 工具筛选
        if filter_tool:
            tools_found = False
            for step in execution_plan:
                if isinstance(step, dict) and filter_tool in step.get("tool", ""):
                    tools_found = True
                    break
            if not tools_found:
                continue
        
        # 添加任务节点
        task_id = f"task_{task_hash}"
        G.add_node(task_id, type="task", label=task[:30] + "..." if len(task) > 30 else task, 
                   success=traj.get("success", False), timestamp=traj.get("timestamp", ""))
        
        # 添加智能体节点和边
        for agent in agents:
            agent_id = f"agent_{agent}"
            if not G.has_node(agent_id):
                G.add_node(agent_id, type="agent", label=agent)
            G.add_edge(task_id, agent_id, relation="uses")
        
        # 添加工具节点和边
        for step in execution_plan:
            if isinstance(step, dict):
                tool = step.get("tool", "")
                agent = step.get("agent", "")
                if tool:
                    tool_id = f"tool_{tool}"
                    if not G.has_node(tool_id):
                        G.add_node(tool_id, type="tool", label=tool.split(".")[-1])
                    G.add_edge(agent_id if agent else task_id, tool_id, relation="calls")
    
    return G


def visualize_graph_to_html(
    G: object,
    output_path: Optional[str] = None,
    layout: str = "spring"
) -> str:
    """
    将图可视化并保存为HTML
    
    Args:
        G: NetworkX图对象
        output_path: 输出路径（可选）
        layout: 布局算法（spring/circular/hierarchical）
    
    Returns:
        HTML字符串
    """
    if not HAS_NETWORKX or not G:
        return "<p>可视化功能不可用（需要安装networkx）</p>"
    
    try:
        import matplotlib.pyplot as plt
        from matplotlib import cm
        import base64
        from io import BytesIO
        
        # 设置图形大小
        plt.figure(figsize=(12, 8))
        
        # 选择布局
        if layout == "spring":
            pos = nx.spring_layout(G, k=1, iterations=50)
        elif layout == "circular":
            pos = nx.circular_layout(G)
        else:
            pos = nx.spring_layout(G)
        
        # 按类型分组节点
        task_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "task"]
        agent_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "agent"]
        tool_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "tool"]
        
        # 绘制边
        nx.draw_networkx_edges(G, pos, alpha=0.3, edge_color='gray', arrows=True, arrowsize=10)
        
        # 绘制节点
        if task_nodes:
            nx.draw_networkx_nodes(G, pos, nodelist=task_nodes, node_color='lightblue', 
                                  node_size=1000, alpha=0.8, label="任务")
        if agent_nodes:
            nx.draw_networkx_nodes(G, pos, nodelist=agent_nodes, node_color='lightgreen', 
                                  node_size=800, alpha=0.8, label="智能体")
        if tool_nodes:
            nx.draw_networkx_nodes(G, pos, nodelist=tool_nodes, node_color='lightcoral', 
                                  node_size=600, alpha=0.8, label="工具")
        
        # 绘制标签
        labels = {n: d.get("label", n) for n, d in G.nodes(data=True)}
        nx.draw_networkx_labels(G, pos, labels, font_size=8, font_family='sans-serif')
        
        plt.axis('off')
        plt.title("记忆轨迹关联图", fontsize=16, fontweight='bold')
        plt.legend(loc='upper right')
        
        # 转换为base64图片
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        # 生成HTML
        html = f"""
        <div style="text-align: center;">
            <img src="data:image/png;base64,{image_base64}" style="max-width: 100%; height: auto;" />
            <p style="margin-top: 10px; color: #666;">
                节点统计: 任务 {len(task_nodes)} | 智能体 {len(agent_nodes)} | 工具 {len(tool_nodes)} | 边 {G.number_of_edges()}
            </p>
        </div>
        """
        
        # 保存到文件（如果指定）
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)
        
        return html
        
    except Exception as e:
        return f"<p>可视化生成失败: {e}</p>"


def get_trajectory_summary(trajectories: List[Dict]) -> Dict:
    """
    获取轨迹摘要统计
    
    Args:
        trajectories: 轨迹列表
    
    Returns:
        摘要字典
    """
    summary = {
        "total": len(trajectories),
        "success_count": sum(1 for t in trajectories if t.get("success", False)),
        "agents": {},
        "tools": {},
        "recent_tasks": []
    }
    
    for traj in trajectories:
        # 统计智能体
        for agent in traj.get("agents_involved", []):
            summary["agents"][agent] = summary["agents"].get(agent, 0) + 1
        
        # 统计工具
        execution_plan = traj.get("reasoning_chain", {}).get("execution_plan", [])
        for step in execution_plan:
            if isinstance(step, dict):
                tool = step.get("tool", "")
                if tool:
                    summary["tools"][tool] = summary["tools"].get(tool, 0) + 1
    
    # 最近任务
    summary["recent_tasks"] = [
        {
            "task": t.get("task", "")[:50],
            "timestamp": t.get("timestamp", ""),
            "success": t.get("success", False)
        }
        for t in trajectories[:10]
    ]
    
    return summary


def generate_visualization_html(
    filter_agent: Optional[str] = None,
    filter_tool: Optional[str] = None,
    time_range_days: Optional[int] = None,
    layout: str = "spring"
) -> str:
    """
    生成完整的可视化HTML页面
    
    Args:
        filter_agent: 筛选智能体
        filter_tool: 筛选工具
        time_range_days: 时间范围（天数）
        layout: 布局算法
    
    Returns:
        HTML字符串
    """
    # 获取轨迹
    trajectories = list_trajectories(limit=100)
    
    if not trajectories:
        return "<p>暂无记忆轨迹数据</p>"
    
    # 构建图
    G = build_trajectory_graph(
        trajectories=trajectories,
        filter_agent=filter_agent,
        filter_tool=filter_tool,
        time_range_days=time_range_days
    )
    
    if not G or G.number_of_nodes() == 0:
        return "<p>根据筛选条件未找到匹配的轨迹</p>"
    
    # 生成可视化
    graph_html = visualize_graph_to_html(G, layout=layout)
    
    # 生成摘要
    filtered_trajectories = trajectories
    if time_range_days:
        cutoff_time = datetime.now() - timedelta(days=time_range_days)
        cutoff_timestamp = int(cutoff_time.timestamp())
        filtered_trajectories = [t for t in trajectories if t.get("timestamp_unix", 0) >= cutoff_timestamp]
    
    summary = get_trajectory_summary(filtered_trajectories)
    
    # 组合HTML
    html = f"""
    <div style="padding: 20px;">
        <h2>记忆轨迹可视化</h2>
        
        <div style="margin-bottom: 20px;">
            <h3>统计摘要</h3>
            <ul>
                <li>总轨迹数: {summary['total']}</li>
                <li>成功数量: {summary['success_count']}</li>
                <li>成功率: {summary['success_count']/summary['total']*100:.1f}%</li>
            </ul>
            
            <h4>智能体使用频率</h4>
            <ul>
                {''.join([f'<li>{agent}: {count}次</li>' for agent, count in sorted(summary['agents'].items(), key=lambda x: x[1], reverse=True)[:5]])}
            </ul>
            
            <h4>工具使用频率</h4>
            <ul>
                {''.join([f'<li>{tool.split(".")[-1]}: {count}次</li>' for tool, count in sorted(summary['tools'].items(), key=lambda x: x[1], reverse=True)[:5]])}
            </ul>
        </div>
        
        <div>
            <h3>轨迹关联图</h3>
            {graph_html}
        </div>
        
        <div style="margin-top: 20px;">
            <h3>最近任务</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th>任务</th>
                    <th>时间</th>
                    <th>状态</th>
                </tr>
                {''.join([f'<tr><td>{t["task"]}</td><td>{t["timestamp"]}</td><td>{"✓" if t["success"] else "✗"}</td></tr>' for t in summary["recent_tasks"]])}
            </table>
        </div>
    </div>
    """
    
    return html


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=== 测试记忆轨迹可视化 ===")
    
    if not HAS_NETWORKX:
        print("⚠️ networkx 未安装，无法进行可视化测试")
        exit(1)
    
    # 获取轨迹
    trajectories = list_trajectories(limit=20)
    print(f"获取到 {len(trajectories)} 条轨迹")
    
    if trajectories:
        # 构建图
        G = build_trajectory_graph(trajectories)
        print(f"图节点数: {G.number_of_nodes()}")
        print(f"图边数: {G.number_of_edges()}")
        
        # 生成可视化
        html = generate_visualization_html()
        print(f"\n可视化HTML长度: {len(html)} 字符")
        
        # 保存测试
        output_file = os.path.expanduser("~/.config/kylin-gui-agent/trajectory_visualization.html")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✓ 可视化已保存到: {output_file}")
    else:
        print("⚠️ 无轨迹数据")

