import sys
import os
import json
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from typing import Dict, List
from gi.repository import GLib

# 项目路径配置
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.settings_agent_logic import SettingsAgentLogic

# ===================== MCP Server DBus配置 =====================
# 使用成员A的MCP Server配置（统一标准）
MCP_BUS_NAME = "com.kylin.ai.mcp.MasterAgent"
MCP_OBJECT_PATH = "/com/kylin/ai/mcp/MasterAgent"
MCP_INTERFACE = "com.kylin.ai.mcp.MasterAgent"

# ===================== SettingsAgent DBus配置 =====================
AGENT_BUS_NAME = "com.mcp.agent.settings"
AGENT_OBJECT_PATH = "/com/mcp/agent/settings"
AGENT_INTERFACE = "com.mcp.agent.settings.Interface"

# ===================== 工具元数据 =====================
SETTINGS_AGENT_TOOLS: List[Dict] = [
    {
        "name": "settings_agent.change_wallpaper",
        "description": "调用DBus实现壁纸修改",
        "parameters": {
            "type": "object",
            "properties": {
                "wallpaper_path": {"type": "string", "description": "壁纸文件绝对路径"},
                "scale": {"type": "string", "enum": ["fill", "scale", "center", "tile", "zoom"], "default": "fill"}
            },
            "required": ["wallpaper_path"]
        }
    },
    {
        "name": "settings_agent.adjust_volume",
        "description": "调用gsettings实现音量调整",
        "parameters": {
            "type": "object",
            "properties": {
                "volume": {"type": "integer", "minimum": 0, "maximum": 100},
                "device": {"type": "string", "default": "@DEFAULT_SINK@"}
            },
            "required": ["volume"]
        }
    }
]

# ===================== 初始化实例 =====================
DBusGMainLoop(set_as_default=True)
settings_agent = SettingsAgentLogic()
bus = dbus.SessionBus()

# ===================== 工具调用核心逻辑 =====================
def handle_tool_call(tool_name: str, params: Dict) -> Dict:
    """处理工具调用的核心逻辑"""
    try:
        if tool_name == "settings_agent.change_wallpaper":
            result = settings_agent.change_wallpaper(
                wallpaper_path=params["wallpaper_path"],
                scale=params.get("scale", "fill")
            )
        elif tool_name == "settings_agent.adjust_volume":
            result = settings_agent.adjust_volume(
                volume=params["volume"],
                device=params.get("device", "@DEFAULT_SINK@")
            )
        else:
            return {"success": False, "error": f"工具不存在：{tool_name}"}
        
        return {
            "success": result["status"] == "success",
            "result": result["data"],
            "msg": result["msg"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ===================== DBus消息处理 =====================
def message_handler(bus, message):
    """处理DBus消息（替代dbus.service.method）"""
    # 检查消息类型和接口
    if message.get_type() != dbus.lowlevel.METHOD_CALL:
        return
    
    if message.get_interface() != AGENT_INTERFACE:
        return
    
    # 获取方法名和参数
    method_name = message.get_member()
    if method_name != "ToolsCall":
        bus.send(
            dbus.lowlevel.ErrorMessage(
                message,
                "org.freedesktop.DBus.Error.UnknownMethod",
                f"Unknown method: {method_name}"
            )
        )
        return
    
    # 解析参数
    try:
        tool_name, params_json = message.get_args_list()
        params = json.loads(params_json)
        
        # 调用工具
        result = handle_tool_call(tool_name, params)
        
        # 发送响应
        reply = dbus.lowlevel.MethodReturnMessage(message)
        reply.append(dbus.String(json.dumps(result)))
        bus.send(reply)
    except Exception as e:
        bus.send(
            dbus.lowlevel.ErrorMessage(
                message,
                "org.freedesktop.DBus.Error.Failed",
                str(e)
            )
        )

# ===================== MCP注册逻辑 =====================
def register_to_mcp():
    """注册到MCP Server"""
    try:
        # 检查MCP Server是否可用
        if not bus.name_has_owner(MCP_BUS_NAME):
            print(f"[WARNING] MCP Server ({MCP_BUS_NAME}) 未启动，跳过注册")
            return
        
        mcp_proxy = bus.get_object(MCP_BUS_NAME, MCP_OBJECT_PATH)
        mcp_interface = dbus.Interface(mcp_proxy, MCP_INTERFACE)
        
        register_data = json.dumps({
            "agent_name": "settings_agent",
            "bus_name": AGENT_BUS_NAME,
            "object_path": AGENT_OBJECT_PATH,
            "interface": AGENT_INTERFACE,
            "tools": SETTINGS_AGENT_TOOLS
        })
        mcp_interface.AgentRegister(register_data)
        print("[INFO] SettingsAgent已成功注册到MCP Server")
    except Exception as e:
        print(f"[ERROR] 注册到MCP Server失败：{str(e)}")

# ===================== 启动服务 =====================
if __name__ == "__main__":
    print("[INFO] 启动SettingsAgent MCP服务")
    
    # 请求DBus服务名
    bus.request_name(AGENT_BUS_NAME)
    
    # 添加DBus消息过滤器
    bus.add_message_filter(message_handler)
    
    # 注册到MCP Server
    register_to_mcp()
    
    # 启动主循环
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\n[INFO] 服务已停止")
        loop.quit()