#!/usr/bin/env python3
"""
功能完整性检查脚本
检查所有智能体的功能是否已实现，并在前端页面有对应UI
"""

import os
import re
import sys
from typing import Dict, List, Tuple

# 颜色输出
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def check_file_exists(filepath: str) -> bool:
    """检查文件是否存在"""
    return os.path.exists(filepath)

def extract_tools_from_mcp(filepath: str) -> List[str]:
    """从MCP文件中提取工具名称"""
    tools = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找工具定义块
        pattern = r'"name":\s*"([^"]+)"'
        matches = re.findall(pattern, content)
        for match in matches:
            if 'agent.' in match:
                tools.append(match)
    except Exception as e:
        pass
    return tools

def check_gradio_ui_component(filepath: str, keywords: List[str]) -> Dict[str, bool]:
    """检查Gradio UI中是否包含指定组件"""
    results = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for keyword in keywords:
            # 检查关键词是否在UI代码中
            results[keyword] = keyword.lower() in content.lower()
    except Exception as e:
        for keyword in keywords:
            results[keyword] = False
    return results

def check_function_in_logic(filepath: str, func_names: List[str]) -> Dict[str, bool]:
    """检查逻辑文件中是否包含指定函数"""
    results = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for func_name in func_names:
            # 检查函数定义
            pattern = rf'def\s+{func_name}\s*\('
            results[func_name] = bool(re.search(pattern, content))
    except Exception as e:
        for func_name in func_names:
            results[func_name] = False
    return results

