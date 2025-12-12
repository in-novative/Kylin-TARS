#!/usr/bin/env python3
"""
MonitorAgent MCP 服务 - 系统监控智能体

工具列表：
1. monitor_agent.get_system_status - 获取系统状态
2. monitor_agent.clean_background_process - 清理后台进程
3. monitor_agent.monitor_agent_status - 监控智能体状态
"""

import time
import json
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from typing import Dict, List
from gi.repository import GLib
from src.monitor_agent_logic import MonitorAgentLogic
from utils.set_logger import set_logger
from utils.get_config import get_master_config, get_child_config

# MonitorAgent DBus配置
AGENT_BUS_NAME = "com.mcp.agent.monitor"
AGENT_OBJECT_PATH = "/com/mcp/agent/monitor"
AGENT_INTERFACE = "com.mcp.agent.monitor.Interface"

# 工具元数据定义
MONITOR_AGENT_TOOLS: List[Dict] = [
    {
        "name": "monitor_agent.get_system_status",
        "description": "获取系统状态（CPU/内存/磁盘占用）",
        "parameters": {"type": "object", "properties": {}},
        "permission": "normal"
    },
    {
        "name": "monitor_agent.clean_background_process",
        "description": "清理后台冗余进程",
        "parameters": {
            "type": "object",
            "properties": {
                "process_name": {"type": "string", "description": "进程名称（可选）"}
            }
        },
        "permission": "normal"
    },
    {
        "name": "monitor_agent.monitor_agent_status",
        "description": "查询所有MCP子智能体在线状态",
        "parameters": {"type": "object", "properties": {}},
        "permission": "normal"
    }
]

DBusGMainLoop(set_as_default=True)
monitor_agent = MonitorAgentLogic()
bus = dbus.SessionBus()

def handle_tool_call(tool_name: str, params: Dict) -> Dict:
    """处理工具调用"""
    try:
        if tool_name == "monitor_agent.get_system_status":
            result = monitor_agent.get_system_status()
        elif tool_name == "monitor_agent.clean_background_process":
            result = monitor_agent.clean_background_process(params.get("process_name"))
        elif tool_name == "monitor_agent.monitor_agent_status":
            result = monitor_agent.monitor_agent_status()
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
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"工具调用失败：{e}"
        })

def message_handler(bus, message):
    """处理 D-Bus 消息"""
    if not isinstance(message, dbus.lowlevel.MethodCallMessage):
        return
    if message.get_interface() != AGENT_INTERFACE:
        return
    
    method_name = message.get_member()
    if method_name == "Ping":
        return json.dumps({
            "status": "ok",
            "timestamp": time.time(),
            "service": "Monitor Agent"
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
    
    try:
        tool_name, params_json = message.get_args_list()
        params = json.loads(params_json)
        result = handle_tool_call(tool_name, params)
        reply = dbus.lowlevel.MethodReturnMessage(message)
        reply.append(dbus.String(json.dumps(result)))
        bus.send(reply)
    except Exception as e:
        bus.send(dbus.lowlevel.ErrorMessage(message, "org.freedesktop.DBus.Error.Failed", str(e)))

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
        interface = dbus.Interface(mcp_proxy, DBUS_INTERFACE_NAME)
        
        register_data = json.dumps({
            "name": "monitor_agent",
            "service": AGENT_BUS_NAME,
            "path": AGENT_OBJECT_PATH,
            "interface": AGENT_INTERFACE,
            "tools": MONITOR_AGENT_TOOLS
        })
        
        result = json.loads(interface.AgentRegister(register_data))
        if result.get("success"):
            logger.info("MonitorAgent 已成功注册到 MCP Server")
        else:
            logger.error(f" 注册失败: {result.get('error')}")
    except Exception as e:
        logger.error(f" 注册到 MCP Server 失败：{e}")

if __name__ == "__main__":
    logger = set_logger("monitor_agent")
    logger.info(" 启动 MonitorAgent MCP 服务")
    bus.request_name(AGENT_BUS_NAME)

    bus.add_message_filter(message_handler)

    register_to_mcp(logger)
    
    loop = GLib.MainLoop()
    try:
        logger.info(" MonitorAgent 服务已启动，等待调用...")
        loop.run()
    except KeyboardInterrupt:
        logger.info("MonitorAgent 服务已停止")
        loop.quit()

