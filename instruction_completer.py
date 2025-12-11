#!/usr/bin/env python3
"""
指令补全/追问模块

功能：
1. 模糊指令判断（参数缺失/指令歧义/依赖缺失）
2. 自动生成追问话术
3. 接收用户补充参数后重新生成推理链

作者：GUI Agent Team
"""

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum


class InstructionIssueType(Enum):
    """指令问题类型"""
    MISSING_PARAMS = "missing_params"  # 参数缺失
    AMBIGUOUS = "ambiguous"  # 指令歧义
    MISSING_DEPENDENCY = "missing_dependency"  # 依赖缺失


# 工具参数清单（定义各工具所需参数）
TOOL_PARAMETERS = {
    # FileAgent 工具
    "file_agent.batch_rename": {
        "required": ["target_dir", "rename_rule"],
        "optional": ["file_type", "prefix", "suffix", "start_number"],
        "description": "批量重命名文件"
    },
    "file_agent.search_file": {
        "required": ["path", "keyword"],
        "optional": ["recursive"],
        "description": "搜索文件"
    },
    "file_agent.move_to_trash": {
        "required": ["file_path"],
        "optional": [],
        "description": "移动到回收站"
    },
    
    # SettingsAgent 工具
    "settings_agent.bluetooth_manage": {
        "required": ["action"],
        "optional": ["device_name"],
        "description": "蓝牙管理（action: enable/disable/connect）"
    },
    "settings_agent.change_wallpaper": {
        "required": ["wallpaper_path"],
        "optional": ["scale_mode"],
        "description": "修改壁纸"
    },
    "settings_agent.adjust_volume": {
        "required": ["volume"],
        "optional": ["device"],
        "description": "调整音量"
    },
    
    # NetworkAgent 工具
    "network_agent.speed_test": {
        "required": [],
        "optional": ["test_type"],
        "description": "网络测速（test_type: quick/full）"
    },
    "network_agent.connect_wifi": {
        "required": ["ssid"],
        "optional": ["password"],
        "description": "连接WiFi"
    },
    "network_agent.set_proxy": {
        "required": ["host", "port", "proxy_type"],
        "optional": [],
        "description": "设置代理"
    },
    
    # AppAgent 工具
    "app_agent.app_quick_operation": {
        "required": ["app_name"],
        "optional": ["args", "url"],
        "description": "应用快捷操作（如firefox https://www.baidu.com）"
    },
    "app_agent.launch_app": {
        "required": ["app_name"],
        "optional": ["args"],
        "description": "启动应用"
    },
    "app_agent.close_app": {
        "required": ["app_name"],
        "optional": ["force"],
        "description": "关闭应用"
    },
    
    # MonitorAgent 工具
    "monitor_agent.get_system_status": {
        "required": [],
        "optional": [],
        "description": "获取系统状态（CPU/内存/磁盘）"
    },
    "monitor_agent.clean_background_process": {
        "required": [],
        "optional": ["process_name"],
        "description": "清理后台进程"
    },
    
    # MediaAgent 工具
    "media_agent.play_media": {
        "required": ["media_path"],
        "optional": [],
        "description": "播放媒体文件"
    },
    "media_agent.media_control": {
        "required": ["action"],
        "optional": [],
        "description": "媒体控制（action: play/pause/stop/fullscreen）"
    },
}

# 模糊指令关键词映射
AMBIGUOUS_PATTERNS = {
    "批量重命名": {
        "tool": "file_agent.batch_rename",
        "questions": [
            "请指定目标目录（如 ~/Downloads）",
            "请指定重命名规则（如：前缀_序号、日期_前缀_序号、后缀_序号）",
            "请指定文件类型（如：.png、.jpg，留空表示所有文件）"
        ]
    },
    "打开微信": {
        "tool": "app_agent.app_quick_operation",
        "questions": [
            "是否打开文件传输助手？",
            "是否打开特定聊天窗口？"
        ]
    },
    "连接蓝牙": {
        "tool": "settings_agent.bluetooth_manage",
        "questions": [
            "请指定要连接的设备名称",
            "是否先开启蓝牙？"
        ]
    },
}