def main():
    """主检查函数"""
    base_dir = "/data1/cyx/Kylin-TARS"
    src_dir = os.path.join(base_dir, "Desktop/agent_project/src")
    gradio_file = os.path.join(src_dir, "gradio_upgrade.py")
    
    print(f"{BLUE}╔══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BLUE}║  功能完整性检查报告                                          ║{NC}")
    print(f"{BLUE}╚══════════════════════════════════════════════════════════════╝{NC}\n")
    
    all_passed = True
    
    # ==================== FileAgent ====================
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{BLUE}FileAgent（📁 文件管理）{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    
    file_agent_logic = os.path.join(src_dir, "file_agent_logic.py")
    file_agent_mcp = os.path.join(src_dir, "file_agent_mcp.py")
    
    file_functions = {
        "文件搜索": ["search_file"],
        "回收站": ["move_to_trash"],
        "批量重命名": ["batch_rename"]
    }
    
    file_ui_keywords = ["file_search", "trash", "batch_rename"]
    
    # 检查逻辑文件
    if check_file_exists(file_agent_logic):
        print(f"{GREEN}✓ 逻辑文件存在{NC}")
        for func_name, funcs in file_functions.items():
            results = check_function_in_logic(file_agent_logic, funcs)
            for func, exists in results.items():
                if exists:
                    print(f"  {GREEN}✓ {func_name}: {func} 已实现{NC}")
                else:
                    print(f"  {RED}✗ {func_name}: {func} 未实现{NC}")
                    all_passed = False
    else:
        print(f"{RED}✗ 逻辑文件不存在{NC}")
        all_passed = False
    
    # 检查MCP注册
    if check_file_exists(file_agent_mcp):
        tools = extract_tools_from_mcp(file_agent_mcp)
        print(f"  MCP工具: {tools}")
        if "file_agent.search_file" in tools and "file_agent.move_to_trash" in tools:
            print(f"  {GREEN}✓ 核心工具已注册{NC}")
        else:
            print(f"  {YELLOW}⚠ 部分工具可能未注册{NC}")
    
    # 检查UI组件
    ui_results = check_gradio_ui_component(gradio_file, file_ui_keywords)
    for keyword, exists in ui_results.items():
        if exists:
            print(f"  {GREEN}✓ UI组件 '{keyword}' 已存在{NC}")
        else:
            print(f"  {RED}✗ UI组件 '{keyword}' 缺失{NC}")
            all_passed = False
    
    print()
    
    # ==================== SettingsAgent ====================
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{BLUE}SettingsAgent（⚙️ 系统设置）{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    
    settings_agent_logic = os.path.join(src_dir, "settings_agent_logic.py")
    settings_agent_mcp = os.path.join(src_dir, "settings_agent_mcp.py")
    
    settings_functions = {
        "壁纸": ["change_wallpaper"],
        "音量": ["adjust_volume"],
        "蓝牙": ["bluetooth_manage"]
    }
    
    settings_ui_keywords = ["wallpaper", "volume", "bluetooth"]
    
    if check_file_exists(settings_agent_logic):
        print(f"{GREEN}✓ 逻辑文件存在{NC}")
        for func_name, funcs in settings_functions.items():
            results = check_function_in_logic(settings_agent_logic, funcs)
            for func, exists in results.items():
                if exists:
                    print(f"  {GREEN}✓ {func_name}: {func} 已实现{NC}")
                else:
                    print(f"  {RED}✗ {func_name}: {func} 未实现{NC}")
                    all_passed = False
    else:
        print(f"{RED}✗ 逻辑文件不存在{NC}")
        all_passed = False
    
    ui_results = check_gradio_ui_component(gradio_file, settings_ui_keywords)
    for keyword, exists in ui_results.items():
        if exists:
            print(f"  {GREEN}✓ UI组件 '{keyword}' 已存在{NC}")
        else:
            print(f"  {YELLOW}⚠ UI组件 '{keyword}' 缺失（可能通过任务执行调用）{NC}")
    
    print()
    
    # ==================== NetworkAgent ====================
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{BLUE}NetworkAgent（🌐 网络管理）{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    
    network_agent_logic = os.path.join(src_dir, "network_agent_logic.py")
    network_agent_mcp = os.path.join(src_dir, "network_agent_mcp.py")
    
    network_functions = {
        "WiFi扫描": ["list_wifi", "list_wifi_networks"],  # 支持两种函数名
        "WiFi连接": ["connect_wifi"],
        "代理设置": ["set_proxy"],
        "网络测速": ["speed_test"]
    }
    
    network_ui_keywords = ["wifi", "proxy", "speed"]
    
    if check_file_exists(network_agent_logic):
        print(f"{GREEN}✓ 逻辑文件存在{NC}")
        for func_name, funcs in network_functions.items():
            results = check_function_in_logic(network_agent_logic, funcs)
            # 检查是否有任一函数存在
            any_exists = any(results.values())
            if any_exists:
                found_func = [f for f, e in results.items() if e][0]
                print(f"  {GREEN}✓ {func_name}: {found_func} 已实现{NC}")
            else:
                print(f"  {RED}✗ {func_name}: 未实现{NC}")
                all_passed = False
    else:
        print(f"{RED}✗ 逻辑文件不存在{NC}")
        all_passed = False
    
    ui_results = check_gradio_ui_component(gradio_file, network_ui_keywords)
    for keyword, exists in ui_results.items():
        if exists:
            print(f"  {GREEN}✓ UI组件 '{keyword}' 已存在{NC}")
        else:
            print(f"  {YELLOW}⚠ UI组件 '{keyword}' 缺失{NC}")
    
    print()
    
    # ==================== AppAgent ====================
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{BLUE}AppAgent（📱 应用管理）{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    
    app_agent_logic = os.path.join(src_dir, "app_agent_logic.py")
    app_agent_mcp = os.path.join(src_dir, "app_agent_mcp.py")
    
    app_functions = {
        "启动应用": ["launch_app"],
        "关闭应用": ["close_app"],
        "快捷操作": ["app_quick_operation"]
    }
    
    app_ui_keywords = ["launch", "close", "app"]
    
    if check_file_exists(app_agent_logic):
        print(f"{GREEN}✓ 逻辑文件存在{NC}")
        for func_name, funcs in app_functions.items():
            results = check_function_in_logic(app_agent_logic, funcs)
            for func, exists in results.items():
                if exists:
                    print(f"  {GREEN}✓ {func_name}: {func} 已实现{NC}")
                else:
                    print(f"  {RED}✗ {func_name}: {func} 未实现{NC}")
                    all_passed = False
    else:
        print(f"{RED}✗ 逻辑文件不存在{NC}")
        all_passed = False
    
    ui_results = check_gradio_ui_component(gradio_file, app_ui_keywords)
    for keyword, exists in ui_results.items():
        if exists:
            print(f"  {GREEN}✓ UI组件 '{keyword}' 已存在{NC}")
        else:
            print(f"  {YELLOW}⚠ UI组件 '{keyword}' 缺失{NC}")
    
    print()
    
    # ==================== MonitorAgent ====================
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{BLUE}MonitorAgent（📊 系统监控）{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    
    monitor_agent_logic = os.path.join(src_dir, "monitor_agent_logic.py")
    monitor_agent_mcp = os.path.join(src_dir, "monitor_agent_mcp.py")
    
    monitor_functions = {
        "系统状态": ["get_system_status"],
        "进程清理": ["clean_background_process"]
    }
    
    monitor_ui_keywords = ["system_status", "process_clean", "monitor"]
    
    if check_file_exists(monitor_agent_logic):
        print(f"{GREEN}✓ 逻辑文件存在{NC}")
        for func_name, funcs in monitor_functions.items():
            results = check_function_in_logic(monitor_agent_logic, funcs)
            for func, exists in results.items():
                if exists:
                    print(f"  {GREEN}✓ {func_name}: {func} 已实现{NC}")
                else:
                    print(f"  {RED}✗ {func_name}: {func} 未实现{NC}")
                    all_passed = False
    else:
        print(f"{RED}✗ 逻辑文件不存在{NC}")
        all_passed = False
    
    ui_results = check_gradio_ui_component(gradio_file, monitor_ui_keywords)
    for keyword, exists in ui_results.items():
        if exists:
            print(f"  {GREEN}✓ UI组件 '{keyword}' 已存在{NC}")
        else:
            print(f"  {RED}✗ UI组件 '{keyword}' 缺失{NC}")
            all_passed = False
    
    print()
    
    # ==================== MediaAgent ====================
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{BLUE}MediaAgent（🎵 媒体控制）{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    
    media_agent_logic = os.path.join(src_dir, "media_agent_logic.py")
    media_agent_mcp = os.path.join(src_dir, "media_agent_mcp.py")
    
    media_functions = {
        "播放媒体": ["play_media"],
        "媒体控制": ["media_control"],
        "截图帧": ["capture_media_frame"]
    }
    
    media_ui_keywords = ["play_media", "media_control", "capture_media_frame"]
    
    if check_file_exists(media_agent_logic):
        print(f"{GREEN}✓ 逻辑文件存在{NC}")
        for func_name, funcs in media_functions.items():
            results = check_function_in_logic(media_agent_logic, funcs)
            for func, exists in results.items():
                if exists:
                    print(f"  {GREEN}✓ {func_name}: {func} 已实现{NC}")
                else:
                    print(f"  {RED}✗ {func_name}: {func} 未实现{NC}")
                    all_passed = False
    else:
        print(f"{RED}✗ 逻辑文件不存在{NC}")
        all_passed = False
    
    ui_results = check_gradio_ui_component(gradio_file, media_ui_keywords)
    for keyword, exists in ui_results.items():
        if exists:
            print(f"  {GREEN}✓ UI组件 '{keyword}' 已存在{NC}")
        else:
            print(f"  {RED}✗ UI组件 '{keyword}' 缺失{NC}")
            all_passed = False
    
    print()
    
    # ==================== 记忆与日志 ====================
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{BLUE}记忆与日志（🧠 记忆轨迹 / 📜 协作日志）{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    
    memory_ui_keywords = ["memory", "history", "visualization", "log", "collaboration"]
    
    ui_results = check_gradio_ui_component(gradio_file, memory_ui_keywords)
    for keyword, exists in ui_results.items():
        if exists:
            print(f"  {GREEN}✓ UI组件 '{keyword}' 已存在{NC}")
        else:
            print(f"  {YELLOW}⚠ UI组件 '{keyword}' 缺失{NC}")
    
    print()
    
    # ==================== MCP配置 ====================
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    print(f"{BLUE}MCP配置（⚙️ MCP配置）{NC}")
    print(f"{BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{NC}")
    
    config_ui_keywords = ["config", "permission", "backup", "restore"]
    
    ui_results = check_gradio_ui_component(gradio_file, config_ui_keywords)
    for keyword, exists in ui_results.items():
        if exists:
            print(f"  {GREEN}✓ UI组件 '{keyword}' 已存在{NC}")
        else:
            print(f"  {RED}✗ UI组件 '{keyword}' 缺失{NC}")
            all_passed = False
    
    print()
    
    # ==================== 总结 ====================
    print(f"{BLUE}╔══════════════════════════════════════════════════════════════╗{NC}")
    print(f"{BLUE}║  检查总结                                                      ║{NC}")
    print(f"{BLUE}╚══════════════════════════════════════════════════════════════╝{NC}")
    
    if all_passed:
        print(f"{GREEN}✓ 所有核心功能已实现并在前端页面体现{NC}")
    else:
        print(f"{RED}✗ 部分功能缺失或未在前端体现，请检查上述报告{NC}")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

