#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for MCP Server
This script tests the basic functionality of the MCP Server
"""

import dbus
import json
import time
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MCP Test")

# DBus constants
DBUS_SERVICE_NAME = "com.kylin.ai.mcp.MasterAgent"
DBUS_OBJECT_PATH = "/com/kylin/ai/mcp/MasterAgent"
DBUS_INTERFACE_NAME = "com.kylin.ai.mcp.MasterAgent"

def test_info():
    """Test basic info of mcp_server"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        iface = dbus.Interface(proxy, DBUS_INTERFACE_NAME)

        print("bus type   :", iface.GetBusType())
        print("service    :", iface.GetServiceName())
        print("object path:", iface.GetObjectPath())
        print("interface  :", iface.GetInterfaceName())
        print("child svcs :", iface.GetChildAgentServices())
    except Exception as e:
        logger.error(f"Info test failed: {str(e)}")
        raise


def test_ping():
    """Test the Ping method"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        interface = dbus.Interface(proxy, DBUS_INTERFACE_NAME)
        
        result = interface.Ping()
        result_dict = json.loads(result)
        
        logger.info(f"Ping result: {result_dict}")
        assert result_dict["status"] == "ok", "Ping failed"
        logger.info("✓ Ping test passed")
        
    except Exception as e:
        logger.error(f"Ping test failed: {str(e)}")
        raise


def test_tools_list():
    """Test the ToolsList method"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        interface = dbus.Interface(proxy, DBUS_INTERFACE_NAME)
        
        result = interface.ToolsList()
        result_dict = json.loads(result)
        
        logger.info(f"ToolsList result: {result_dict}")
        assert result_dict["success"] == True, "ToolsList failed"
        assert "tools" in result_dict, "Tools list not found"
        
        logger.info(f"Found {len(result_dict['tools'])} tools:")
        for tool in result_dict["tools"]:
            if "." in tool:
                agent_name, tool_name = tool.split(".", 1)
            logger.info(f"find tool {tool_name} of agent {agent_name}")
        
        logger.info("✓ ToolsList test passed")
        
    except Exception as e:
        logger.error(f"ToolsList test failed: {str(e)}")
        raise


def test_tools_call():
    """Test the ToolsCall method with echo tool"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        interface = dbus.Interface(proxy, DBUS_INTERFACE_NAME)
        
        # Test echo tool
        test_message = "Hello, MCP Server!"
        parameters = {"message": test_message}
        
        result = interface.ToolsCall("echo", json.dumps(parameters))
        result_dict = json.loads(result)
        
        logger.info(f"ToolsCall result: Er{result_dict}")
        assert result_dict["success"] == True, "ToolsCall failed"
        assert result_dict["result"]["echo"] == test_message, "Echo message mismatch"
        
        logger.info("✓ ToolsCall test passed")
        
    except Exception as e:
        logger.error(f"ToolsCall test failed: {str(e)}")
        raise


def test_agent_register(agent_info):
    """Test the AgentRegister method"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        interface = dbus.Interface(proxy, DBUS_INTERFACE_NAME)
        
        # Create a mock agent info
        result = interface.AgentRegister(json.dumps(agent_info))
        result_dict = json.loads(result)
        
        logger.info(f"AgentRegister result: {result_dict}")
        assert result_dict["success"] == True, "AgentRegister failed"
        
        logger.info("✓ AgentRegister test passed")
        
    except Exception as e:
        logger.error(f"AgentRegister test failed: {str(e)}")
        raise


def test_agents_list(agent_name):
    """Test the AgentsList method"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        interface = dbus.Interface(proxy, DBUS_INTERFACE_NAME)
        
        result = interface.AgentsList()
        result_dict = json.loads(result)
        
        logger.info(f"AgentsList result: {result_dict}")
        assert result_dict["success"] == True, "AgentsList failed"
        assert "agents" in result_dict, "Agents list not found"
        
        # Check if our test agent is in the list
        test_agent_found = False
        for agent in result_dict["agents"]:
            logger.info(f"  - {agent['name']}: {agent['service']} (alive: {agent['is_alive']})")
            if agent["name"] == agent_name:
                test_agent_found = True
                assert agent["is_alive"] == True, "Test agent should be alive"
        
        assert test_agent_found, f"Test agent '{agent_name}' not found in agents list"
        logger.info("✓ AgentsList test passed")
        
    except Exception as e:
        logger.error(f"AgentsList test failed: {str(e)}")
        raise


def test_agent_unregister(agent_name):
    """Test the AgentUnregister method"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        interface = dbus.Interface(proxy, DBUS_INTERFACE_NAME)
        
        result = interface.AgentUnregister(agent_name)
        result_dict = json.loads(result)
        
        logger.info(f"AgentUnregister result: {result_dict}")
        assert result_dict["success"] == True, "AgentUnregister failed"
        
        logger.info("✓ AgentUnregister test passed")
        
    except Exception as e:
        logger.error(f"AgentUnregister test failed: {str(e)}")
        raise


def test_tools_list_after_agent_register(tool_name):
    """Test that agent tools appear in ToolsList"""
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
        interface = dbus.Interface(proxy, DBUS_INTERFACE_NAME)
        
        result = interface.ToolsList()
        result_dict = json.loads(result)

        # Check if agent tool is in the list
        agent_tool_found = False
        for tool in result_dict["tools"]:
            if tool == tool_name:
                agent_tool_found = True
                break
        
        assert agent_tool_found, f"Agent tool '{agent_name}.test_tool' not found in tools list"
        logger.info("✓ ToolsList after agent register test passed")
        
    except Exception as e:
        logger.error(f"ToolsList after agent register test failed: {str(e)}")
        raise


def main():
    """Run all tests"""
    logger.info("Starting MCP Server tests...")

    agent_info = {
            "name": "FileAgent",
            "service": "com.kylin.ai.mcp.FileAgent",
            "path": "/com/kylin/ai/mcp/FileAgent",
            "interface": "com.kylin.ai.mcp.FileAgent",
            "tools": [
                {
                    "name": "FilEAgent.search_file",
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
                    "name": "FileAgent.move_to_trash",
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
        }
    
    try:
        # Test 1: Ping
        test_ping()
        
        # Test 2: ToolsList
        test_tools_list()
        
        # Test 3: ToolsCall
        test_tools_call()
        
        # Test 4: AgentRegister
        test_agent_register(agent_info)
        
        # Test 5: ToolsList after agent register
        test_tools_list_after_agent_register(agent_info["tools"][0]["name"])
        
        # Test 6: AgentsList
        test_agents_list(agent_info["name"])
        
        # Test 7: AgentUnregister
        test_agent_unregister(agent_info["name"])
        
        logger.info("🎉 All tests passed!")
        
    except Exception as e:
        logger.error(f"Tests failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())