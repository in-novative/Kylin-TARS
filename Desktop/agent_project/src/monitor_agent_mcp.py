#!/usr/bin/env python3
"""
MonitorAgent MCP 服务 - 系统监控智能体

工具列表：
1. monitor_agent.get_system_status - 获取系统状态
2. monitor_agent.clean_background_process - 清理后台进程
3. monitor_agent.monitor_agent_status - 监控智能体状态

作者：GUI Agent Team
"""

import sys
import os
import json
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from typing import Dict, List
from gi.repository import GLib

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.monitor_agent_logic import MonitorAgentLogic

# MCP Server DBus配置
MCP_BUS_NAME = "com.kylin.ai.mcp.MasterAgent"
MCP_OBJECT_PATH = "/com/kylin/ai/mcp/MasterAgent"
MCP_INTERFACE = "com.kylin.ai.mcp.MasterAgent"

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
            return {"success": False, "error": f"未知工具：{tool_name}"}
        
        return {
            "success": result["status"] == "success",
            "result": result["data"],
            "msg": result["msg"],
            "screenshot_path": result.get("screenshot_path"),
            "error": result["msg"] if result["status"] == "error" else None
        }
    except Exception as e:
        return {"success": False, "error": f"工具调用失败：{e}"}

def message_handler(bus, message):
    """处理 D-Bus 消息"""
    if message.get_type() != dbus.lowlevel.METHOD_CALL:
        return
    if message.get_interface() != AGENT_INTERFACE:
        return
    
    method_name = message.get_member()
    if method_name != "ToolsCall":
        bus.send(dbus.lowlevel.ErrorMessage(message, "org.freedesktop.DBus.Error.UnknownMethod", f"Unknown method: {method_name}"))
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

def register_to_mcp():
    """注册到 MCP Server"""
    try:
        if not bus.name_has_owner(MCP_BUS_NAME):
            print(f"[WARNING] MCP Server ({MCP_BUS_NAME}) 未启动，跳过注册")
            return
        
        mcp_proxy = bus.get_object(MCP_BUS_NAME, MCP_OBJECT_PATH)
        mcp_interface = dbus.Interface(mcp_proxy, MCP_INTERFACE)
        
        register_data = json.dumps({
            "name": "monitor_agent",
            "agent_name": "monitor_agent",
            "bus_name": AGENT_BUS_NAME,
            "service": AGENT_BUS_NAME,
            "object_path": AGENT_OBJECT_PATH,
            "path": AGENT_OBJECT_PATH,
            "interface": AGENT_INTERFACE,
            "tools": MONITOR_AGENT_TOOLS
        })
        
        result = json.loads(mcp_interface.AgentRegister(register_data))
        if result.get("success"):
            print("[INFO] MonitorAgent 已成功注册到 MCP Server")
        else:
            print(f"[ERROR] 注册失败: {result.get('error')}")
    except Exception as e:
        print(f"[ERROR] 注册到 MCP Server 失败：{e}")

if __name__ == "__main__":
    print("[INFO] 启动 MonitorAgent MCP 服务")
    bus.request_name(AGENT_BUS_NAME)
    bus.add_message_filter(message_handler)
    register_to_mcp()
    
    loop = GLib.MainLoop()
    try:
        print("[INFO] MonitorAgent 服务已启动，等待调用...")
        loop.run()
    except KeyboardInterrupt:
        print("\n[INFO] MonitorAgent 服务已停止")
        loop.quit()

