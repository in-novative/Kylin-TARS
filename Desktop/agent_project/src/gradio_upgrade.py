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

# 项目路径配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "src"))

# 导入智能体逻辑
from file_agent_logic import FileAgentLogic
from settings_agent_logic import SettingsAgentLogic
from network_agent_logic import NetworkAgentLogic
from app_agent_logic import AppAgentLogic

# 导入记忆模块（如果可用）
try:
    sys.path.insert(0, "/data1/cyx/Kylin-TARS")
    from memory_store import list_trajectories, search_trajectories
    from memory_retrieve import retrieve_similar_trajectory
    HAS_MEMORY = True
except ImportError:
    HAS_MEMORY = False
    print("[WARNING] 记忆模块未找到，部分功能不可用")

# ============================================================
# 初始化智能体
# ============================================================
file_agent = FileAgentLogic()
settings_agent = SettingsAgentLogic()
network_agent = NetworkAgentLogic()
app_agent = AppAgentLogic()

# 截图目录
SCREENSHOT_DIR = os.path.join(PROJECT_ROOT, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 日志存储
execution_logs = []

# 权限控制（演示模式）
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"
REQUIRE_CONFIRMATION = os.environ.get("REQUIRE_CONFIRMATION", "false").lower() == "true"

# ============================================================
# 自定义CSS样式
# ============================================================
CUSTOM_CSS = """
/* 主题色 */
:root {
    --primary-color: #2563eb;
    --secondary-color: #3b82f6;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --error-color: #ef4444;
    --bg-dark: #1e293b;
    --bg-light: #f8fafc;
    --text-primary: #1e293b;
    --text-secondary: #64748b;
}

/* 标题样式 */
.main-title {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5rem;
    font-weight: 800;
    text-align: center;
    margin-bottom: 0.5rem;
}

.subtitle {
    color: var(--text-secondary);
    text-align: center;
    font-size: 1rem;
    margin-bottom: 1.5rem;
}

/* 模块容器 */
.module-container {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1rem;
    background: white;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* 按钮样式 */
.primary-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 0.75rem 1.5rem !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
}

.primary-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
}

/* 日志样式 */
.log-success { color: #10b981; }
.log-error { color: #ef4444; }
.log-info { color: #3b82f6; }
.log-warning { color: #f59e0b; }

/* 推理链高亮 */
.highlight-tool { color: #ef4444; font-weight: bold; }
.highlight-agent { color: #2563eb; font-weight: bold; }
.highlight-action { color: #10b981; }

/* 演示模式按钮 */
.demo-btn {
    background: #f0f9ff !important;
    border: 2px solid #3b82f6 !important;
    color: #1e40af !important;
    font-weight: 500 !important;
}

.demo-btn:hover {
    background: #dbeafe !important;
}

/* 状态指示器 */
.status-online { color: #10b981; }
.status-offline { color: #ef4444; }
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
    """格式化推理链为高亮HTML"""
    if not reasoning:
        return "无推理链数据"
    
    json_str = json.dumps(reasoning, indent=2, ensure_ascii=False)
    
    # 高亮工具名
    import re
    json_str = re.sub(
        r'"(.*?_agent\.[a-z_]+)"',
        r'<span class="highlight-tool">"\1"</span>',
        json_str
    )
    
    # 高亮智能体名
    json_str = re.sub(
        r'"(FileAgent|SettingsAgent|NetworkAgent|AppAgent)"',
        r'<span class="highlight-agent">"\1"</span>',
        json_str
    )
    
    return f"<pre>{json_str}</pre>"

def get_history_tasks() -> List[str]:
    """获取历史任务列表"""
    if not HAS_MEMORY:
        return ["（记忆模块不可用）"]
    
    try:
        trajectories = list_trajectories(limit=20)
        tasks = [t.get("task", "未知任务") for t in trajectories if t.get("task")]
        return list(set(tasks))[:10] if tasks else ["（无历史任务）"]
    except:
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

# ============================================================
# 核心功能函数
# ============================================================

def execute_task(task: str, use_memory: bool = True, confirm: bool = False) -> Tuple[str, str, str, List[str]]:
    """
    执行用户任务
    
    Args:
        task: 任务指令
        use_memory: 是否使用记忆模块
        confirm: 用户确认（权限控制）
    
    Returns:
        (推理链, 执行结果, 日志, 截图列表)
    """
    # 权限检查（演示模式）
    if REQUIRE_CONFIRMATION and not confirm:
        add_log("⚠️ 需要用户确认才能执行", "warning")
        return (
            "<pre>等待用户确认...</pre>",
            "⚠️ 请在确认框中勾选「我已确认」后再执行",
            get_logs(),
            []
        )
    
    add_log(f"收到任务: {task}", "info")
    
    # 简单的任务分析和执行
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
    
    results = []
    screenshots = []
    
    # 根据任务关键词分发到不同智能体
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
    
    # 生成任务分解描述
    if reasoning["execution_plan"]:
        steps = [f"{p['step']}. {p['action']}" for p in reasoning["execution_plan"]]
        reasoning["thought_chain"]["task_decomposition"] = "；".join(steps)
        reasoning["milestone_markers"] = [f"step_{i+1}_complete" for i in range(len(steps))]
    else:
        reasoning["thought_chain"]["task_decomposition"] = "任务分析中，请提供更具体的指令"
    
    # 截图
    screenshot = capture_screenshot("task_result")
    if screenshot:
        screenshots.append(screenshot)
        add_log(f"截图已保存: {screenshot}", "info")
    
    add_log("任务执行完成", "success")
    
    # 格式化输出
    reasoning_html = format_reasoning_chain(reasoning)
    result_text = "\n".join(results) if results else "任务已分析，等待执行具体操作"
    logs = get_logs()
    
    return reasoning_html, result_text, logs, screenshots

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
    result = network_agent.list_wifi_networks()
    
    if result["status"] == "success":
        return [[w["ssid"], w["signal"], w["security"]] for w in result["data"]]
    return []

def launch_application(app_name: str) -> str:
    """启动应用"""
    add_log(f"启动应用: {app_name}", "info")
    result = app_agent.launch_app(app_name)
    
    status = "✓" if result["status"] == "success" else "✗"
    return f"{status} {result['msg']}"

def list_running() -> list:
    """列出运行中应用"""
    result = app_agent.list_running_apps()
    
    if result["status"] == "success":
        return [[a.get("name", ""), a.get("title", "")[:40], a.get("pid", "")] 
                for a in result["data"][:20]]
    return []

# ============================================================
# 构建 Gradio 界面
# ============================================================

def create_ui():
    """创建 Gradio 界面"""
    
    with gr.Blocks() as demo:
        
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
                        
                        with gr.Row():
                            history_dropdown = gr.Dropdown(
                                label="历史指令",
                                choices=get_history_tasks(),
                                interactive=True
                            )
                            refresh_history_btn = gr.Button("🔄", scale=0)
                        
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
                            demo_btn_1 = gr.Button("📁 搜索+壁纸", elem_classes=["demo-btn"])
                            demo_btn_2 = gr.Button("🌐 网络+浏览器", elem_classes=["demo-btn"])
                            demo_btn_3 = gr.Button("🔊 调整音量", elem_classes=["demo-btn"])
                    
                    # 右侧：推理链
                    with gr.Column(scale=1):
                        gr.Markdown("### 🧠 推理链解析")
                        reasoning_output = gr.HTML(
                            value="<pre>等待执行任务...</pre>",
                            label="推理链"
                        )
                        copy_btn = gr.Button("📋 复制推理链")
                
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
            
            # ==================== 文件管理页 ====================
            with gr.Tab("📁 文件管理", id="file"):
                gr.Markdown("### 文件搜索")
                with gr.Row():
                    file_path = gr.Textbox(
                        label="搜索路径",
                        value=os.path.expanduser("~/Downloads")
                    )
                    file_keyword = gr.Textbox(label="关键词", value=".png")
                    file_recursive = gr.Checkbox(label="递归", value=True)
                
                file_search_btn = gr.Button("🔍 搜索", variant="primary")
                file_result = gr.Dataframe(
                    headers=["文件名", "路径", "大小", "修改时间"],
                    label="搜索结果"
                )
                file_msg = gr.Textbox(label="操作结果")
                
                gr.Markdown("### 文件操作")
                with gr.Row():
                    trash_path = gr.Textbox(label="文件路径", placeholder="输入要删除的文件路径")
                    trash_btn = gr.Button("🗑️ 移至回收站")
            
            # ==================== 系统设置页 ====================
            with gr.Tab("⚙️ 系统设置", id="settings"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 🖼️ 壁纸设置")
                        wallpaper_path = gr.Textbox(
                            label="壁纸路径",
                            placeholder="/path/to/image.png"
                        )
                        wallpaper_scale = gr.Dropdown(
                            label="缩放方式",
                            choices=["zoom", "scaled", "centered", "stretched"],
                            value="zoom"
                        )
                        wallpaper_btn = gr.Button("🖼️ 设置壁纸", variant="primary")
                        wallpaper_msg = gr.Textbox(label="结果")
                        wallpaper_preview = gr.Image(label="预览", height=200)
                    
                    with gr.Column():
                        gr.Markdown("### 🔊 音量设置")
                        volume_slider = gr.Slider(
                            label="音量",
                            minimum=0,
                            maximum=100,
                            value=50,
                            step=1
                        )
                        volume_device = gr.Textbox(
                            label="设备",
                            value="@DEFAULT_SINK@"
                        )
                        volume_btn = gr.Button("🔊 调整音量", variant="primary")
                        volume_msg = gr.Textbox(label="结果")
            
            # ==================== 网络管理页 ====================
            with gr.Tab("🌐 网络管理", id="network"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 📶 网络状态")
                        network_status_btn = gr.Button("🔄 刷新状态", variant="primary")
                        network_status = gr.Markdown("点击刷新查看网络状态")
                        
                        gr.Markdown("### 📡 可用 WiFi")
                        wifi_scan_btn = gr.Button("📡 扫描 WiFi")
                        wifi_list = gr.Dataframe(
                            headers=["名称", "信号", "安全性"],
                            label="WiFi 列表"
                        )
                    
                    with gr.Column():
                        gr.Markdown("### 🔗 代理设置")
                        proxy_host = gr.Textbox(label="主机", placeholder="127.0.0.1")
                        proxy_port = gr.Number(label="端口", value=1080)
                        proxy_type = gr.Dropdown(
                            label="类型",
                            choices=["http", "https", "socks"],
                            value="http"
                        )
                        with gr.Row():
                            proxy_set_btn = gr.Button("✓ 设置代理")
                            proxy_clear_btn = gr.Button("✗ 清除代理")
                        proxy_msg = gr.Textbox(label="结果")
            
            # ==================== 应用管理页 ====================
            with gr.Tab("📱 应用管理", id="app"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### 🚀 启动应用")
                        app_name = gr.Textbox(
                            label="应用名称",
                            placeholder="firefox / 终端 / 文件管理器"
                        )
                        with gr.Row():
                            app_launch_btn = gr.Button("▶️ 启动", variant="primary")
                            app_close_btn = gr.Button("⏹️ 关闭")
                        app_msg = gr.Textbox(label="结果")
                        
                        gr.Markdown("### 💡 快捷启动")
                        with gr.Row():
                            gr.Button("🦊 Firefox").click(
                                lambda: launch_application("firefox"),
                                outputs=[app_msg]
                            )
                            gr.Button("📂 文件").click(
                                lambda: launch_application("nautilus"),
                                outputs=[app_msg]
                            )
                            gr.Button("💻 终端").click(
                                lambda: launch_application("gnome-terminal"),
                                outputs=[app_msg]
                            )
                    
                    with gr.Column():
                        gr.Markdown("### 📋 运行中的应用")
                        running_refresh_btn = gr.Button("🔄 刷新列表")
                        running_apps = gr.Dataframe(
                            headers=["应用", "标题", "PID"],
                            label="运行中"
                        )
            
            # ==================== 记忆轨迹页 ====================
            with gr.Tab("🧠 记忆轨迹", id="memory"):
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
                    memory_search_btn = gr.Button("🔍 搜索")
        
        # ==================== 事件绑定 ====================
        
        # 任务执行
        execute_btn.click(
            fn=execute_task,
            inputs=[task_input, confirm_checkbox],
            outputs=[reasoning_output, result_output, log_output, screenshot_gallery]
        )
        
        # 历史指令选择
        history_dropdown.change(
            fn=lambda x: x if x and x != "（" else "",
            inputs=[history_dropdown],
            outputs=[task_input]
        )
        
        # 刷新历史
        refresh_history_btn.click(
            fn=lambda: gr.update(choices=get_history_tasks()),
            outputs=[history_dropdown]
        )
        
        # 清空
        clear_btn.click(
            fn=lambda: ("", "<pre>等待执行任务...</pre>", "", []),
            outputs=[task_input, reasoning_output, result_output, screenshot_gallery]
        )
        
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
        
        # 网络管理
        network_status_btn.click(fn=get_network_status, outputs=[network_status])
        wifi_scan_btn.click(fn=list_wifi, outputs=[wifi_list])
        
        # 应用管理
        app_launch_btn.click(
            fn=launch_application,
            inputs=[app_name],
            outputs=[app_msg]
        )
        running_refresh_btn.click(fn=list_running, outputs=[running_apps])
    
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

