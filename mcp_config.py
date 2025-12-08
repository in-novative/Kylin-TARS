#!/usr/bin/env python3
"""
MCP 配置文件 - 统一各成员的 D-Bus 配置

本文件解决成员A和成员C的D-Bus服务名不一致问题。
联调时使用此配置作为统一标准。

成员A原始配置: com.kylin.ai.mcp.MasterAgent
成员C原始配置: com.mcp.server

统一方案: 使用成员A的配置作为标准，成员C的代码需要适配
"""

# ============================================================
# MCP Server 配置（成员A - Master Agent）
# ============================================================

MCP_SERVER_CONFIG = {
    # D-Bus 服务名
    "service_name": "com.kylin.ai.mcp.MasterAgent",
    # D-Bus 对象路径
    "object_path": "/com/kylin/ai/mcp/MasterAgent",
    # D-Bus 接口名
    "interface_name": "com.kylin.ai.mcp.MasterAgent",
    # 默认总线类型
    "bus_type": "session"
}

# 导出便捷常量
MCP_SERVICE_NAME = MCP_SERVER_CONFIG["service_name"]
MCP_OBJECT_PATH = MCP_SERVER_CONFIG["object_path"]
MCP_INTERFACE_NAME = MCP_SERVER_CONFIG["interface_name"]
MCP_BUS_TYPE = MCP_SERVER_CONFIG["bus_type"]


# ============================================================
# 子智能体配置（成员C）
# ============================================================

FILE_AGENT_CONFIG = {
    "name": "FileAgent",
    "service": "com.mcp.agent.file",
    "path": "/com/mcp/agent/file",
    "interface": "com.mcp.agent.file.Interface",
    "tools": [
        {
            "name": "file_agent.search_file",
            "description": "按关键词搜索指定目录下的文件",
            "parameters": {
                "search_path": {"type": "string", "description": "搜索目录路径"},
                "keyword": {"type": "string", "description": "搜索关键词"},
                "recursive": {"type": "boolean", "default": True}
            },
            "examples": []
        },
        {
            "name": "file_agent.move_to_trash",
            "description": "将文件移动到回收站",
            "parameters": {
                "file_path": {"type": "string", "description": "文件路径"}
            },
            "examples": []
        }
    ]
}

SETTINGS_AGENT_CONFIG = {
    "name": "SettingsAgent",
    "service": "com.mcp.agent.settings",
    "path": "/com/mcp/agent/settings",
    "interface": "com.mcp.agent.settings.Interface",
    "tools": [
        {
            "name": "settings_agent.change_wallpaper",
            "description": "修改桌面壁纸",
            "parameters": {
                "wallpaper_path": {"type": "string", "description": "壁纸文件路径"},
                "scale": {"type": "string", "default": "zoom"}
            },
            "examples": []
        },
        {
            "name": "settings_agent.adjust_volume",
            "description": "调整系统音量",
            "parameters": {
                "volume": {"type": "integer", "min": 0, "max": 100},
                "device": {"type": "string", "default": "@DEFAULT_SINK@"}
            },
            "examples": []
        }
    ]
}

# 所有子智能体配置
AGENTS_CONFIG = {
    "FileAgent": FILE_AGENT_CONFIG,
    "SettingsAgent": SETTINGS_AGENT_CONFIG
}


# ============================================================
# 工具名称映射（统一标准）
# ============================================================

# 从用户友好的工具名映射到实际的MCP工具名
TOOL_NAME_MAP = {
    # FileAgent 工具
    "search_file": "file_agent.search_file",
    "搜索文件": "file_agent.search_file",
    "move_to_trash": "file_agent.move_to_trash",
    "删除文件": "file_agent.move_to_trash",
    "移动到回收站": "file_agent.move_to_trash",
    
    # SettingsAgent 工具
    "change_wallpaper": "settings_agent.change_wallpaper",
    "更换壁纸": "settings_agent.change_wallpaper",
    "设置壁纸": "settings_agent.change_wallpaper",
    "adjust_volume": "settings_agent.adjust_volume",
    "调整音量": "settings_agent.adjust_volume",
}


# ============================================================
# 任务关键词到智能体的映射
# ============================================================

TASK_AGENT_MAP = {
    # FileAgent 相关关键词
    "搜索": "FileAgent",
    "查找": "FileAgent",
    "文件": "FileAgent",
    "目录": "FileAgent",
    "回收站": "FileAgent",
    "删除": "FileAgent",
    "移动": "FileAgent",
    
    # SettingsAgent 相关关键词
    "壁纸": "SettingsAgent",
    "桌面": "SettingsAgent",
    "音量": "SettingsAgent",
    "设置": "SettingsAgent",
    "声音": "SettingsAgent",
}


def get_agent_for_task(task: str) -> str:
    """
    根据任务描述确定应该使用的智能体
    
    Args:
        task: 用户任务描述
        
    Returns:
        智能体名称
    """
    for keyword, agent in TASK_AGENT_MAP.items():
        if keyword in task:
            return agent
    return "FileAgent"  # 默认返回 FileAgent


def get_tool_name(friendly_name: str) -> str:
    """
    获取标准工具名称
    
    Args:
        friendly_name: 用户友好的工具名
        
    Returns:
        标准MCP工具名
    """
    return TOOL_NAME_MAP.get(friendly_name, friendly_name)


def get_all_tools() -> list:
    """获取所有可用工具列表"""
    tools = []
    for agent_config in AGENTS_CONFIG.values():
        tools.extend(agent_config["tools"])
    return tools


def get_tool_by_name(tool_name: str) -> dict:
    """
    根据工具名获取工具配置
    
    Args:
        tool_name: 工具名
        
    Returns:
        工具配置字典
    """
    for agent_config in AGENTS_CONFIG.values():
        for tool in agent_config["tools"]:
            if tool["name"] == tool_name:
                return tool
    return None


# ============================================================
# 联调验证函数
# ============================================================

def validate_config():
    """验证配置完整性"""
    print("🔧 MCP 配置验证")
    print("=" * 50)
    
    # 验证 MCP Server 配置
    print("\n✓ MCP Server 配置:")
    print(f"  服务名: {MCP_SERVICE_NAME}")
    print(f"  对象路径: {MCP_OBJECT_PATH}")
    print(f"  接口名: {MCP_INTERFACE_NAME}")
    
    # 验证子智能体配置
    print("\n✓ 子智能体配置:")
    for name, config in AGENTS_CONFIG.items():
        print(f"\n  [{name}]")
        print(f"    服务: {config['service']}")
        print(f"    工具数: {len(config['tools'])}")
        for tool in config["tools"]:
            print(f"      - {tool['name']}")
    
    # 验证工具映射
    print("\n✓ 工具映射验证:")
    all_tools = get_all_tools()
    print(f"  总工具数: {len(all_tools)}")
    
    print("\n配置验证完成 ✓")


if __name__ == "__main__":
    validate_config()

