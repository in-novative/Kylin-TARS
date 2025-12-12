#!/usr/bin/env python3
"""
MediaAgent MCP 服务 - 媒体控制智能体

工具列表：
1. media_agent.play_media - 播放媒体文件
2. media_agent.media_control - 媒体控制
3. media_agent.capture_media_frame - 截图播放帧
"""

import time
import json
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from typing import Dict, List
from gi.repository import GLib
from src.media_agent_logic import MediaAgentLogic
from utils.set_logger import set_logger
from utils.get_config import get_master_config, get_child_config

# MediaAgent DBus配置
AGENT_BUS_NAME = "com.mcp.agent.media"
AGENT_OBJECT_PATH = "/com/mcp/agent/media"
AGENT_INTERFACE = "com.mcp.agent.media.Interface"

# 工具元数据定义
MEDIA_AGENT_TOOLS: List[Dict] = [
    {
        "name": "media_agent.play_media",
        "description": "播放音频/视频文件",
        "parameters": {
            "type": "object",
            "properties": {
                "media_path": {"type": "string", "description": "媒体文件路径"}
            },
            "required": ["media_path"]
        },
        "permission": "normal"
    },
    {
        "name": "media_agent.media_control",
        "description": "控制媒体播放状态",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作类型（play/pause/stop/fullscreen）"}
            },
            "required": ["action"]
        },
        "permission": "normal"
    },
    {
        "name": "media_agent.capture_media_frame",
        "description": "截图当前播放帧",
        "parameters": {"type": "object", "properties": {}},
        "permission": "normal"
    }
]

DBusGMainLoop(set_as_default=True)
media_agent = MediaAgentLogic()
bus = dbus.SessionBus()

def handle_tool_call(tool_name: str, params: Dict) -> Dict:
    """处理工具调用"""
    try:
        if tool_name == "media_agent.play_media":
            result = media_agent.play_media(params["media_path"])
        elif tool_name == "media_agent.media_control":
            result = media_agent.media_control(params["action"])
        elif tool_name == "media_agent.capture_media_frame":
            result = media_agent.capture_media_frame()
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
            "service": "Media Agent"
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
        mcp_interface = dbus.Interface(mcp_proxy, DBUS_INTERFACE_NAME)
        
        register_data = json.dumps({
            "name": "media_agent",
            "service": AGENT_BUS_NAME,
            "path": AGENT_OBJECT_PATH,
            "interface": AGENT_INTERFACE,
            "tools": MEDIA_AGENT_TOOLS
        })
        
        result = json.loads(mcp_interface.AgentRegister(register_data))
        if result.get("success") is True:
            logger.info("MediaAgent 已成功注册到 MCP Server")
        else:
            logger.error(f"MediaAgent 注册失败: {result.get('error')}")
    except Exception as e:
        logger.warnning(f"注册到 MCP Server 失败：{e}")

if __name__ == "__main__":
    logger = set_logger("media_agent")
    logger.info("启动 MediaAgent MCP 服务")
    bus.request_name(AGENT_BUS_NAME)

    bus.add_message_filter(message_handler)

    register_to_mcp(logger)
    
    loop = GLib.MainLoop()
    try:
        logger.info("MediaAgent 服务已启动，等待调用...")
        loop.run()
    except KeyboardInterrupt:
        logger.info("MediaAgent 服务已停止")
        loop.quit()