def check_instruction_completeness(
    user_task: str,
    reasoning_chain: Optional[Dict] = None
) -> Tuple[bool, Optional[Dict]]:
    """
    检查指令完整性，判断是否需要追问
    
    Args:
        user_task: 用户任务指令
        reasoning_chain: 已生成的推理链（可选）
        
    Returns:
        (is_complete, issue_info)
        is_complete: 指令是否完整
        issue_info: 问题信息（如果需要追问）
            {
                "issue_type": InstructionIssueType,
                "tool": "tool_name",
                "missing_params": ["param1", "param2"],
                "questions": ["问题1", "问题2"],
                "suggestion": "建议话术"
            }
    """
    user_task_lower = user_task.lower()
    
    # 1. 检查参数缺失
    for tool_name, tool_info in TOOL_PARAMETERS.items():
        # 检查是否涉及该工具
        tool_keywords = tool_info["description"]
        if any(kw in user_task_lower for kw in tool_keywords.split()):
            missing_params = []
            required_params = tool_info["required"]
            
            # 检查必填参数
            for param in required_params:
                if param == "target_dir" and "目录" not in user_task and "路径" not in user_task:
                    missing_params.append(param)
                elif param == "rename_rule" and "规则" not in user_task and "重命名" in user_task:
                    missing_params.append(param)
                elif param == "ssid" and "wifi" in user_task_lower and "ssid" not in user_task_lower:
                    missing_params.append(param)
                elif param == "app_name" and "应用" in user_task and not re.search(r'(firefox|chrome|微信|终端)', user_task):
                    missing_params.append(param)
                elif param == "media_path" and "播放" in user_task and not re.search(r'\.(mp4|mp3|avi|mkv)', user_task_lower):
                    missing_params.append(param)
            
            if missing_params:
                questions = _generate_questions(tool_name, missing_params, tool_info)
                return False, {
                    "issue_type": InstructionIssueType.MISSING_PARAMS,
                    "tool": tool_name,
                    "missing_params": missing_params,
                    "questions": questions,
                    "suggestion": _generate_suggestion(tool_name, missing_params)
                }
    
    # 2. 检查指令歧义
    for pattern, info in AMBIGUOUS_PATTERNS.items():
        if pattern in user_task:
            return False, {
                "issue_type": InstructionIssueType.AMBIGUOUS,
                "tool": info["tool"],
                "questions": info["questions"],
                "suggestion": f"请补充以下信息：{'; '.join(info['questions'])}"
            }
    
    # 3. 检查依赖缺失（需要先检查系统状态）
    dependency_checks = [
        ("蓝牙", "settings_agent.bluetooth_manage", "蓝牙功能"),
        ("wifi", "network_agent.connect_wifi", "WiFi功能"),
        ("代理", "network_agent.set_proxy", "网络代理功能"),
    ]
    
    for keyword, tool, feature_name in dependency_checks:
        if keyword in user_task_lower:
            # 这里可以调用实际的系统检查，暂时返回提示
            return False, {
                "issue_type": InstructionIssueType.MISSING_DEPENDENCY,
                "tool": tool,
                "questions": [f"是否先检查{feature_name}状态？"],
                "suggestion": f"建议先检查{feature_name}是否已开启"
            }
    
    return True, None


def _generate_questions(tool_name: str, missing_params: List[str], tool_info: Dict) -> List[str]:
    """生成追问问题列表"""
    questions = []
    param_descriptions = {
        "target_dir": "目标目录（如 ~/Downloads）",
        "rename_rule": "重命名规则（如：前缀_序号、日期_前缀_序号）",
        "file_type": "文件类型（如：.png、.jpg）",
        "ssid": "WiFi网络名称",
        "password": "WiFi密码",
        "app_name": "应用名称（如：firefox、微信）",
        "media_path": "媒体文件路径",
        "action": "操作类型",
        "host": "代理主机地址",
        "port": "代理端口",
        "proxy_type": "代理类型（http/https/socks）",
    }
    
    for param in missing_params:
        desc = param_descriptions.get(param, param)
        questions.append(f"请指定{desc}")
    
    return questions


def _generate_suggestion(tool_name: str, missing_params: List[str]) -> str:
    """生成建议话术"""
    tool_display = tool_name.split(".")[-1].replace("_", " ")
    
    if "batch_rename" in tool_name:
        return f"批量重命名需要指定：目标目录和重命名规则。例如：'批量重命名~/Downloads目录的png文件，规则为日期_序号'"
    elif "bluetooth" in tool_name:
        return f"蓝牙操作需要指定：操作类型（开启/关闭/连接）和设备名称"
    elif "speed_test" in tool_name:
        return f"网络测速可以直接执行，无需额外参数"
    elif "app_quick_operation" in tool_name:
        return f"应用快捷操作需要指定：应用名称。例如：'打开Firefox浏览器访问百度'"
    else:
        return f"请补充{', '.join(missing_params)}参数"


def complete_instruction(
    original_task: str,
    user_responses: Dict[str, str]
) -> str:
    """
    根据用户补充的参数完成指令
    
    Args:
        original_task: 原始任务指令
        user_responses: 用户补充的参数 {"param1": "value1", "param2": "value2"}
        
    Returns:
        补全后的完整指令
    """
    completed_task = original_task
    
    # 将用户响应合并到原始指令中
    for param, value in user_responses.items():
        if param == "target_dir":
            completed_task += f"，目标目录：{value}"
        elif param == "rename_rule":
            completed_task += f"，重命名规则：{value}"
        elif param == "file_type":
            completed_task += f"，文件类型：{value}"
        elif param == "ssid":
            completed_task += f"，WiFi名称：{value}"
        elif param == "password":
            completed_task += f"，密码：{value}"
        elif param == "app_name":
            completed_task += f"，应用：{value}"
        elif param == "media_path":
            completed_task += f"，文件路径：{value}"
    
    return completed_task


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    print("=== 测试指令补全模块 ===\n")
    
    # 测试1: 参数缺失
    test_cases = [
        "批量重命名文件",
        "连接WiFi",
        "打开应用",
        "播放视频",
        "搜索下载目录的png文件并设置为壁纸",  # 完整指令
    ]
    
    for task in test_cases:
        print(f"测试指令: {task}")
        is_complete, issue_info = check_instruction_completeness(task)
        
        if is_complete:
            print("  ✓ 指令完整，无需追问\n")
        else:
            print(f"  ✗ 需要追问")
            print(f"  问题类型: {issue_info['issue_type'].value}")
            print(f"  涉及工具: {issue_info.get('tool', 'N/A')}")
            print(f"  追问问题: {issue_info.get('questions', [])}")
            print(f"  建议: {issue_info.get('suggestion', 'N/A')}\n")

