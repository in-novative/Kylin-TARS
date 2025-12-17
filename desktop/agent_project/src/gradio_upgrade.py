#!/usr/bin/env python3
"""
Kylin-TARS 智能体管理系统 - 升级版 Gradio UI

功能特性：
1. 4模块布局：指令输入、推理链解析、执行结果、记忆轨迹
2. 历史指令下拉框
3. 推理链 JSON 格式化展示（关键字段高亮）
4. 实时日志流
5. 截图轮播
6. 一键复制推理链
7. 演示模式（预设指令）

作者：GUI Agent Team
日期：2024-12
"""

import gradio as gr
import sys
import os
import json
import time
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置中文字体
rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'Noto Sans CJK']  # 替换为系统中可用的中文字体
rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 项目路径配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

# 导入智能体逻辑
from file_agent_logic import FileAgentLogic
from settings_agent_logic import SettingsAgentLogic
from network_agent_logic import NetworkAgentLogic
from app_agent_logic import AppAgentLogic

# 导入新增智能体（如果可用）
try:
    from monitor_agent_logic import MonitorAgentLogic
    from media_agent_logic import MediaAgentLogic
    HAS_MONITOR_AGENT = True
    HAS_MEDIA_AGENT = True
except ImportError:
    HAS_MONITOR_AGENT = False
    HAS_MEDIA_AGENT = False
    print("[WARNING] MonitorAgent或MediaAgent未找到，相关功能不可用")

# 导入记忆模块（如果可用）
HAS_MEMORY = False
HAS_CONFIG_MANAGER = False

# 导入记忆存储和检索模块
try:
    sys.path.insert(0, "/data1/cyx/Kylin-TARS")
    sys.path.insert(0, "/data1/cyx/Kylin-TARS/memory")  # 添加memory目录到路径
    from memory_store import list_trajectories, search_trajectories, save_collaboration_trajectory
    from memory_retrieve import retrieve_similar_trajectory, semantic_retrieve
    from memory_visualization import generate_visualization_html, get_trajectory_summary
    # 为了兼容性，创建别名
    save_trajectory = save_collaboration_trajectory
    HAS_MEMORY = True
except ImportError as e:
    print(f"[WARNING] 记忆模块未找到，记忆功能不可用: {e}")

# 导入协作日志模块（可选）
try:
    sys.path.insert(0, "/data1/cyx/Kylin-TARS/log")  # 添加log目录到路径（collaboration_logger）
    from collaboration_logger import query_logs, get_log_chain, get_log_statistics
except ImportError as e:
    print(f"[WARNING] 协作日志模块未找到，日志功能不可用: {e}")

# 导入MCP配置管理模块（可选）
try:
    sys.path.insert(0, "/data1/cyx/Kylin-TARS/run")  # 添加run目录到路径（mcp_config_manager）
    from mcp_config_manager import get_config_manager, PermissionLevel
    HAS_CONFIG_MANAGER = True
except ImportError as e:
    print(f"[WARNING] MCP配置管理模块未找到，配置管理功能不可用: {e}")

# 导入System-2推理模块（如果可用）
try:
    sys.path.insert(0, "/data1/cyx/Kylin-TARS/run")  # system2_prompt在run目录下
    from system2_prompt import generate_master_reasoning
    HAS_SYSTEM2 = True
except ImportError as e:
    HAS_SYSTEM2 = False
    print(f"[WARNING] System-2推理模块未找到，将使用关键词匹配模式: {e}")

# ============================================================
# 初始化智能体
# ============================================================
file_agent = FileAgentLogic()
settings_agent = SettingsAgentLogic()
network_agent = NetworkAgentLogic()
app_agent = AppAgentLogic()

# 初始化新增智能体（如果可用）
if HAS_MONITOR_AGENT:
    monitor_agent = MonitorAgentLogic()
if HAS_MEDIA_AGENT:
    media_agent = MediaAgentLogic()

