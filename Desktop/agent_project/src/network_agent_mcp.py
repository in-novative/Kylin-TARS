#!/usr/bin/env python3
"""
NetworkAgent MCP 服务 - 网络管理智能体

工具列表：
1. network_agent.list_wifi - 列出可用WiFi
2. network_agent.connect_wifi - 连接WiFi
3. network_agent.disconnect_wifi - 断开WiFi
4. network_agent.get_wifi_status - 获取WiFi状态
5. network_agent.set_proxy - 设置代理 (敏感)
6. network_agent.clear_proxy - 清除代理 (敏感)
7. network_agent.get_proxy_status - 获取代理状态
"""

import sys
import os
import json
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from typing import Dict, List
from gi.repository import GLib
from src.network_agent_logic import NetworkAgentLogic
from utils.set_logger import set_logger
from utils.get_config import get_master_config, get_child_config

# ===================== NetworkAgent DBus配置 =====================
AGENT_BUS_NAME = "com.mcp.agent.network"
AGENT_OBJECT_PATH = "/com/mcp/agent/network"
AGENT_INTERFACE = "com.mcp.agent.network.Interface"

# ===================== 工具元数据定义 =====================
NETWORK_AGENT_TOOLS: List[Dict] = [
    {
        "name": "network_agent.list_wifi",
        "description": "列出可用的WiFi网络",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "permission": "normal"
    },
    {
        "name": "network_agent.connect_wifi",
        "description": "连接指定的WiFi网络",
        "parameters": {
            "type": "object",
            "properties": {
                "ssid": {"type": "string", "description": "WiFi名称"},
                "password": {"type": "string", "description": "WiFi密码（可选）"}
            },
            "required": ["ssid"]
        },
        "permission": "normal"
    },
    {
        "name": "network_agent.disconnect_wifi",
        "description": "断开当前WiFi连接",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "permission": "normal"
    },
    {
        "name": "network_agent.get_wifi_status",
        "description": "获取当前WiFi连接状态",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "permission": "normal"
    },
    {
        "name": "network_agent.set_proxy",
        "description": "设置系统代理（敏感操作，需确认）",
        "parameters": {
            "type": "object",
            "properties": {
                "http_proxy": {"type": "string", "description": "HTTP代理地址"},
                "https_proxy": {"type": "string", "description": "HTTPS代理地址"},
                "socks_proxy": {"type": "string", "description": "SOCKS代理地址"},
                "user_confirm": {"type": "boolean", "description": "用户确认"}
            }
            },
        "permission": "sensitive"
    },
    {
        "name": "network_agent.clear_proxy",
        "description": "清除系统代理（敏感操作，需确认）",
        "parameters": {
            "type": "object",
            "properties": {
                "user_confirm": {"type": "boolean", "description": "用户确认"}
        }
        },
        "permission": "sensitive"
    },
    {
        "name": "network_agent.get_proxy_status",
        "description": "获取当前代理设置",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "permission": "normal"
    },
    {
        "name": "network_agent.speed_test",
        "description": "网络测速（支持快速/完整测速切换）",
        "parameters": {
            "type": "object",
            "properties": {
                "test_type": {"type": "string", "enum": ["quick", "full"], "default": "quick", "description": "测速类型（quick约10秒，full约30秒）"}
            }
        },
        "permission": "normal",
        "extend_type": "new"
    },
    {
        "name": "network_agent.get_network_status",
        "description": "获取综合网络状态（WiFi/代理/IP）",
        "parameters": {
            "type": "object",
            "properties": {}
        },
        "permission": "normal"
    }
]

# ===================== 初始化 =====================
DBusGMainLoop(set_as_default=True)
network_agent = NetworkAgentLogic()
bus = dbus.SessionBus()

# ===================== 工具调用处理 =====================
def handle_tool_call(tool_name: str, params: Dict) -> Dict:
    """处理工具调用"""
    try:
        # WiFi 功能
        if tool_name == "network_agent.list_wifi":
            result = network_agent.list_wifi()
        elif tool_name == "network_agent.connect_wifi":
            result = network_agent.connect_wifi(
                ssid=params["ssid"],
                password=params.get("password")
            )
        elif tool_name == "network_agent.disconnect_wifi":
            result = network_agent.disconnect_wifi()
        elif tool_name == "network_agent.get_wifi_status":
            result = network_agent.get_wifi_status()
        # 代理功能（敏感操作需确认）
        elif tool_name == "network_agent.set_proxy":
            if not params.get("user_confirm", False):
                return json.dumps({
                    "success": False,
                    "error": "敏感操作需要用户确认（user_confirm=true）"
                })
            result = network_agent.set_proxy(
                http_proxy=params.get("http_proxy"),
                https_proxy=params.get("https_proxy"),
                socks_proxy=params.get("socks_proxy")
            )
        elif tool_name == "network_agent.clear_proxy":
            if not params.get("user_confirm", False):
                return json.dumps({
                    "success": False,
                    "error": "敏感操作需要用户确认（user_confirm=true）"
                })
            result = network_agent.clear_proxy()
        elif tool_name == "network_agent.get_proxy_status":
            result = network_agent.get_proxy_status()
        elif tool_name == "network_agent.speed_test":
            result = network_agent.speed_test(test_type=params.get("test_type", "quick"))
        elif tool_name == "network_agent.get_network_status":
            result = network_agent.get_network_status()
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
            logger(f"[WARNING] MCP Server ({DBUS_SERVICE_NAME}) 未启动，跳过注册")
            return
        
        mcp_proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        DBUS_INTERFACE_NAME = dbus.Interface(mcp_proxy, DBUS_INTERFACE_NAME)
        
        register_data = json.dumps({
            "name": "network_agent",
            "service": AGENT_BUS_NAME,
            "path": AGENT_OBJECT_PATH,
            "interface": AGENT_INTERFACE,
            "tools": NETWORK_AGENT_TOOLS
        })
        
        result = json.loads(DBUS_INTERFACE_NAME.AgentRegister(register_data))
        if result.get("success"):
            logger.info("NetworkAgent 已成功注册到 MCP Server")
            logger.info(f"工具: {[t['name'] for t in NETWORK_AGENT_TOOLS]}")
        else:
            logger.error(f"注册失败: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"[ERROR] 注册到 MCP Server 失败：{e}")

# ===================== 启动服务 =====================
if __name__ == "__main__":
    logger = set_logger("monitor_agent")
    logger.info("启动 NetworkAgent MCP 服务")
    
    # 请求 D-Bus 服务名
    bus.request_name(AGENT_BUS_NAME)
    
    # 添加消息处理器
    bus.add_message_filter(message_handler)
    
    # 注册到 MCP
    register_to_mcp(logger)
    
    # 启动主循环
    loop = GLib.MainLoop()
    try:
        logger.info("NetworkAgent 服务已启动，等待调用...")
        loop.run()
    except KeyboardInterrupt:
        logger.info("NetworkAgent 服务已停止")
        loop.quit()
