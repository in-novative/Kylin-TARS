import time
import json
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from typing import Dict, List
from gi.repository import GLib
from src.settings_agent_logic import SettingsAgentLogic
from utils.set_logger import set_logger
from utils.get_config import get_master_config, get_child_config

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
    },
    {
        "name": "settings_agent.bluetooth_manage",
        "description": "蓝牙管理（开启/关闭/连接已配对设备/查询状态）",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["enable", "disable", "connect", "status"], "description": "操作类型"},
                "device_name": {"type": "string", "description": "设备名称（连接时必需）"}
            },
            "required": ["action"]
        },
        "permission": "normal",
        "extend_type": "new"
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
        elif tool_name == "settings_agent.bluetooth_manage":
            result = settings_agent.bluetooth_manage(
                action=params["action"],
                device_name=params.get("device_name")
            )
        else:
            return json.dumps({
                "success": False,
                "error": f"工具不存在：{tool_name}"
            })
    
        return json.dumps({
            "success": result["status"] == "success",
            "result": result["data"],
            "msg": result["msg"]
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })

# ===================== DBus消息处理 =====================
def message_handler(bus, message):
    """处理DBus消息（替代dbus.service.method）"""
    # 检查消息类型和接口
    if not isinstance(message, dbus.lowlevel.MethodCallMessage):
        return
    if message.get_interface() != AGENT_INTERFACE:
        return
    
    # 获取方法名和参数
    method_name = message.get_member()
    if method_name == "Ping":
        return json.dumps({
            "status": "ok",
            "timestamp": time.time(),
            "service": "Setting Agent"
        })
    elif method_name != "ToolsCall":
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
def register_to_mcp(logger):
    """注册到MCP Server"""
    MASTERAGENT = get_master_config()
    DBUS_SERVICE_NAME = MASTERAGENT["SERVICE_NAME"]
    DBUS_OBJECT_PATH = MASTERAGENT["OBJECT_PATH"]
    DBUS_INTERFACE_NAME = MASTERAGENT["INTERFACE_NAME"]
    try:
        # 检查MCP Server是否可用
        if not bus.name_has_owner(DBUS_SERVICE_NAME):
            logger.warning(f"MCP Server ({DBUS_SERVICE_NAME}) 未启动，跳过注册")
            return
        
        mcp_proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        interface = dbus.Interface(mcp_proxy, DBUS_INTERFACE_NAME)
        
        register_data = json.dumps({
            "name": "settings_agent",
            "service": AGENT_BUS_NAME,
            "path": AGENT_OBJECT_PATH,
            "interface": AGENT_INTERFACE,
            "tools": SETTINGS_AGENT_TOOLS
        })
        interface.AgentRegister(register_data)
        logger.info("SettingsAgent已成功注册到MCP Server")
    except Exception as e:
        logger.error(f"注册到MCP Server失败：{str(e)}")

# ===================== 启动服务 =====================
if __name__ == "__main__":
    logger = set_logger("setting_agent")
    logger.info("启动SettingsAgent MCP服务")
    
    # 请求DBus服务名
    bus.request_name(AGENT_BUS_NAME)
    
    # 添加DBus消息过滤器
    bus.add_message_filter(message_handler)
    
    # 注册到MCP Server
    register_to_mcp(logger)
    
    # 启动主循环
    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        logger.info("Setting Agent 服务已停止")
        loop.quit()