# 截图目录
SCREENSHOT_DIR = os.path.join(PROJECT_ROOT, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 日志存储
execution_logs = []

# 权限控制（演示模式）
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"
REQUIRE_CONFIRMATION = os.environ.get("REQUIRE_CONFIRMATION", "false").lower() == "true"

# ============================================================
# 自定义CSS样式 - UKUI主题风格
# ============================================================
CUSTOM_CSS = """
/* UKUI主题配色 - 淡蓝色/麒麟橙 */
:root {
    --ukui-primary: #4A90E2;        /* UKUI主色 - 淡蓝色 */
    --ukui-primary-hover: #357ABD;
    --ukui-accent: #FF6B35;         /* 麒麟系统标识橙 */
    --ukui-success: #52C41A;
    --ukui-warning: #FAAD14;
    --ukui-error: #F5222D;
    --ukui-bg: #F5F7FA;             /* 浅灰背景 */
    --ukui-card-bg: #FFFFFF;
    --ukui-border: #E8EAED;
    --ukui-text-primary: #1F2937;
    --ukui-text-secondary: #6B7280;
    --ukui-shadow: 0 2px 8px rgba(0,0,0,0.08);
    --ukui-shadow-hover: 0 4px 16px rgba(74,144,226,0.15);
}

/* 全局字体 - 思源黑体/系统默认 */
body, .gradio-container {
    font-family: "Source Han Sans CN", "Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC", sans-serif !important;
}

/* 标题样式 - UKUI风格 */
.main-title {
    color: var(--ukui-primary) !important;
    font-size: 2.2rem !important;
    font-weight: 600 !important;
    text-align: center;
    margin-bottom: 0.5rem;
    letter-spacing: -0.5px;
}

.subtitle {
    color: var(--ukui-text-secondary) !important;
    text-align: center;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
    font-weight: 400;
}

/* 模块容器 - UKUI圆角卡片 */
.module-container {
    border: 1px solid var(--ukui-border);
    border-radius: 12px;
    padding: 1.25rem;
    background: var(--ukui-card-bg);
    box-shadow: var(--ukui-shadow);
    transition: all 0.3s ease;
}

.module-container:hover {
    box-shadow: var(--ukui-shadow-hover);
}

/* 按钮样式 - UKUI圆角按钮 */
.primary-btn, button[class*="primary"] {
    background: var(--ukui-primary) !important;
    border: none !important;
    color: white !important;
    font-weight: 500 !important;
    padding: 0.625rem 1.25rem !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 4px rgba(74,144,226,0.2) !important;
}

.primary-btn:hover, button[class*="primary"]:hover {
    background: var(--ukui-primary-hover) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 8px rgba(74,144,226,0.3) !important;
}

/* 输入框样式 - UKUI圆角输入框 */
input[type="text"], textarea, select {
    border: 1px solid var(--ukui-border) !important;
    border-radius: 8px !important;
    padding: 0.625rem 0.875rem !important;
    background: var(--ukui-card-bg) !important;
    transition: all 0.2s ease !important;
}

input[type="text"]:focus, textarea:focus, select:focus {
    border-color: var(--ukui-primary) !important;
    box-shadow: 0 0 0 3px rgba(74,144,226,0.1) !important;
    outline: none !important;
}

/* 标签页样式 - UKUI选中效果 */
.tab-nav button[aria-selected="true"] {
    color: var(--ukui-primary) !important;
    border-bottom: 2px solid var(--ukui-primary) !important;
    font-weight: 500 !important;
}

/* 日志样式 */
.log-success { color: var(--ukui-success); font-weight: 500; }
.log-error { color: var(--ukui-error); font-weight: 500; }
.log-info { color: var(--ukui-primary); font-weight: 500; }
.log-warning { color: var(--ukui-warning); font-weight: 500; }

/* 推理链高亮 - UKUI配色 */
.highlight-tool { 
    color: var(--ukui-accent) !important; 
    font-weight: 600 !important;
    background: rgba(255,107,53,0.1);
    padding: 2px 4px;
    border-radius: 4px;
}
.highlight-agent { 
    color: var(--ukui-primary) !important; 
    font-weight: 600 !important;
    background: rgba(74,144,226,0.1);
    padding: 2px 4px;
    border-radius: 4px;
}
.highlight-action { 
    color: var(--ukui-success) !important;
    font-weight: 500 !important;
}

/* 演示模式按钮 - UKUI风格 */
.demo-btn {
    background: rgba(74,144,226,0.08) !important;
    border: 1.5px solid var(--ukui-primary) !important;
    color: var(--ukui-primary) !important;
    font-weight: 500 !important;
    border-radius: 8px !important;
    transition: all 0.2s ease !important;
}

.demo-btn:hover {
    background: rgba(74,144,226,0.15) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 2px 8px rgba(74,144,226,0.2) !important;
}

/* 状态指示器 */
.status-online { color: var(--ukui-success); }
.status-offline { color: var(--ukui-error); }

/* 流程状态条 */
.process-status-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: rgba(74,144,226,0.05);
    border-radius: 8px;
    margin: 1rem 0;
    border-left: 3px solid var(--ukui-primary);
}

.process-step {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.375rem 0.75rem;
    border-radius: 6px;
    font-size: 0.875rem;
    transition: all 0.2s ease;
}

.process-step.active {
    background: var(--ukui-primary);
    color: white;
    font-weight: 500;
}

.process-step.completed {
    background: var(--ukui-success);
    color: white;
}

.process-step.pending {
    background: var(--ukui-bg);
    color: var(--ukui-text-secondary);
}

.process-arrow {
    color: var(--ukui-text-secondary);
    font-size: 0.875rem;
}

/* 推理链折叠面板 */
.reasoning-panel {
    border: 1px solid var(--ukui-border);
    border-radius: 8px;
    margin: 0.5rem 0;
    overflow: hidden;
    background: var(--ukui-card-bg);
}

.reasoning-panel-header {
    padding: 0.75rem 1rem;
    background: rgba(74,144,226,0.05);
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
    color: var(--ukui-primary);
    transition: background 0.2s ease;
}

.reasoning-panel-header:hover {
    background: rgba(74,144,226,0.1);
}

.reasoning-panel-content {
    padding: 1rem;
    border-top: 1px solid var(--ukui-border);
}

.reasoning-item {
    padding: 0.5rem 0;
    border-bottom: 1px solid rgba(232,234,237,0.5);
}

.reasoning-item:last-child {
    border-bottom: none;
}

/* 任务结果总结卡片 */
.result-summary-card {
    border: 1px solid var(--ukui-border);
    border-radius: 12px;
    padding: 1.25rem;
    background: linear-gradient(135deg, rgba(74,144,226,0.05) 0%, rgba(255,255,255,1) 100%);
    margin: 1rem 0;
    box-shadow: var(--ukui-shadow);
}

.result-summary-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--ukui-primary);
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.result-summary-content {
    color: var(--ukui-text-primary);
    line-height: 1.6;
    margin-bottom: 0.75rem;
}

.result-screenshots {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-top: 0.75rem;
}

.result-screenshot-item {
    border: 1px solid var(--ukui-border);
    border-radius: 6px;
    overflow: hidden;
    width: 120px;
    height: 80px;
    object-fit: cover;
    cursor: pointer;
    transition: transform 0.2s ease;
}

.result-screenshot-item:hover {
    transform: scale(1.05);
    box-shadow: var(--ukui-shadow);
}

/* Loading动画 */
.loading-spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(74,144,226,0.2);
    border-top-color: var(--ukui-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* 提示信息 */
.input-hint {
    font-size: 0.75rem;
    color: var(--ukui-text-secondary);
    margin-top: 0.25rem;
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.input-hint-icon {
    color: var(--ukui-primary);
    cursor: help;
}

/* 错误提示 */
.error-hint {
    color: var(--ukui-error);
    font-size: 0.875rem;
    margin-top: 0.5rem;
    padding: 0.5rem;
    background: rgba(245,34,45,0.1);
    border-radius: 6px;
    border-left: 3px solid var(--ukui-error);
}

/* 响应式布局 */
@media (max-width: 768px) {
    .main-title {
        font-size: 1.75rem !important;
    }
    
    .process-status-bar {
        flex-direction: column;
        align-items: flex-start;
    }
}
"""

# ============================================================
# 工具函数
# ============================================================

def add_log(message: str, level: str = "info"):
    """添加日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] [{level.upper()}] {message}"
    execution_logs.append(log_entry)
    # 保留最近100条日志
    if len(execution_logs) > 100:
        execution_logs.pop(0)
    return log_entry

def get_logs() -> str:
    """获取所有日志"""
    return "\n".join(execution_logs[-50:])  # 返回最近50条

def capture_screenshot(prefix: str = "screenshot") -> Optional[str]:
    """截取屏幕"""
    timestamp = int(time.time())
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"{prefix}_{timestamp}.png")
    
    try:
        subprocess.run(["scrot", screenshot_path], check=True, capture_output=True)
        return screenshot_path
    except:
        pass
    
    try:
        subprocess.run(["gnome-screenshot", "-f", screenshot_path], check=True, capture_output=True)
        return screenshot_path
    except:
        pass
    
    return None

def format_reasoning_chain(reasoning: dict) -> str:
    """格式化推理链为结构化HTML（UKUI风格折叠面板）"""
    if not reasoning:
        return '<div class="reasoning-panel"><div class="reasoning-panel-content"><p style="color: var(--ukui-text-secondary);">等待生成推理链...</p></div></div>'
    
    import re
    html_parts = []
    
    # 任务理解面板
    thought_chain = reasoning.get("thought_chain", {})
    if thought_chain:
        html_parts.append('<div class="reasoning-panel">')
        html_parts.append('<div class="reasoning-panel-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display===\'none\'?\'\':\'none\'">')
        html_parts.append('<span>🧠 任务理解与分解</span>')
        html_parts.append('<span>▼</span>')
        html_parts.append('</div>')
        html_parts.append('<div class="reasoning-panel-content">')
        
        # 任务理解
        task_understanding = thought_chain.get("task_understanding", "")
        if task_understanding:
            html_parts.append(f'<div class="reasoning-item"><strong>任务理解：</strong><span class="highlight-action">{task_understanding}</span></div>')
        
        # 任务分解
        task_decomposition = thought_chain.get("task_decomposition", "")
        if task_decomposition:
            html_parts.append(f'<div class="reasoning-item"><strong>任务分解：</strong>{task_decomposition}</div>')
        
        # 智能体选择
        agent_selection = thought_chain.get("agent_selection", [])
        if agent_selection:
            agents_html = []
            for agent_info in agent_selection:
                agent_name = agent_info.get("agent", "")
                reason = agent_info.get("reason", "")
                agents_html.append(f'<span class="highlight-agent">{agent_name}</span>（{reason}）')
            html_parts.append(f'<div class="reasoning-item"><strong>智能体选择：</strong>{" → ".join(agents_html)}</div>')
        
        # 风险评估
        risk_assessment = thought_chain.get("risk_assessment", "")
        if risk_assessment:
            risk_color = "var(--ukui-success)" if "无" in risk_assessment or "低" in risk_assessment else "var(--ukui-warning)"
            html_parts.append(f'<div class="reasoning-item"><strong>风险评估：</strong><span style="color: {risk_color};">{risk_assessment}</span></div>')
        
        html_parts.append('</div></div>')
    
    # 执行计划面板
    execution_plan = reasoning.get("execution_plan", [])
    if execution_plan:
        html_parts.append('<div class="reasoning-panel">')
        html_parts.append('<div class="reasoning-panel-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display===\'none\'?\'\':\'none\'">')
        html_parts.append('<span>📋 执行计划</span>')
        html_parts.append('<span>▼</span>')
        html_parts.append('</div>')
        html_parts.append('<div class="reasoning-panel-content">')
        
        for step in execution_plan:
            step_num = step.get("step", 0)
            action = step.get("action", "")
            agent = step.get("agent", "")
            html_parts.append(
                f'<div class="reasoning-item">'
                f'<strong>步骤 {step_num}：</strong>'
                f'<span class="highlight-action">{action}</span> '
                f'（<span class="highlight-agent">{agent}</span>）'
                f'</div>'
            )
        
        html_parts.append('</div></div>')
    
    # 里程碑标记
    milestones = reasoning.get("milestone_markers", [])
    if milestones:
        html_parts.append('<div class="reasoning-panel">')
        html_parts.append('<div class="reasoning-panel-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display===\'none\'?\'\':\'none\'">')
        html_parts.append('<span>🎯 里程碑标记</span>')
        html_parts.append('<span>▼</span>')
        html_parts.append('</div>')
        html_parts.append('<div class="reasoning-panel-content">')
        for milestone in milestones:
            html_parts.append(f'<div class="reasoning-item">✓ {milestone}</div>')
        html_parts.append('</div></div>')
    
    # 如果没有内容，显示原始JSON（格式化）
    if not html_parts:
        json_str = json.dumps(reasoning, indent=2, ensure_ascii=False)
        # 高亮关键字段
        json_str = re.sub(
            r'"(.*?_agent\.[a-z_]+)"',
            r'<span class="highlight-tool">"\1"</span>',
            json_str
        )
        json_str = re.sub(
            r'"(FileAgent|SettingsAgent|NetworkAgent|AppAgent|MonitorAgent|MediaAgent)"',
            r'<span class="highlight-agent">"\1"</span>',
            json_str
        )
        html_parts.append(f'<div class="reasoning-panel"><div class="reasoning-panel-content"><pre style="margin:0; white-space: pre-wrap;">{json_str}</pre></div></div>')
    
    return "".join(html_parts)

def get_history_tasks(use_memory: bool = True) -> List[str]:
    """获取历史任务列表"""
    # 如果记忆模块不可用，无论是否勾选都显示不可用
    if not HAS_MEMORY:
        return ["（记忆模块不可用）"]
    
    # 如果记忆模块可用但未启用，显示已禁用
    if not use_memory:
        return ["（记忆模块已禁用）"]
    
    # 如果记忆模块可用且已启用，返回历史任务列表
    try:
        trajectories = list_trajectories(limit=20)
        tasks = [t.get("task", "未知任务") for t in trajectories if t.get("task")]
        return list(set(tasks))[:10] if tasks else ["（无历史任务）"]
    except Exception as e:
        print(f"[WARNING] 获取历史任务失败: {e}")
        return ["（获取失败）"]

def get_screenshots() -> List[str]:
    """获取截图列表"""
    screenshots = []
    if os.path.exists(SCREENSHOT_DIR):
        for f in os.listdir(SCREENSHOT_DIR):
            if f.endswith(('.png', '.jpg', '.jpeg')):
                screenshots.append(os.path.join(SCREENSHOT_DIR, f))
    screenshots.sort(key=os.path.getmtime, reverse=True)
    return screenshots[:10]

def generate_process_status_bar(steps: List[str], current_step: int = 0) -> str:
    """生成流程状态条HTML"""
    html_parts = ['<div class="process-status-bar">']
    for i, step in enumerate(steps):
        if i < current_step:
            status_class = "completed"
            icon = "✓"
        elif i == current_step:
            status_class = "active"
            icon = "⟳"
        else:
            status_class = "pending"
            icon = "○"
        
        html_parts.append(
            f'<div class="process-step {status_class}">'
            f'<span>{icon}</span>'
            f'<span>{step}</span>'
            f'</div>'
        )
        
        if i < len(steps) - 1:
            html_parts.append('<span class="process-arrow">→</span>')
    
    html_parts.append('</div>')
    return "".join(html_parts)

def generate_result_summary(task: str, result: str, screenshots: List[str] = None) -> str:
    """生成任务结果总结卡片HTML"""
    if not screenshots:
        screenshots = []
    
    html_parts = ['<div class="result-summary-card">']
    html_parts.append('<div class="result-summary-title">')
    html_parts.append('<span>✅</span>')
    html_parts.append('<span>任务执行结果总结</span>')
    html_parts.append('</div>')
    
    html_parts.append('<div class="result-summary-content">')
    html_parts.append(f'<p><strong>任务：</strong>{task}</p>')
    html_parts.append(f'<p><strong>结果：</strong>{result}</p>')
    html_parts.append('</div>')
    
    if screenshots:
        html_parts.append('<div class="result-screenshots">')
        for screenshot in screenshots[:6]:  # 最多显示6张
            if os.path.exists(screenshot):
                html_parts.append(
                    f'<img src="file/{screenshot}" class="result-screenshot-item" '
                    f'onclick="window.open(this.src.replace(\'file/\', \'\'), \'_blank\')" '
                    f'alt="执行截图" />'
                )
        html_parts.append('</div>')
    
    html_parts.append('</div>')
    return "".join(html_parts)

# ============================================================
# 核心功能函数
# ============================================================

def execute_reasoning_plan(reasoning: dict) -> List[str]:
    """
    根据推理链的执行计划调用智能体工具
    
    Args:
        reasoning: 推理链字典
        
    Returns:
        执行结果列表
    """
    results = []
    execution_plan = reasoning.get("execution_plan", [])
    
    if not execution_plan:
        return results
    
    for step in execution_plan:
        step_num = step.get("step", 0)
        action = step.get("action", "")
        agent = step.get("agent", "")
        tool = step.get("tool", "")
        
        add_log(f"执行步骤 {step_num}: {action} (Agent: {agent}, Tool: {tool})", "info")
        
        try:
            # 根据agent和tool调用相应的智能体方法
            if agent == "FileAgent":
                if tool == "search_file":
                    path = step.get("parameters", {}).get("path", os.path.expanduser("~"))
                    keyword = step.get("parameters", {}).get("keyword", "")
                    result = file_agent.search_file(path, keyword, recursive=True)
                    results.append(f"FileAgent: {result.get('msg', '执行完成')}")
                elif tool == "move_to_trash":
                    file_path = step.get("parameters", {}).get("file_path", "")
                    if file_path:
                        result = file_agent.move_to_trash(file_path)
                        results.append(f"FileAgent: {result.get('msg', '执行完成')}")
                elif tool == "batch_rename":
                    results.append(f"FileAgent: 批量重命名功能已准备")
                    
            elif agent == "SettingsAgent":
                if tool == "set_wallpaper":
                    image_path = step.get("parameters", {}).get("image_path", "")
                    if image_path:
                        result = settings_agent.set_wallpaper(image_path)
                        results.append(f"SettingsAgent: {result.get('msg', '执行完成')}")
                elif tool == "adjust_volume":
                    volume = step.get("parameters", {}).get("volume", 50)
                    result = settings_agent.adjust_volume(volume)
                    results.append(f"SettingsAgent: {result.get('msg', '执行完成')}")
                elif tool == "bluetooth_manage":
                    action_type = step.get("parameters", {}).get("action", "status")
                    result = settings_agent.bluetooth_manage(action_type)
                    results.append(f"SettingsAgent: {result.get('msg', '执行完成')}")
                    
            elif agent == "NetworkAgent":
                if tool == "scan_wifi":
                    result = network_agent.scan_wifi()
                    results.append(f"NetworkAgent: {result.get('msg', '执行完成')}")
                elif tool == "connect_wifi":
                    ssid = step.get("parameters", {}).get("ssid", "")
                    password = step.get("parameters", {}).get("password", "")
                    result = network_agent.connect_wifi(ssid, password)
                    results.append(f"NetworkAgent: {result.get('msg', '执行完成')}")
                elif tool == "set_proxy":
                    proxy_host = step.get("parameters", {}).get("host", "")
                    proxy_port = step.get("parameters", {}).get("port", "")
                    result = network_agent.set_proxy(proxy_host, proxy_port)
                    results.append(f"NetworkAgent: {result.get('msg', '执行完成')}")
                elif tool == "speed_test":
                    result = network_agent.speed_test()
                    results.append(f"NetworkAgent: {result.get('msg', '执行完成')}")
                elif tool == "get_network_status":
                    result = network_agent.get_network_status()
                    results.append(f"NetworkAgent: {result.get('msg', '执行完成')}")
                    
            elif agent == "AppAgent":
                if tool == "launch_app":
                    app_name = step.get("parameters", {}).get("app_name", "")
                    if app_name:
                        result = app_agent.launch_app(app_name)
                        results.append(f"AppAgent: {result.get('msg', '执行完成')}")
                elif tool == "close_app":
                    app_name = step.get("parameters", {}).get("app_name", "")
                    if app_name:
                        result = app_agent.close_app(app_name)
                        results.append(f"AppAgent: {result.get('msg', '执行完成')}")
                elif tool == "app_quick_operation":
                    command = step.get("parameters", {}).get("command", "")
                    result = app_agent.app_quick_operation(command)
                    results.append(f"AppAgent: {result.get('msg', '执行完成')}")
                    
            elif agent == "MonitorAgent" and HAS_MONITOR_AGENT:
                if tool == "get_system_status":
                    result = monitor_agent.get_system_status()
                    if result["status"] == "success":
                        data = result["data"]
                        cpu_info = data.get("cpu", {})
                        memory_info = data.get("memory", {})
                        disk_info = data.get("disk", {})
                        # 返回详细的系统状态信息
                        status_detail = f"CPU: {cpu_info.get('percent', 0):.1f}% ({cpu_info.get('status', 'N/A')}), "
                        status_detail += f"内存: {memory_info.get('percent', 0):.1f}% ({memory_info.get('status', 'N/A')}), "
                        status_detail += f"磁盘: {disk_info.get('percent', 0):.1f}% ({disk_info.get('status', 'N/A')})"
                        results.append(f"MonitorAgent: {result.get('msg', '执行完成')} - {status_detail}")
                    else:
                        results.append(f"MonitorAgent: {result.get('msg', '执行失败')}")
                elif tool == "clean_background_process" or tool == "clean_processes":
                    # 支持两种工具名称：clean_background_process 和 clean_processes
                    process_name = step.get("parameters", {}).get("process_name")
                    if not process_name:
                        # 如果参数是 process_names（列表），取第一个
                        process_names = step.get("parameters", {}).get("process_names", [])
                        process_name = process_names[0] if process_names else None
                    result = monitor_agent.clean_background_process(process_name)
                    if result["status"] == "success":
                        cleaned_count = result.get("data", {}).get("cleaned_count", 0)
                        results.append(f"MonitorAgent: {result.get('msg', '执行完成')} (已清理 {cleaned_count} 个进程)")
                    else:
                        results.append(f"MonitorAgent: {result.get('msg', '执行失败')}")
                    
            elif agent == "MediaAgent" and HAS_MEDIA_AGENT:
                if tool == "play_media":
                    media_path = step.get("parameters", {}).get("media_path", "")
                    if media_path:
                        result = media_agent.play_media(media_path)
                        results.append(f"MediaAgent: {result.get('msg', '执行完成')}")
                elif tool == "control_media":
                    action = step.get("parameters", {}).get("action", "pause")
                    result = media_agent.control_media(action)
                    results.append(f"MediaAgent: {result.get('msg', '执行完成')}")
            else:
                results.append(f"{agent}: 步骤已记录 - {action}")
                
        except Exception as e:
            error_msg = f"{agent}执行失败: {str(e)}"
            add_log(error_msg, "error")
            results.append(error_msg)
    
    return results

def execute_task(task: str, use_memory: bool = True, confirm: bool = False) -> Tuple[str, str, str, str, List[str]]:
    """
    执行用户任务（集成System-2推理）
    
    Args:
        task: 任务指令
        use_memory: 是否使用记忆模块
        confirm: 用户确认（权限控制）
    
    Returns:
        (流程状态条, 推理链, 执行结果, 结果总结, 截图列表)
    """
    # 权限检查（演示模式）
    if REQUIRE_CONFIRMATION and not confirm:
        add_log("⚠️ 需要用户确认才能执行", "warning")
        process_steps = ["生成推理链", "调用智能体", "任务执行"]
        process_status = generate_process_status_bar(process_steps, 0)
        reasoning_html = '<div class="reasoning-panel"><div class="reasoning-panel-content"><p style="color: var(--ukui-text-secondary);">等待用户确认...</p></div></div>'
        result_text = "⚠️ 请在确认框中勾选「我已确认」后再执行"
        result_summary = ""
        return process_status, reasoning_html, result_text, result_summary, []
    
    add_log(f"收到任务: {task}", "info")
    
    reasoning = None
    results = []
    screenshots = []
    use_fallback = False
    
    # Step 1: 记忆检索（如果启用）
    reused_reasoning = None
    if use_memory and HAS_MEMORY:
        try:
            add_log("🔍 检索相似任务...", "info")
            similar_traj = retrieve_similar_trajectory(task, threshold=60, verbose=False)
            if similar_traj:
                reused_reasoning = similar_traj.get("reasoning_chain")
                add_log(f"✓ 找到相似任务，复用推理链", "success")
        except Exception as e:
            add_log(f"记忆检索失败: {str(e)}", "warning")
    else:
        add_log("💡 记忆模块已禁用，将直接使用UITARS推理", "info")
    
    # Step 2: 生成推理链（使用System-2或复用记忆）
    if reused_reasoning:
        reasoning = reused_reasoning
        add_log("✓ 使用记忆中的推理链", "success")
    elif HAS_SYSTEM2:
        try:
            add_log("🧠 使用uitars生成推理链...", "info")
            process_steps = ["生成推理链", "调用智能体", "任务执行"]
            process_status = generate_process_status_bar(process_steps, 0)
            
            # 命令行监控：显示推理开始
            print("\n" + "="*70)
            print("🧠 UITARS推理链生成")
            print("="*70)
            print(f"📝 用户任务: {task}")
            print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("-"*70)
            
            # 调用System-2推理（启用verbose模式以便命令行输出）
            reasoning = generate_master_reasoning(task, max_retries=3, verbose=True)
            
            # 命令行监控：显示推理结果
            if reasoning and not reasoning.get("_is_fallback"):
                add_log("✓ 推理链生成成功", "success")
                print("\n" + "="*70)
                print("✅ 推理链生成成功")
                print("="*70)
                
                # 显示推理链摘要
                thought_chain = reasoning.get("thought_chain", {})
                print(f"📋 任务理解: {thought_chain.get('task_understanding', 'N/A')}")
                print(f"🔧 任务分解: {thought_chain.get('task_decomposition', 'N/A')}")
                
                agent_selection = thought_chain.get("agent_selection", [])
                if agent_selection:
                    print(f"🤖 智能体选择:")
                    for agent_info in agent_selection:
                        if isinstance(agent_info, dict):
                            print(f"   - {agent_info.get('agent', 'Unknown')}: {agent_info.get('reason', 'N/A')}")
                        else:
                            print(f"   - {agent_info}")
                
                print(f"⚠️  风险评估: {thought_chain.get('risk_assessment', 'N/A')}")
                print(f"🔄 回退方案: {thought_chain.get('fallback_plan', 'N/A')}")
                
                execution_plan = reasoning.get("execution_plan", [])
                if execution_plan:
                    print(f"\n📊 执行计划 ({len(execution_plan)} 步):")
                    for step in execution_plan:
                        step_num = step.get("step", 0)
                        action = step.get("action", "")
                        agent = step.get("agent", "")
                        tool = step.get("tool", "")
                        print(f"   {step_num}. [{agent}] {action} (工具: {tool})")
                
                print("="*70 + "\n")
            else:
                add_log("⚠️ 推理链生成失败，使用降级策略", "warning")
                use_fallback = True
                print("\n" + "="*70)
                print("⚠️  推理链生成失败，使用降级策略（关键词匹配）")
                print("="*70 + "\n")
        except Exception as e:
            add_log(f"推理链生成异常: {str(e)}", "error")
            use_fallback = True
            print("\n" + "="*70)
            print(f"❌ 推理链生成异常: {str(e)}")
            print("="*70 + "\n")
    
    # Step 3: 如果推理失败，使用关键词匹配降级策略
    if not reasoning or use_fallback:
        add_log("⚠️ 使用关键词匹配模式", "warning")
        reasoning = {
            "thought_chain": {
                "task_understanding": task,
                "task_decomposition": "",
                "agent_selection": [],
                "risk_assessment": "无明显风险",
                "fallback_plan": "重试或手动操作"
            },
            "execution_plan": [],
            "milestone_markers": []
        }
        use_fallback = True
    
    # 确保reasoning字典有必要的键
    if not reasoning:
        reasoning = {
            "thought_chain": {
                "task_understanding": task,
                "task_decomposition": "",
                "agent_selection": [],
                "risk_assessment": "无明显风险",
                "fallback_plan": "重试或手动操作"
            },
            "execution_plan": [],
            "milestone_markers": []
        }
    
    if "execution_plan" not in reasoning:
        reasoning["execution_plan"] = []
    if "thought_chain" not in reasoning:
        reasoning["thought_chain"] = {
            "task_understanding": task,
            "task_decomposition": "",
            "agent_selection": [],
            "risk_assessment": "无明显风险",
            "fallback_plan": "重试或手动操作"
        }
    if "agent_selection" not in reasoning["thought_chain"]:
        reasoning["thought_chain"]["agent_selection"] = []
    
    # Step 4: 执行推理链计划
    if not use_fallback and reasoning.get("execution_plan"):
        # 使用推理链的执行计划
        add_log("📋 执行推理链计划...", "info")
        process_steps = ["生成推理链", "调用智能体", "任务执行"]
        process_status = generate_process_status_bar(process_steps, 1)
        
        results = execute_reasoning_plan(reasoning)
        
        if not results:
            add_log("⚠️ 推理链执行计划为空，使用关键词匹配", "warning")
            use_fallback = True
    
    # Step 5: 降级策略 - 关键词匹配（如果推理链无效或执行计划为空）
    if use_fallback or not reasoning.get("execution_plan"):
        add_log("🔧 使用关键词匹配模式", "info")
    task_lower = task.lower()
    
    # 文件操作
    if any(kw in task_lower for kw in ["搜索", "查找", "文件", "目录"]):
        add_log("调用 FileAgent 处理文件操作", "info")
        reasoning["thought_chain"]["agent_selection"].append({"agent": "FileAgent", "reason": "文件操作"})
        
        # 提取路径和关键词
        path = os.path.expanduser("~/Downloads")
        keyword = ".png"
        if "下载" in task_lower:
            path = os.path.expanduser("~/Downloads")
        if "桌面" in task_lower:
            path = os.path.expanduser("~/Desktop")
        
        result = file_agent.search_file(path, keyword, recursive=True)
        results.append(f"FileAgent: {result['msg']}")
        
        reasoning["execution_plan"].append({
            "step": 1,
            "action": f"搜索 {path} 中的 {keyword} 文件",
            "agent": "FileAgent"
        })
    
    # 回收站操作
    if any(kw in task_lower for kw in ["回收站", "删除", "移动到垃圾"]):
        add_log("调用 FileAgent 移动文件到回收站", "info")
        reasoning["thought_chain"]["agent_selection"].append({"agent": "FileAgent", "reason": "文件删除"})
        results.append("FileAgent: 文件操作已准备")
    
    # 壁纸设置
    if any(kw in task_lower for kw in ["壁纸", "桌面背景"]):
        add_log("调用 SettingsAgent 设置壁纸", "info")
        reasoning["thought_chain"]["agent_selection"].append({"agent": "SettingsAgent", "reason": "系统设置"})
        results.append("SettingsAgent: 壁纸设置功能已准备")
        
        reasoning["execution_plan"].append({
            "step": len(reasoning["execution_plan"]) + 1,
            "action": "设置桌面壁纸",
            "agent": "SettingsAgent"
        })
    
    # 音量调整
    if any(kw in task_lower for kw in ["音量", "声音"]):
        add_log("调用 SettingsAgent 调整音量", "info")
        reasoning["thought_chain"]["agent_selection"].append({"agent": "SettingsAgent", "reason": "系统设置"})
        
        # 提取音量值
        import re
        vol_match = re.search(r'(\d+)', task)
        volume = int(vol_match.group(1)) if vol_match else 50
        
        result = settings_agent.adjust_volume(volume)
        results.append(f"SettingsAgent: {result['msg']}")
        
        reasoning["execution_plan"].append({
            "step": len(reasoning["execution_plan"]) + 1,
            "action": f"调整音量到 {volume}%",
            "agent": "SettingsAgent"
        })
    
    # WiFi 操作
    if any(kw in task_lower for kw in ["wifi", "网络", "连接"]):
        add_log("调用 NetworkAgent 处理网络操作", "info")
        reasoning["thought_chain"]["agent_selection"].append({"agent": "NetworkAgent", "reason": "网络设置"})
        
        result = network_agent.get_network_status()
        results.append(f"NetworkAgent: {result['msg']}")
        
        reasoning["execution_plan"].append({
            "step": len(reasoning["execution_plan"]) + 1,
            "action": "获取网络状态",
            "agent": "NetworkAgent"
        })
    
    # 代理设置
    if any(kw in task_lower for kw in ["代理", "proxy"]):
        add_log("调用 NetworkAgent 设置代理", "info")
        reasoning["thought_chain"]["agent_selection"].append({"agent": "NetworkAgent", "reason": "代理设置"})
        results.append("NetworkAgent: 代理设置功能已准备（需要确认）")
    
    # 应用操作
    if any(kw in task_lower for kw in ["启动", "打开", "运行"]):
        add_log("调用 AppAgent 启动应用", "info")
        reasoning["thought_chain"]["agent_selection"].append({"agent": "AppAgent", "reason": "应用管理"})
        
        # 提取应用名
        app_name = "firefox"  # 默认
        if "浏览器" in task_lower or "firefox" in task_lower:
            app_name = "firefox"
        elif "终端" in task_lower:
            app_name = "gnome-terminal"
        elif "文件" in task_lower:
            app_name = "nautilus"
        
        result = app_agent.launch_app(app_name)
        results.append(f"AppAgent: {result['msg']}")
        
        reasoning["execution_plan"].append({
            "step": len(reasoning["execution_plan"]) + 1,
            "action": f"启动 {app_name}",
            "agent": "AppAgent"
        })
    
    # 关闭应用
    if any(kw in task_lower for kw in ["关闭", "退出", "停止"]):
        add_log("调用 AppAgent 关闭应用", "info")
        reasoning["thought_chain"]["agent_selection"].append({"agent": "AppAgent", "reason": "应用管理"})
        results.append("AppAgent: 关闭应用功能已准备")
    
    # 系统监控
    if any(kw in task_lower for kw in ["监控", "系统状态", "cpu", "内存", "磁盘", "系统资源", "进程"]):
        if HAS_MONITOR_AGENT:
            add_log("调用 MonitorAgent 获取系统状态", "info")
            reasoning["thought_chain"]["agent_selection"].append({"agent": "MonitorAgent", "reason": "系统监控"})
            
            result = monitor_agent.get_system_status()
            if result["status"] == "success":
                data = result["data"]
                cpu_info = data.get("cpu", {})
                memory_info = data.get("memory", {})
                disk_info = data.get("disk", {})
                results.append(f"MonitorAgent: CPU使用率 {cpu_info.get('percent', 0):.1f}%, 内存使用率 {memory_info.get('percent', 0):.1f}%, 磁盘使用率 {disk_info.get('percent', 0):.1f}%")
            else:
                results.append(f"MonitorAgent: {result.get('msg', '获取系统状态失败')}")
            
            reasoning["execution_plan"].append({
                "step": len(reasoning.get("execution_plan", [])) + 1,
                "action": "获取系统状态",
                "agent": "MonitorAgent",
                "tool": "get_system_status"
            })
        else:
            results.append("MonitorAgent: 系统监控功能不可用")
    
    # 清理进程
    if any(kw in task_lower for kw in ["清理进程", "清理后台", "结束进程", "kill"]):
        if HAS_MONITOR_AGENT:
            add_log("调用 MonitorAgent 清理进程", "info")
            reasoning["thought_chain"]["agent_selection"].append({"agent": "MonitorAgent", "reason": "进程管理"})
            
            # 提取进程名（如果有）
            process_name = None
            import re
            # 尝试从任务中提取进程名
            process_match = re.search(r'(清理|结束|kill)\s+(\w+)', task_lower)
            if process_match:
                process_name = process_match.group(2)
            
            result = monitor_agent.clean_background_process(process_name)
            results.append(f"MonitorAgent: {result.get('msg', '清理完成')}")
            
            reasoning["execution_plan"].append({
                "step": len(reasoning.get("execution_plan", [])) + 1,
                "action": f"清理进程{' ' + process_name if process_name else ''}",
                "agent": "MonitorAgent",
                "tool": "clean_background_process",
                "parameters": {"process_name": process_name} if process_name else {}
            })
        else:
            results.append("MonitorAgent: 进程清理功能不可用")
    
    # 生成任务分解描述
    if reasoning.get("execution_plan"):
        steps = [f"{p['step']}. {p['action']}" for p in reasoning["execution_plan"]]
        if "thought_chain" not in reasoning:
            reasoning["thought_chain"] = {}
        reasoning["thought_chain"]["task_decomposition"] = "；".join(steps)
        if "milestone_markers" not in reasoning:
            reasoning["milestone_markers"] = []
        reasoning["milestone_markers"] = [f"step_{i+1}_complete" for i in range(len(steps))]
    else:
        if "thought_chain" not in reasoning:
            reasoning["thought_chain"] = {}
        reasoning["thought_chain"]["task_decomposition"] = "任务分析中，请提供更具体的指令"
    
    # Step 6: 截图
    screenshot = capture_screenshot("task_result")
    if screenshot:
        screenshots.append(screenshot)
        add_log(f"截图已保存: {screenshot}", "info")
    
    # Step 7: 保存到记忆模块（如果启用且推理链有效）
    if use_memory and HAS_MEMORY and reasoning and not use_fallback:
        try:
            add_log("💾 保存执行轨迹到记忆模块...", "info")
            save_trajectory(
                task=task,
                reasoning_chain=reasoning,
                execution_result="\n".join(results) if results else "执行完成",
                screenshot_paths=screenshots if screenshots else None,
                success=True
            )
            add_log("✓ 轨迹已保存", "success")
        except Exception as e:
            add_log(f"保存轨迹失败: {str(e)}", "warning")
            print(f"[ERROR] 保存轨迹失败: {e}")
    
    add_log("任务执行完成", "success")
    
    # Step 8: 生成流程状态条
    process_steps = ["生成推理链", "调用智能体", "任务执行"]
    current_step = 2  # 已完成
    process_status = generate_process_status_bar(process_steps, current_step)
    
    # Step 9: 格式化输出
    reasoning_html = format_reasoning_chain(reasoning)
    result_text = "\n".join(results) if results else "任务已分析，等待执行具体操作"
    
    # Step 10: 生成结果总结
    result_summary = generate_result_summary(task, result_text, screenshots)
    
    return process_status, reasoning_html, result_text, result_summary, screenshots

def demo_task_1():
    """演示任务1：搜索png文件设为壁纸"""
    return "搜索下载目录的png文件并设置为壁纸"

def demo_task_2():
    """演示任务2：网络+应用组合"""
    return "获取当前网络状态，然后启动Firefox浏览器"

def demo_task_3():
    """演示任务3：音量调整"""
    return "把系统音量调到50%"

# ============================================================
# 智能体功能页面
# ============================================================

def file_search(path: str, keyword: str, recursive: bool) -> Tuple[list, str]:
    """文件搜索"""
    add_log(f"搜索文件: {path} / {keyword}", "info")
    result = file_agent.search_file(path, keyword, recursive)
    
    if result["status"] == "success":
        data = [[i["file_name"], i["file_path"], i["file_size"], i["modify_time"]] 
                for i in result["data"]]
        return data, f"✓ {result['msg']}"
    return [], f"✗ {result['msg']}"

def move_to_trash(file_path: str) -> str:
    """移动到回收站"""
    add_log(f"移动到回收站: {file_path}", "info")
    result = file_agent.move_to_trash(file_path)
    status = "✓" if result["status"] == "success" else "✗"
    return f"{status} {result['msg']}"

def change_wallpaper(wallpaper_path: str, scale: str) -> Tuple[str, Optional[str]]:
    """修改壁纸"""
    add_log(f"修改壁纸: {wallpaper_path}", "info")
    
    if not os.path.exists(wallpaper_path):
        return f"✗ 壁纸文件不存在: {wallpaper_path}", None
    
    result = settings_agent.change_wallpaper(wallpaper_path, scale)
    
    if result["status"] == "success":
        time.sleep(1)
        screenshot = capture_screenshot("wallpaper")
        return f"✓ {result['msg']}", screenshot
    return f"✗ {result['msg']}", None

def adjust_volume(volume: int, device: str) -> Tuple[str, Optional[str]]:
    """调整音量"""
    add_log(f"调整音量: {volume}%", "info")
    result = settings_agent.adjust_volume(volume, device)
    
    status = "✓" if result["status"] == "success" else "✗"
    return f"{status} {result['msg']}", None

def get_network_status() -> str:
    """获取网络状态"""
    add_log("获取网络状态", "info")
    result = network_agent.get_network_status()
    
    if result["status"] == "success":
        data = result["data"]
        status_text = f"""
**网络状态**
- WiFi 连接: {'✓ 已连接' if data.get('wifi_connected') else '✗ 未连接'}
- WiFi 名称: {data.get('wifi_ssid', 'N/A')}
- IP 地址: {data.get('ip_address', 'N/A')}
- 代理状态: {'✓ 已启用' if data.get('proxy_enabled') else '✗ 未启用'}
"""
        return status_text
    return f"✗ {result['msg']}"

def list_wifi() -> list:
    """列出 WiFi"""
    add_log("扫描 WiFi 网络", "info")
    result = network_agent.list_wifi()
    
    if result["status"] == "success":
        return [[w["ssid"], w["signal"], w["security"]] for w in result["data"]]
    return []

def launch_application(app_name: str) -> str:
    """启动应用"""
    add_log(f"启动应用: {app_name}", "info")
    result = app_agent.launch_app(app_name)
    
    status = "✓" if result["status"] == "success" else "✗"
    return f"{status} {result['msg']}"

def close_application(app_name: str) -> str:
    """关闭应用"""
    add_log(f"关闭应用: {app_name}", "info")
    result = app_agent.close_app(app_name)
    
    status = "✓" if result["status"] == "success" else "✗"
    return f"{status} {result['msg']}"

def list_running() -> list:
    """列出运行中应用"""
    result = app_agent.list_running_apps()
    
    if result["status"] == "success":
        return [[a.get("pid", ""), a.get("name", "")[:40], a.get("cmdline", "")] \
                for a in result["data"]["apps"]]
    else:
        return []

# ============================================================
# 构建 Gradio 界面
# ============================================================

def create_ui():
    """创建 Gradio 界面（UKUI风格）"""
    
    # 兼容旧版本Gradio：使用HTML组件注入CSS，而不是css参数
    with gr.Blocks() as demo:
        
        # 注入CSS样式（兼容旧版本Gradio）
        gr.HTML(f"""
        <style>
        {CUSTOM_CSS}
        </style>
        """)
        
        # 标题
        gr.HTML("""
        <div style="text-align: center; padding: 1rem 0;">
            <h1 class="main-title">🤖 Kylin-TARS 智能体管理系统</h1>
            <p class="subtitle">openKylin 桌面 GUI Agent - 多智能体协作平台</p>
        </div>
        """)
        
        with gr.Tabs():
            # ==================== 任务执行页 ====================
            with gr.Tab("🎯 任务执行", id="task"):
                with gr.Row():
                    # 左侧：指令输入
                    with gr.Column(scale=1):
                        gr.Markdown("### 📝 指令输入")
                        
                        task_input = gr.Textbox(
                            label="输入任务指令",
                            placeholder="例如：搜索下载目录的png文件并设置为壁纸",
                            lines=3
                        )
                        
                        # 输入提示
                        gr.HTML("""
                        <div class="input-hint">
                            <span class="input-hint-icon" title="请输入自然语言指令，如「将下载目录的tmp文件移动到回收站」「把系统音量调到50%」">ℹ️</span>
                            <span>提示：请输入自然语言指令，系统会自动分解任务并调用相应智能体</span>
                        </div>
                        """)
                        
                        with gr.Row():
                            history_dropdown = gr.Dropdown(
                                label="历史指令",
                                choices=get_history_tasks(False),  # 初始状态：记忆模块未启用
                                interactive=True
                            )
                            refresh_history_btn = gr.Button("🔄", scale=0)
                        
                        # 推理模式选择
                        gr.Markdown("### 🧠 推理模式")
                        use_memory_checkbox = gr.Checkbox(
                            label="💾 使用记忆模块（启用后将优先检索相似任务，否则直接使用UITARS推理）",
                            value=False,
                            info="关闭记忆模块时，将直接调用外部UITARS API进行推理"
                        )
                        
                        with gr.Row():
                            execute_btn = gr.Button("▶️ 执行任务", variant="primary")
                            clear_btn = gr.Button("🗑️ 清空")
                        
                        # 权限控制（演示模式）
                        if REQUIRE_CONFIRMATION:
                            confirm_checkbox = gr.Checkbox(
                                label="✓ 我已确认执行此操作",
                                value=False
                            )
                        else:
                            confirm_checkbox = gr.Checkbox(
                                label="✓ 我已确认执行此操作",
                                value=True,
                                visible=False
                            )
                        
                        gr.Markdown("### 🎬 演示模式")
                        with gr.Row():
                            demo_btn_1 = gr.Button("📁 搜索+壁纸", elem_classes=["demo-btn"], scale=1)
                            demo_btn_2 = gr.Button("🌐 网络+浏览器", elem_classes=["demo-btn"], scale=1)
                            demo_btn_3 = gr.Button("🔊 调整音量", elem_classes=["demo-btn"], scale=1)
                    
                    # 右侧：推理链
                    with gr.Column(scale=2):
                        gr.Markdown("### 🧠 推理链解析")
                        reasoning_output = gr.HTML(
                            value='<div class="reasoning-panel"><div class="reasoning-panel-content"><p style="color: var(--ukui-text-secondary);">等待执行任务...</p></div></div>',
                            label="推理链"
                        )
                        with gr.Row():
                            copy_btn = gr.Button("📋 复制推理链", scale=1)
                            expand_all_btn = gr.Button("📖 展开全部", scale=1)
                            collapse_all_btn = gr.Button("📕 折叠全部", scale=1)
                
                # 流程状态条
                process_status_bar = gr.HTML(
                    value=generate_process_status_bar(["生成推理链", "调用智能体", "任务执行"], 0),
                    label="执行流程"
                )
                
                # 任务结果总结卡片
                result_summary_card = gr.HTML(
                    value="",
                    label="任务结果总结"
                )
                
                with gr.Row():
                    # 执行结果
                    with gr.Column(scale=1):
                        gr.Markdown("### ✅ 执行结果")
                        result_output = gr.Textbox(
                            label="执行结果",
                            lines=6,
                            interactive=False
                        )
                    
                    # 截图展示
                    with gr.Column(scale=1):
                        gr.Markdown("### 📸 执行截图")
                        screenshot_gallery = gr.Gallery(
                            label="截图",
                            columns=2,
                            height=200
                        )
                
                # 实时日志
                gr.Markdown("### 📜 实时日志")
                log_output = gr.Textbox(
                    label="执行日志",
                    lines=8,
                    interactive=False,
                    value=get_logs()
                )
            
            # ==================== 子智能体监控页（整合所有智能体功能）====================
            with gr.Tab("🤖 子智能体监控", id="agents"):
                gr.Markdown("### 📊 统一智能体功能管理界面")
                
                # FileAgent
                with gr.Accordion("📁 FileAgent - 文件管理", open=False):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### 文件搜索")
                            file_path = gr.Textbox(label="搜索路径", value=os.path.expanduser("~/Downloads"))
                            file_keyword = gr.Textbox(label="关键词", value=".png")
                            file_recursive = gr.Checkbox(label="递归", value=True)
                            file_search_btn = gr.Button("🔍 搜索", variant="primary")
                            file_result = gr.Dataframe(headers=["文件名", "路径", "大小", "修改时间"], label="搜索结果")
                            file_msg = gr.Textbox(label="操作结果")
                            
                            gr.Markdown("#### 文件操作")
                            trash_path = gr.Textbox(label="文件路径", placeholder="输入要删除的文件路径")
                            trash_btn = gr.Button("🗑️ 移至回收站")
                            
                            gr.Markdown("#### 批量重命名")
                            batch_rename_dir = gr.Textbox(label="目录路径", placeholder="/path/to/directory")
                            batch_rename_rule = gr.Dropdown(label="重命名规则", choices=["prefix", "suffix", "number", "replace"], value="prefix")
                            batch_rename_prefix = gr.Textbox(label="前缀（可选）", value="")
                            batch_rename_suffix = gr.Textbox(label="后缀（可选）", value="")
                            batch_rename_start = gr.Number(label="起始编号", value=1)
                            batch_rename_btn = gr.Button("📝 批量重命名", variant="primary")
                            batch_rename_result = gr.Textbox(label="重命名结果")
                
                # SettingsAgent
                with gr.Accordion("⚙️ SettingsAgent - 系统设置", open=False):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### 壁纸设置")
                            wallpaper_path = gr.Textbox(label="壁纸路径", placeholder="/path/to/image.png")
                            wallpaper_scale = gr.Dropdown(label="缩放方式", choices=["zoom", "scaled", "centered", "stretched"], value="zoom")
                            wallpaper_btn = gr.Button("🖼️ 设置壁纸", variant="primary")
                            wallpaper_msg = gr.Textbox(label="结果")
                            wallpaper_preview = gr.Image(label="预览", height=150)
                        with gr.Column():
                            gr.Markdown("#### 音量设置")
                            volume_slider = gr.Slider(label="音量", minimum=0, maximum=100, value=50, step=1)
                            volume_device = gr.Textbox(label="设备", value="@DEFAULT_SINK@")
                            volume_btn = gr.Button("🔊 调整音量", variant="primary")
                            volume_msg = gr.Textbox(label="结果")
                            
                            gr.Markdown("#### 蓝牙管理")
                            bluetooth_action = gr.Radio(label="操作", choices=["enable", "disable", "status", "connect"], value="status", interactive=True)
                            bluetooth_device = gr.Textbox(label="设备名称（连接时填写）", placeholder="设备MAC地址或名称", interactive=True)
                            bluetooth_btn = gr.Button("📶 执行操作", variant="primary", interactive=True)
                            bluetooth_msg = gr.Textbox(label="操作结果", lines=5)

                # NetworkAgent
                with gr.Accordion("🌐 NetworkAgent - 网络管理", open=False):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### WiFi管理")
                            network_status_btn = gr.Button("🔄 刷新网络状态", variant="primary")
                            network_status = gr.Markdown("点击刷新查看网络状态")
                            wifi_scan_btn = gr.Button("📡 扫描 WiFi")
                            wifi_list = gr.Dataframe(headers=["名称", "信号", "安全性"], label="WiFi 列表")
                        with gr.Column():
                            gr.Markdown("#### 代理设置")
                            proxy_host = gr.Textbox(label="主机", placeholder="127.0.0.1")
                            proxy_port = gr.Number(label="端口", value=1080, precision=0, interactive=True)
                            proxy_type = gr.Dropdown(label="类型", choices=["http", "https", "socks"], value="http", interactive=True)
                            with gr.Row():
                                proxy_set_btn = gr.Button("✓ 设置代理")
                                proxy_clear_btn = gr.Button("✗ 清除代理")
                            proxy_msg = gr.Textbox(label="结果")
                            
                            gr.Markdown("#### 网络测速")
                            speed_test_btn = gr.Button("🚀 开始测速", variant="primary")
                            speed_test_result = gr.Markdown("点击「开始测速」测试网络速度")
                
                # AppAgent
                with gr.Accordion("📱 AppAgent - 应用管理", open=False):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### 应用启动/关闭")
                            app_name = gr.Textbox(label="应用名称", placeholder="firefox / 终端 / 文件管理器")
                            with gr.Row():
                                app_launch_btn = gr.Button("▶️ 启动", variant="primary")
                                app_close_btn = gr.Button("⏹️ 关闭")
                            app_msg = gr.Textbox(label="结果")
                            
                            gr.Markdown("#### 快捷启动")
                            with gr.Row():
                                app_quick_firefox = gr.Button("🦊 Firefox")
                                app_quick_file = gr.Button("📂 文件")
                                app_quick_terminal = gr.Button("💻 终端")
                        with gr.Column():
                            gr.Markdown("#### 运行中的应用")
                            running_refresh_btn = gr.Button("🔄 刷新列表")
                            running_apps = gr.Dataframe(headers=["PID", "应用", "cmdline"], label="运行中")
                
                # MonitorAgent
                with gr.Accordion("📊 MonitorAgent - 系统监控", open=False):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### 系统状态")
                            
                            # 状态显示 - 使用HTML显示 MonitorAgent 是否可用
                            status_html = ""
                            if HAS_MONITOR_AGENT:
                                status_html = '''
                                <div style="padding: 10px; background: #d4edda; border-radius: 5px; margin-bottom: 10px;">
                                    <h4 style="color: #155724; margin: 0;">✅ MonitorAgent 可用</h4>
                                    <p style="color: #0c5460; margin: 5px 0 0 0;">可以正常使用系统监控功能</p>
                                </div>
                                '''
                            else:
                                status_html = '''
                                <div style="padding: 10px; background: #f8d7da; border-radius: 5px; margin-bottom: 10px;">
                                    <h4 style="color: #721c24; margin: 0;">❌ MonitorAgent 不可用</h4>
                                    <p style="color: #856404; margin: 5px 0 0 0;">需要启动 MonitorAgent MCP 服务</p>
                                </div>
                                '''
                            
                            status_display = gr.HTML(value=status_html)
                            
                            # 按钮区域
                            with gr.Row():
                                monitor_start_btn = gr.Button(
                                    "🚀 启动 MonitorAgent 服务", 
                                    variant="primary", 
                                    visible=not HAS_MONITOR_AGENT
                                )
                                monitor_refresh_btn = gr.Button("🔄 刷新系统状态", variant="primary")
                            
                            monitor_start_output = gr.Textbox(
                                label="启动结果", 
                                lines=4,
                                visible=not HAS_MONITOR_AGENT,
                                placeholder="启动结果将显示在这里..."
                            )
                            
                            system_status_display = gr.HTML(
                                value='<div style="padding: 15px; border: 1px solid #dee2e6; border-radius: 5px; background: #f8f9fa;">'
                                    '<p style="color: #6c757d;">点击「刷新系统状态」按钮查看系统监控信息</p>'
                                    '</div>', 
                                label="系统监控信息"
                            )
                            
                            gr.Markdown("#### 进程清理")
                            process_clean_name = gr.Textbox(
                                label="进程名称（可选，留空清理所有冗余进程）", 
                                placeholder="例如：chrome, firefox, 或留空清理所有低占用进程"
                            )
                            process_clean_btn = gr.Button("🧹 清理选中进程", variant="primary")
                            process_clean_result = gr.Textbox(label="清理结果", lines=2)
                            
                        with gr.Column():
                            gr.Markdown("#### 实时监控设置")
                            monitor_auto_refresh = gr.Checkbox(
                                label="启用自动刷新", 
                                value=False,
                                interactive=HAS_MONITOR_AGENT
                            )
                            monitor_interval = gr.Slider(
                                minimum=1,
                                maximum=60,
                                value=5,
                                step=1,
                                label="刷新间隔（秒）",
                                interactive=HAS_MONITOR_AGENT
                            )
                
                # MediaAgent
                with gr.Accordion("🎵 MediaAgent - 媒体控制", open=False):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown("#### 媒体播放")
                            media_file_path = gr.Textbox(label="媒体文件路径", placeholder="/path/to/media/file.mp4 或 /path/to/audio/file.mp3")
                            media_play_btn = gr.Button("▶️ 播放", variant="primary")
                            media_play_result = gr.Textbox(label="播放结果")
                            
                            gr.Markdown("#### 播放控制")
                            with gr.Row():
                                media_pause_btn = gr.Button("⏸️ 暂停")
                                media_resume_btn = gr.Button("▶️ 继续")
                                media_stop_btn = gr.Button("⏹️ 停止")
                                media_fullscreen_btn = gr.Button("🔲 全屏")
                            media_control_result = gr.Textbox(label="控制结果")
                            
                            gr.Markdown("#### 截图播放帧")
                            media_capture_btn = gr.Button("📸 截图当前播放帧", variant="primary")
                            media_capture_display = gr.Image(label="截图预览")
                        with gr.Column():
                            gr.Markdown("#### 💡 提示")
                            gr.Markdown("""
                            **支持的媒体格式：**
                            - 视频：MP4, AVI, MKV, MOV
                            - 音频：MP3, WAV, OGG, FLAC
                            
                            **播放器：**
                            - 默认使用系统媒体播放器（totem）
                            """)
            
            # ==================== 记忆轨迹页 ====================
            with gr.Tab("🧠 记忆轨迹", id="memory"):
                with gr.Row():
                    # 左侧：历史与搜索
                    with gr.Column(scale=2):
                        gr.Markdown("### 📚 协作轨迹历史")
                        
                        memory_refresh_btn = gr.Button("🔄 刷新轨迹", variant="primary")
                        
                        if HAS_MEMORY:
                            try:
                                trajectories = list_trajectories(limit=10)
                                memory_data = [
                                    [t.get("task", "")[:50], 
                                     t.get("timestamp", ""),
                                     "✓" if t.get("success") else "✗",
                                     ", ".join(t.get("agents_involved", []))]
                                    for t in trajectories
                                ]
                            except:
                                memory_data = []
                        else:
                            memory_data = []
                        
                        memory_table = gr.Dataframe(
                            value=memory_data,
                            headers=["任务", "时间", "状态", "智能体"],
                            label="历史轨迹"
                        )
                        
                        gr.Markdown("### 🔍 搜索轨迹")
                        with gr.Row():
                            memory_search = gr.Textbox(label="搜索关键词", placeholder="输入任务关键词")
                            memory_search_mode = gr.Radio(
                                choices=["关键词检索", "语义检索"],
                                value="关键词检索",
                                label="检索模式"
                            )
                        memory_search_btn = gr.Button("🔍 搜索")
                    
                    # 右侧：可视化
                    with gr.Column(scale=1):
                        gr.Markdown("### 📊 轨迹可视化")
                        
                        with gr.Row():
                            viz_filter_agent = gr.Dropdown(
                                choices=["全部", "FileAgent", "SettingsAgent", "NetworkAgent", "AppAgent", "MonitorAgent", "MediaAgent"],
                                value="全部",
                                label="筛选智能体"
                            )
                            viz_time_range = gr.Number(
                                value=30,
                                label="时间范围（天）",
                                minimum=1,
                                maximum=365
                            )
                        
                        viz_layout = gr.Radio(
                            choices=["spring", "circular"],
                            value="spring",
                            label="布局算法"
                        )
                        
                        viz_generate_btn = gr.Button("🎨 生成可视化", variant="primary")
                        memory_visualization = gr.HTML(
                            value="<p>点击「生成可视化」查看轨迹关联图</p>",
                            label="轨迹关联图"
                        )
            
            # ==================== 更多功能页（包含协作日志和MCP配置）====================
            with gr.Tab("⚙️ 更多功能", id="more"):
                with gr.Accordion("📜 协作日志追溯", open=False):
                    with gr.Row():
                        with gr.Column(scale=2):
                            gr.Markdown("### 📋 日志查询")
                        
                        with gr.Row():
                            log_filter_agent = gr.Dropdown(
                                choices=["全部", "FileAgent", "SettingsAgent", "NetworkAgent", "AppAgent", "MonitorAgent", "MediaAgent"],
                                value="全部",
                                label="筛选智能体"
                            )
                            log_filter_status = gr.Dropdown(
                                choices=["全部", "success", "error", "pending"],
                                value="全部",
                                label="筛选状态"
                            )
                            log_filter_type = gr.Dropdown(
                                choices=["全部", "decision", "schedule", "execution", "broadcast"],
                                value="全部",
                                label="筛选类型"
                            )
                        
                        log_search_keyword = gr.Textbox(
                            label="搜索关键词",
                            placeholder="输入任务关键词或日志ID"
                        )
                        
                        log_query_btn = gr.Button("🔍 查询日志", variant="primary")
                        
                        log_table = gr.Dataframe(
                            headers=["日志ID", "类型", "任务", "智能体", "工具", "状态", "时间"],
                            label="日志列表",
                            interactive=False
                        )
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### 🔗 日志链追溯")
                        
                        log_id_input = gr.Textbox(
                            label="日志ID",
                            placeholder="输入日志ID查看完整链路"
                        )
                        log_chain_btn = gr.Button("🔗 查看日志链", variant="primary")
                        
                        log_chain_display = gr.HTML(
                            value="<p>输入日志ID查看关联的完整日志链</p>",
                            label="日志链"
                        )
                        
                        gr.Markdown("### 📊 日志统计")
                        log_stats_display = gr.HTML(
                            value="<p>点击查询查看统计信息</p>",
                            label="统计信息"
                        )
                        log_stats_btn = gr.Button("📊 查看统计")
                
                with gr.Accordion("⚙️ MCP配置管理", open=False):
                    gr.Markdown("### 🔐 智能体权限管理")
                    
                    with gr.Row():
                        with gr.Column(scale=2):
                            agent_permission_table = gr.Dataframe(
                                headers=["智能体", "当前权限", "操作"],
                                label="智能体权限列表",
                                interactive=False
                            )
                            
                            gr.Markdown("### 🔧 修改权限")
                            config_agent_name = gr.Dropdown(
                                choices=["FileAgent", "SettingsAgent", "NetworkAgent", "AppAgent", "MonitorAgent", "MediaAgent"],
                                label="选择智能体"
                            )
                            config_permission = gr.Radio(
                                choices=["admin", "normal", "readonly", "guest"],
                                value="normal",
                                label="权限级别"
                            )
                            config_save_btn = gr.Button("💾 保存权限", variant="primary")
                            config_save_result = gr.Textbox(label="保存结果")
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### 📦 配置备份")
                            config_backup_btn = gr.Button("💾 创建备份", variant="primary")
                            config_backup_result = gr.Textbox(label="备份结果")
                            
                            gr.Markdown("### 🔄 配置恢复")
                            config_backup_list = gr.Dropdown(
                                label="选择备份",
                                choices=[]
                            )
                            config_restore_btn = gr.Button("🔄 恢复配置", variant="primary")
                            config_restore_result = gr.Textbox(label="恢复结果")
                            
                            config_refresh_backups_btn = gr.Button("🔄 刷新备份列表")
                            
                            gr.Markdown("### 📋 权限说明")
                            gr.Markdown("""
                            - **admin**: 管理员权限，所有操作
                            - **normal**: 普通用户，正常操作
                            - **readonly**: 只读权限，仅查询
                            - **guest**: 访客权限，受限操作
                            """)
            
        
        # ==================== 事件绑定 ====================
        
        # 任务执行
        # 执行任务（带loading状态）
        def execute_with_loading(task, confirm, use_memory):
            """执行任务并显示loading状态"""
            if not task or not task.strip():
                return (
                    generate_process_status_bar(["生成推理链", "调用智能体", "任务执行"], 0),
                    '<div class="reasoning-panel"><div class="reasoning-panel-content"><p style="color: var(--ukui-error);">⚠️ 请输入任务指令</p></div></div>',
                    "",
                    "",
                    []
                )
            
            # 显示执行中状态
            process_status = generate_process_status_bar(["生成推理链", "调用智能体", "任务执行"], 1)
            mode_text = "记忆检索" if use_memory else "UITARS推理"
            reasoning_html = f'<div class="reasoning-panel"><div class="reasoning-panel-content"><p><span class="loading-spinner"></span> 正在{mode_text}...</p></div></div>'
            
            # 执行任务
            process_status_final, reasoning_html_final, result_text, result_summary, screenshots = execute_task(task, use_memory, confirm)
            
            return process_status_final, reasoning_html_final, result_text, result_summary, screenshots
        
        execute_btn.click(
            fn=execute_with_loading,
            inputs=[task_input, confirm_checkbox, use_memory_checkbox],
            outputs=[process_status_bar, reasoning_output, result_output, result_summary_card, screenshot_gallery]
        )
        
        # 历史指令选择
        history_dropdown.change(
            fn=lambda x: x if x and x != "（" else "",
            inputs=[history_dropdown],
            outputs=[task_input]
        )
        
        # 刷新历史（根据记忆模块状态）
        def refresh_history_with_memory_state(use_memory):
            return gr.update(choices=get_history_tasks(use_memory))
        
        refresh_history_btn.click(
            fn=refresh_history_with_memory_state,
            inputs=[use_memory_checkbox],
            outputs=[history_dropdown]
        )
        
        # 当记忆模块开关改变时，自动刷新历史指令列表
        use_memory_checkbox.change(
            fn=refresh_history_with_memory_state,
            inputs=[use_memory_checkbox],
            outputs=[history_dropdown]
        )
        
        # 清空
        def clear_all():
            return (
                "",
                generate_process_status_bar(["生成推理链", "调用智能体", "任务执行"], 0),
                '<div class="reasoning-panel"><div class="reasoning-panel-content"><p style="color: var(--ukui-text-secondary);">等待执行任务...</p></div></div>',
                "",
                "",
                []
            )
        
        clear_btn.click(
            fn=clear_all,
            outputs=[task_input, process_status_bar, reasoning_output, result_output, result_summary_card, screenshot_gallery]
        )
        
        # 展开/折叠推理链
        def expand_all_reasoning():
            return gr.update(value='<script>document.querySelectorAll(".reasoning-panel-content").forEach(el => el.style.display = "");</script>')
        
        def collapse_all_reasoning():
            return gr.update(value='<script>document.querySelectorAll(".reasoning-panel-content").forEach(el => el.style.display = "none");</script>')
        
        expand_all_btn.click(fn=expand_all_reasoning, outputs=[reasoning_output])
        collapse_all_btn.click(fn=collapse_all_reasoning, outputs=[reasoning_output])
        
        # 演示按钮
        demo_btn_1.click(fn=demo_task_1, outputs=[task_input])
        demo_btn_2.click(fn=demo_task_2, outputs=[task_input])
        demo_btn_3.click(fn=demo_task_3, outputs=[task_input])
        
        # 文件管理
        file_search_btn.click(
            fn=file_search,
            inputs=[file_path, file_keyword, file_recursive],
            outputs=[file_result, file_msg]
        )
        trash_btn.click(fn=move_to_trash, inputs=[trash_path], outputs=[file_msg])
        
        # 批量重命名
        def batch_rename_files(target_dir: str, rename_rule: str, prefix: str, suffix: str, start_number: int) -> str:
            add_log(f"批量重命名: {target_dir}", "info")
            if not target_dir or not os.path.exists(target_dir):
                return "✗ 目录不存在或路径无效"
            try:
                result = file_agent.batch_rename(
                    target_dir=target_dir,
                    rename_rule=rename_rule,
                    prefix=prefix if prefix else "",
                    suffix=suffix if suffix else "",
                    start_number=int(start_number) if start_number else 1
                )
                if result.get("status") == "success":
                    return f"✓ {result.get('msg', '批量重命名成功')}"
                else:
                    return f"✗ {result.get('msg', '批量重命名失败')}"
            except Exception as e:
                return f"✗ 错误: {e}"
        
        batch_rename_btn.click(
            fn=batch_rename_files,
            inputs=[batch_rename_dir, batch_rename_rule, batch_rename_prefix, batch_rename_suffix, batch_rename_start],
            outputs=[batch_rename_result]
        )
        
        # 系统设置
        wallpaper_btn.click(
            fn=change_wallpaper,
            inputs=[wallpaper_path, wallpaper_scale],
            outputs=[wallpaper_msg, wallpaper_preview]
        )
        volume_btn.click(
            fn=adjust_volume,
            inputs=[volume_slider, volume_device],
            outputs=[volume_msg, wallpaper_preview]
        )
        
        # 蓝牙管理
        def manage_bluetooth(action: str, device: str) -> str:
            add_log(f"蓝牙操作: {action}", "info")
            try:
                result = settings_agent.bluetooth_manage(action, device if device else None)
                if result.get("status") == "success":
                    return f"✓ {result.get('msg', '操作成功')}"
                else:
                    return f"✗ {result.get('msg', '操作失败')}"
            except Exception as e:
                return f"✗ 错误: {e}"
        
        bluetooth_btn.click(
            fn=manage_bluetooth,
            inputs=[bluetooth_action, bluetooth_device],
            outputs=[bluetooth_msg]
        )
        
        # 网络管理
        network_status_btn.click(fn=get_network_status, outputs=[network_status])
        wifi_scan_btn.click(fn=list_wifi, outputs=[wifi_list])
        
        # 网络测速
        def run_speed_test() -> str:
            add_log("开始网络测速", "info")
            try:
                result = network_agent.speed_test()
                if result.get("status") == "success":
                    data = reult.get("data", {})
                    download = data.get("download_mbps", 0)
                    upload = data.get("upload_mbps", 0)
                    ping = data.get("ping_ms", 0)
                    return f"""### 🚀 测速结果

- **下载速度**: {download:.2f} Mbps
- **上传速度**: {upload:.2f} Mbps  
- **延迟**: {ping:.2f} ms

{result.get('msg', '')}"""
                else:
                    return f"✗ {result.get('msg', '测速失败')}"
            except Exception as e:
                return f"✗ 错误: {e}"
        
        speed_test_btn.click(fn=run_speed_test, outputs=[speed_test_result])
        
        # 代理设置
        def set_proxy(proxy_host, proxy_port, proxy_type):
            proxy_addr = f"{proxy_type}://{proxy_host}:{proxy_port}"
            add_log(f"设置代理:{proxy_addr}", "info")
            try:
                if proxy_type == "http":
                    network_agent.set_proxy(http_proxy=proxy_addr)
                elif proxy_type == "https":
                    network_agent.set_proxy(https_proxy=proxy_addr)
                elif proxy_type == "socks":
                    network_agent.set_proxy(socks_proxy=proxy_addr)
                else:
                    network_agent.set_proxy(no_proxy=proxy_addr)
                return f"✓ 成功设置代理: {proxy_addr}"
            except Exception as e:
                return f"✗ 错误: {e}"

        proxy_set_btn.click(
            fn=set_proxy,
            inputs=[proxy_host, proxy_port, proxy_type],
            outputs=[proxy_msg]
        )

        # 清除代理
        def clear_proxy():
            add_log("清除代理", "info")
            try:
                network_agent.clear_proxy()
                return "✓ 已清除代理设置"
            except Exception as e:
                return f"✗ 错误: {e}"

        proxy_clear_btn.click(
            fn=clear_proxy,
            inputs=[],
            outputs=[proxy_msg]
        ) 

        # 应用管理
        app_launch_btn.click(
            fn=launch_application,
            inputs=[app_name],
            outputs=[app_msg]
        )
        app_close_btn.click(
            fn=lambda name: close_application(name) if name else "请输入应用名称",
            inputs=[app_name],
            outputs=[app_msg]
        )
        app_quick_firefox.click(fn=lambda: launch_application("firefox"), outputs=[app_msg])
        app_quick_file.click(fn=lambda: launch_application("nautilus"), outputs=[app_msg])
        app_quick_terminal.click(fn=lambda: launch_application("gnome-terminal"), outputs=[app_msg])
        running_refresh_btn.click(fn=list_running, outputs=[running_apps])
        
        # 记忆轨迹
        def refresh_memory_table():
            if not HAS_MEMORY:
                return []
            try:
                trajectories = list_trajectories(limit=10)
                return [
                    [t.get("task", "")[:50], 
                     t.get("timestamp", ""),
                     "✓" if t.get("success") else "✗",
                     ", ".join(t.get("agents_involved", []))]
                    for t in trajectories
                ]
            except:
                return []
        
        def search_memory(keyword: str, mode: str):
            if not HAS_MEMORY or not keyword:
                return []
            try:
                if mode == "语义检索":
                    results = semantic_retrieve(keyword, threshold=0.6, limit=10, verbose=False)
                    trajectories = [r[0] for r in results]
                else:
                    trajectories = search_trajectories(keyword=keyword, limit=10)
                
                return [
                    [t.get("task", "")[:50], 
                     t.get("timestamp", ""),
                     "✓" if t.get("success") else "✗",
                     ", ".join(t.get("agents_involved", []))]
                    for t in trajectories
                ]
            except:
                return []
        
        def generate_memory_visualization(agent_filter: str, time_days: int, layout: str):
            if not HAS_MEMORY:
                return "<p>记忆模块不可用</p>"
            try:
                filter_agent = None if agent_filter == "全部" else agent_filter
                html = generate_visualization_html(
                    filter_agent=filter_agent,
                    time_range_days=int(time_days) if time_days else 30,
                    layout=layout
                )
                return html
            except Exception as e:
                return f"<p>可视化生成失败: {e}</p>"
        
        memory_refresh_btn.click(fn=refresh_memory_table, outputs=[memory_table])
        memory_search_btn.click(fn=search_memory, inputs=[memory_search, memory_search_mode], outputs=[memory_table])
        viz_generate_btn.click(
            fn=generate_memory_visualization,
            inputs=[viz_filter_agent, viz_time_range, viz_layout],
            outputs=[memory_visualization]
        )
        
        # 协作日志
        def query_collaboration_logs(agent_filter: str, status_filter: str, type_filter: str, keyword: str):
            if not HAS_MEMORY:
                return []
            try:
                agent = None if agent_filter == "全部" else agent_filter
                status = None if status_filter == "全部" else status_filter
                log_type = None if type_filter == "全部" else type_filter
                
                logs = query_logs(
                    agent=agent,
                    status=status,
                    log_type=log_type,
                    task=keyword if keyword else None,
                    limit=50
                )
                
                return [
                    [
                        log.get("log_id", "")[:8],
                        log.get("log_type", ""),
                        log.get("task", "")[:30],
                        log.get("agent", ""),
                        log.get("tool", "")[:30] if log.get("tool") else "",
                        log.get("status", ""),
                        log.get("timestamp", "")[:19] if log.get("timestamp") else ""
                    ]
                    for log in logs
                ]
            except Exception as e:
                return [[f"查询失败: {e}", "", "", "", "", "", ""]]
        
        def display_log_chain(log_id: str):
            if not HAS_MEMORY or not log_id:
                return "<p>请输入日志ID</p>"
            try:
                chain = get_log_chain(log_id)
                if not chain:
                    return f"<p>未找到日志ID: {log_id}</p>"
                
                html = "<div style='padding: 10px;'><h3>日志链（按时间顺序）</h3><table border='1' style='border-collapse: collapse; width: 100%;'><tr><th>日志ID</th><th>类型</th><th>智能体</th><th>工具</th><th>状态</th><th>时间</th></tr>"
                for log in chain:
                    html += f"<tr><td>{log.get('log_id', '')[:8]}</td><td>{log.get('log_type', '')}</td><td>{log.get('agent', '')}</td><td>{log.get('tool', '')[:30]}</td><td>{log.get('status', '')}</td><td>{log.get('timestamp', '')[:19]}</td></tr>"
                html += "</table></div>"
                return html
            except Exception as e:
                return f"<p>查看日志链失败: {e}</p>"
        
        def display_log_statistics():
            if not HAS_MEMORY:
                return "<p>日志模块不可用</p>"
            try:
                stats = get_log_statistics()
                html = f"""
                <div style='padding: 10px;'>
                    <h3>日志统计</h3>
                    <ul>
                        <li>总日志数: {stats['total_logs']}</li>
                        <li>按类型: {stats['by_type']}</li>
                        <li>按状态: {stats['by_status']}</li>
                        <li>按智能体: {stats['by_agent']}</li>
                    </ul>
                </div>
                """
                return html
            except Exception as e:
                return f"<p>获取统计失败: {e}</p>"
        
        log_query_btn.click(
            fn=query_collaboration_logs,
            inputs=[log_filter_agent, log_filter_status, log_filter_type, log_search_keyword],
            outputs=[log_table]
        )
        log_chain_btn.click(fn=display_log_chain, inputs=[log_id_input], outputs=[log_chain_display])
        log_stats_btn.click(fn=display_log_statistics, outputs=[log_stats_display])
        
        # 系统监控
        def refresh_system_status():
            if not HAS_MONITOR_AGENT:
                return "<p>MonitorAgent不可用</p>"
            try:
                result = monitor_agent.get_system_status()
                if result["status"] == "success":
                    data = result["data"]
                    cpu_info = data.get("cpu", {})
                    memory_info = data.get("memory", {})
                    disk_info = data.get("disk", {})
                    top_processes = data.get("top_processes", [])
                    
                    cpu_percent = cpu_info.get("percent", 0)
                    memory_percent = memory_info.get("percent", 0)
                    memory_used_gb = memory_info.get("used_gb", 0)
                    memory_total_gb = memory_info.get("total_gb", 0)
                    disk_percent = disk_info.get("percent", 0)
                    disk_used_gb = disk_info.get("used_gb", 0)
                    disk_total_gb = disk_info.get("total_gb", 0)
                    
                    html = f"""
                    <div style='padding: 15px;'>
                        <h3>系统状态</h3>
                        <table border='1' style='border-collapse: collapse; width: 100%;'>
                            <tr><th>指标</th><th>值</th><th>百分比</th><th>状态</th></tr>
                            <tr>
                                <td>CPU使用率</td>
                                <td>{cpu_percent:.1f}% ({cpu_info.get('count', 'N/A')} 核心)</td>
                                <td><div style='background: #e0e0e0; width: 100px; height: 20px;'>
                                    <div style='background: #4CAF50; width: {cpu_percent}%; height: 100%;'></div>
                                </div></td>
                                <td>{cpu_info.get('status', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td>内存使用</td>
                                <td>{memory_used_gb:.2f}GB / {memory_total_gb:.2f}GB</td>
                                <td><div style='background: #e0e0e0; width: 100px; height: 20px;'>
                                    <div style='background: #2196F3; width: {memory_percent}%; height: 100%;'></div>
                                </div></td>
                                <td>{memory_info.get('status', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td>磁盘使用</td>
                                <td>{disk_used_gb:.2f}GB / {disk_total_gb:.2f}GB</td>
                                <td><div style='background: #e0e0e0; width: 100px; height: 20px;'>
                                    <div style='background: #FF9800; width: {disk_percent}%; height: 100%;'></div>
                                </div></td>
                                <td>{disk_info.get('status', 'N/A')}</td>
                            </tr>
                        </table>
                    """
                    
                    if top_processes:
                        html += "<h4>CPU占用前5进程：</h4><ul style='margin-top: 10px;'>"
                        for proc in top_processes[:5]:
                            name = proc.get('name', '未知进程')
                            pid = proc.get('pid', 'N/A')
                            cpu_percent = proc.get('cpu_percent', 0)
                            memory_percent = proc.get('memory_percent', 0)
                            html += f"<li><strong>{name}</strong> (PID: {pid}) - CPU: {cpu_percent:.1f}%, 内存: {memory_percent:.1f}%</li>"
                        html += "</ul>"
                    
                    html += "</div>"
                    return html
                else:
                    return f"<p>获取系统状态失败: {result.get('msg', '未知错误')}</p>"
            except Exception as e:
                return f"<p>获取系统状态失败: {e}</p>"
                
        def clean_background_process(process_name: str):
            if not HAS_MONITOR_AGENT:
                return "MonitorAgent不可用"
            try:
                result = monitor_agent.clean_background_process(process_name if process_name else None)
                return result.get("msg", "清理完成")
            except Exception as e:
                return f"清理失败: {e}"
        
        monitor_refresh_btn.click(fn=refresh_system_status, outputs=[system_status_display])
        process_clean_btn.click(fn=clean_background_process, inputs=[process_clean_name], outputs=[process_clean_result])

        # 媒体控制
        def play_media_file(media_path: str):
            if not HAS_MEDIA_AGENT:
                return "MediaAgent不可用", None
            try:
                result = media_agent.play_media(media_path)
                screenshot_path = result.get("screenshot_path")
                return result.get("msg", "播放失败"), screenshot_path if screenshot_path else None
            except Exception as e:
                return f"播放失败: {e}", None
        
        def media_control_action(action: str):
            if not HAS_MEDIA_AGENT:
                return f"MediaAgent不可用"
            try:
                result = media_agent.media_control(action)
                return result.get("msg", "操作失败")
            except Exception as e:
                return f"操作失败: {e}"
        
        def capture_media_frame():
            if not HAS_MEDIA_AGENT:
                return None
            try:
                result = media_agent.capture_media_frame()
                screenshot_path = result.get("screenshot_path")
                return screenshot_path if screenshot_path else None
            except Exception as e:
                return None
        
        media_play_btn.click(fn=play_media_file, inputs=[media_file_path], outputs=[media_play_result, media_capture_display])
        media_pause_btn.click(fn=lambda: media_control_action("pause"), outputs=[media_control_result])
        media_resume_btn.click(fn=lambda: media_control_action("play"), outputs=[media_control_result])
        media_stop_btn.click(fn=lambda: media_control_action("stop"), outputs=[media_control_result])
        media_fullscreen_btn.click(fn=lambda: media_control_action("fullscreen"), outputs=[media_control_result])
        media_capture_btn.click(fn=capture_media_frame, outputs=[media_capture_display])
        
        # MCP配置管理
        def load_agent_permissions():
            if not HAS_CONFIG_MANAGER:
                return []
            try:
                config_manager = get_config_manager()
                agents = ["FileAgent", "SettingsAgent", "NetworkAgent", "AppAgent", "MonitorAgent", "MediaAgent"]
                data = []
                for agent in agents:
                    permission = config_manager.get_agent_permission(agent)
                    data.append([agent, permission.value, "修改"])
                return data
            except Exception as e:
                return []
        
        def save_agent_permission(agent_name: str, permission: str):
            if not HAS_CONFIG_MANAGER:
                return "配置管理器不可用"
            try:
                config_manager = get_config_manager()
                permission_level = PermissionLevel(permission)
                config_manager.set_agent_permission(agent_name, permission_level)
                return f"✓ 已更新 {agent_name} 权限为 {permission}"
            except Exception as e:
                return f"保存失败: {e}"
        
        def create_config_backup():
            if not HAS_CONFIG_MANAGER:
                return "配置管理器不可用"
            try:
                config_manager = get_config_manager()
                backup_file = config_manager.backup_config()
                return f"✓ 备份已创建: {os.path.basename(backup_file)}"
            except Exception as e:
                return f"备份失败: {e}"
        
        def load_backup_list():
            if not HAS_CONFIG_MANAGER:
                return []
            try:
                config_manager = get_config_manager()
                backups = config_manager.list_backups()
                return [f"{b['file']} ({b['timestamp'][:19]})" for b in backups]
            except Exception as e:
                return []
        
        def restore_config_backup(backup_info: str):
            if not HAS_CONFIG_MANAGER or not backup_info:
                return "配置管理器不可用或未选择备份"
            try:
                config_manager = get_config_manager()
                backups = config_manager.list_backups()
                backup_file = None
                for b in backups:
                    if backup_info.startswith(b['file']):
                        backup_file = b['path']
                        break
                
                if backup_file and config_manager.restore_config(backup_file):
                    return f"✓ 配置已恢复: {os.path.basename(backup_file)}"
                else:
                    return "恢复失败: 未找到备份文件"
            except Exception as e:
                return f"恢复失败: {e}"
        
        config_save_btn.click(
            fn=save_agent_permission,
            inputs=[config_agent_name, config_permission],
            outputs=[config_save_result]
        )
        config_save_btn.click(
            fn=load_agent_permissions,
            outputs=[agent_permission_table]
        )
        config_backup_btn.click(fn=create_config_backup, outputs=[config_backup_result])
        config_refresh_backups_btn.click(fn=load_backup_list, outputs=[config_backup_list])
        config_restore_btn.click(fn=restore_config_backup, inputs=[config_backup_list], outputs=[config_restore_result])
        
        # 初始化权限列表
        config_refresh_backups_btn.click(fn=load_backup_list, outputs=[config_backup_list])
        
        # 页面加载时刷新权限列表
        def on_config_tab_select():
            return load_agent_permissions(), load_backup_list()
        
        # 使用load事件在标签页切换时刷新
        config_save_btn.click(fn=on_config_tab_select, outputs=[agent_permission_table, config_backup_list])
    
    return demo


# ============================================================
# 主函数
# ============================================================

def find_available_port(start_port: int = 7870, max_attempts: int = 10) -> int:
    """动态查找可用端口"""
    import socket
    
    for i in range(max_attempts):
        port = start_port + i
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('0.0.0.0', port))
            sock.close()
            return port
        except OSError:
            continue
    return start_port  # 如果都不可用，返回起始端口

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Kylin-TARS 智能体管理系统 - 升级版")
    print("=" * 60)
    print()
    print("可用智能体:")
    print("  - FileAgent: 文件搜索、移动到回收站")
    print("  - SettingsAgent: 壁纸设置、音量调整")
    print("  - NetworkAgent: WiFi连接、代理设置")
    print("  - AppAgent: 应用启动、关闭")
    print()
    
    demo = create_ui()
    
    # 动态查找可用端口
    port = find_available_port(7870)
    print(f"🌐 启动 Web UI，端口: {port}")
    print(f"   访问地址: http://localhost:{port}")
    print()
    
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True
    )