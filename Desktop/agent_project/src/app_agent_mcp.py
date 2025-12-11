#!/usr/bin/env python3
"""
AppAgent MCP 服务 - 应用管理智能体

工具列表：
1. app_agent.find_app - 查找应用
2. app_agent.launch_app - 启动应用
3. app_agent.close_app - 关闭应用
4. app_agent.list_running_apps - 列出运行中的应用
5. app_agent.is_app_running - 检查应用是否运行
"""

import sys
import os
import json
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from typing import Dict, List
from gi.repository import GLib
from src.app_agent_logic import AppAgentLogic
from utils.set_logger import set_logger
from utils.get_config import get_master_config, get_child_config

# ===================== AppAgent DBus配置 =====================
AGENT_BUS_NAME = "com.mcp.agent.app"
AGENT_OBJECT_PATH = "/com/mcp/agent/app"
AGENT_INTERFACE = "com.mcp.agent.app.Interface"

# ===================== 工具元数据定义 =====================
APP_AGENT_TOOLS: List[Dict] = [
    {
        "name": "app_agent.find_app",
        "description": "查找应用路径或桌面文件",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "应用名称（如 firefox, chrome）"}
            },
            "required": ["app_name"]
        },
        "permission": "normal"
    },
    {
        "name": "app_agent.launch_app",
        "description": "启动指定应用",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "应用名称"},
                "args": {"type": "array", "items": {"type": "string"}, "description": "启动参数（可选）"}
            },
            "required": ["app_name"]
        },
        "permission": "normal"
    },
    {
        "name": "app_agent.close_app",
        "description": "关闭指定应用",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "应用名称"},
                "force": {"type": "boolean", "description": "是否强制关闭（默认false）"}
            },
            "required": ["app_name"]
        },
        "permission": "normal"
    },
    {
        "name": "app_agent.list_running_apps",
        "description": "列出当前运行的所有应用",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "permission": "normal"
    },
    {
        "name": "app_agent.is_app_running",
        "description": "检查指定应用是否正在运行",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "应用名称"}
            },
            "required": ["app_name"]
        },
        "permission": "normal"
    },
    {
        "name": "app_agent.app_quick_operation",
        "description": "应用快捷操作（支持URL参数，如firefox https://www.baidu.com）",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "应用名称（firefox/chrome/微信/终端/文件等）"},
                "url": {"type": "string", "description": "URL地址（浏览器应用）"},
                "args": {"type": "array", "items": {"type": "string"}, "description": "启动参数（可选）"}
            },
            "required": ["app_name"]
        },
        "permission": "normal",
        "extend_type": "new"
    }
]

# ===================== 初始化 =====================
DBusGMainLoop(set_as_default=True)
app_agent = AppAgentLogic()
bus = dbus.SessionBus()

# ===================== 工具调用处理 =====================
def handle_tool_call(tool_name: str, params: Dict) -> Dict:
    """处理工具调用"""
    try:
        if tool_name == "app_agent.find_app":
            result = app_agent.find_app(params["app_name"])
        elif tool_name == "app_agent.launch_app":
            result = app_agent.launch_app(
                app_name=params["app_name"],
                args=params.get("args", [])
            )
        elif tool_name == "app_agent.close_app":
            result = app_agent.close_app(
                app_name=params["app_name"],
                force=params.get("force", False)
            )
        elif tool_name == "app_agent.list_running_apps":
            result = app_agent.list_running_apps()
        elif tool_name == "app_agent.is_app_running":
            result = app_agent.is_app_running(params["app_name"])
        elif tool_name == "app_agent.app_quick_operation":
            result = app_agent.app_quick_operation(
                app_name=params["app_name"],
                url=params.get("url"),
                args=params.get("args", [])
            )
        else:
            return json.dumps({
                "success": False,
                "error": f"未知工具：{tool_name}"
            })
        
        return json.dumps({
            "success": result["status"] == "success",
            "result": result["data"],
            "msg": result["msg"],
            "screenshot_path": result.get("screenshot_path"),
            "error": result["msg"] if result["status"] == "error" else None
        })
    except KeyError as e:
        return json.dumps({
            "success": False,
            "error": f"缺少必填参数：{e}"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"工具调用失败：{e}"
        })

# ===================== D-Bus 消息处理 =====================
def message_handler(bus, message):
    """处理 D-Bus 消息"""
    if not isinstance(message, dbus.lowlevel.MethodCallMessage):
        return
    if message.get_interface() != AGENT_INTERFACE:
        return
    
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
    
    try:
        tool_name, params_json = message.get_args_list()
        params = json.loads(params_json)
        
        result = handle_tool_call(tool_name, params)
        
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

# ===================== MCP 注册 =====================
def register_to_mcp(logger):
    """注册到 MCP Server"""
    MASTERAGENT = get_master_config()
    DBUS_SERVICE_NAME = MASTERAGENT["SERVICE_NAME"]
    DBUS_OBJECT_PATH = MASTERAGENT["OBJECT_PATH"]
    DBUS_INTERFACE_NAME = MASTERAGENT["INTERFACE_NAME"]
    try:
        if not bus.name_has_owner(DBUS_SERVICE_NAME):
            logger.warning(f"MCP Server ({DBUS_SERVICE_NAME}) 未启动，跳过注册")
            return
        
        mcp_proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        mcp_interface = dbus.Interface(mcp_proxy, DBUS_INTERFACE_NAME)
        
        register_data = json.dumps({
            "name": "app_agent",
            "service": AGENT_BUS_NAME,
            "path": AGENT_OBJECT_PATH,
            "interface": AGENT_INTERFACE,
            "tools": APP_AGENT_TOOLS
        })
        
        result = json.loads(mcp_interface.AgentRegister(register_data))
        if result.get("success"):
            logger.info("AppAgent 已成功注册到 MCP Server")
            logger.info(f"工具: {[t['name'] for t in APP_AGENT_TOOLS]}")
        else:
            logger.error(f"注册失败: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"注册到 MCP Server 失败：{e}")

# ===================== 启动服务 =====================
if __name__ == "__main__":
    logger = set_logger("app_agent")
    logger.info("启动 AppAgent MCP 服务")
    
    # 请求 D-Bus 服务名
    bus.request_name(AGENT_BUS_NAME)
    
    # 添加消息处理器
    bus.add_message_filter(message_handler)
    
    # 注册到 MCP
    register_to_mcp(logger)
    
    # 启动主循环
    loop = GLib.MainLoop()
    try:
        logger.info("AppAgent 服务已启动，等待调用...")
        loop.run()
    except KeyboardInterrupt:
        logger.info("AppAgent 服务已停止")
        loop.quit()