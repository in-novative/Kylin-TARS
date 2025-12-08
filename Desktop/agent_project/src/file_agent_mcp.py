import sys
import os
import json
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from typing import Dict, List
from gi.repository import GLib

# 把项目根目录加入Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.file_agent_logic import FileAgentLogic

# ===================== MCP Server DBus配置 =====================
MCP_BUS_NAME = "com.mcp.server"
MCP_OBJECT_PATH = "/com/mcp/server"
MCP_INTERFACE = "com.mcp.server.Interface"

# ===================== FileAgent DBus配置 =====================
AGENT_BUS_NAME = "com.mcp.agent.file"
AGENT_OBJECT_PATH = "/com/mcp/agent/file"
AGENT_INTERFACE = "com.mcp.agent.file.Interface"

# ===================== 工具元数据定义 =====================
FILE_AGENT_TOOLS: List[Dict] = [
    {
        "name": "file_agent.search_file",
        "description": "按关键词递归/非递归搜索指定目录下的文件，返回文件详情",
        "parameters": {
            "type": "object",
            "properties": {
                "search_path": {"type": "string", "description": "搜索目录的绝对路径"},
                "keyword": {"type": "string", "description": "搜索关键词"},
                "recursive": {"type": "boolean", "default": True, "description": "是否递归搜索"}
            },
            "required": ["search_path", "keyword"]
        }
    },
    {
        "name": "file_agent.move_to_trash",
        "description": "将指定文件/目录移动到Linux系统回收站",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "文件/目录的绝对路径"}
            },
            "required": ["file_path"]
        }
    }
]

# ===================== 初始化实例 =====================
DBusGMainLoop(set_as_default=True)
file_agent = FileAgentLogic()
bus = dbus.SessionBus()

# ===================== 工具调用核心逻辑 =====================
def handle_tool_call(tool_name: str, params: Dict) -> Dict:
    """处理工具调用的核心逻辑"""
    try:
        if tool_name == "file_agent.search_file":
            search_path = params["search_path"]
            keyword = params["keyword"]
            recursive = params.get("recursive", True)
            result = file_agent.search_file(search_path, keyword, recursive)
            return {
                "success": result["status"] == "success",
                "result": result["data"],
                "error": result["msg"] if result["status"] == "error" else None
            }
        elif tool_name == "file_agent.move_to_trash":
            file_path = params["file_path"]
            result = file_agent.move_to_trash(file_path)
            return {
                "success": result["status"] == "success",
                "result": result["data"],
                "error": result["msg"] if result["status"] == "error" else None
            }
        else:
            return {"success": False, "error": f"工具不存在：{tool_name}"}
    except KeyError as e:
        return {"success": False, "error": f"缺少必填参数：{str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"工具调用失败：{str(e)}"}

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
            "agent_name": "file_agent",
            "bus_name": AGENT_BUS_NAME,
            "object_path": AGENT_OBJECT_PATH,
            "interface": AGENT_INTERFACE,
            "tools": FILE_AGENT_TOOLS
        })
        mcp_interface.RegisterAgent(register_data)
        print("[INFO] FileAgent已成功注册到MCP Server")
    except Exception as e:
        print(f"[ERROR] 注册到MCP Server失败：{str(e)}")

# ===================== 启动服务 =====================
if __name__ == "__main__":
    print("[INFO] 启动FileAgent MCP服务")
    
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