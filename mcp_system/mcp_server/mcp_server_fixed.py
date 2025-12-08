#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Server - Master Control Protocol Server Implementation (Fixed Version)

修复版MCP Server，解决原版中的语法错误：
1. 第112行：修复三元运算符语法
2. 第134行：修复函数返回类型注解
"""

import dbus
import dbus.service
import dbus.mainloop.glib
import json
import logging
import time
from threading import Thread
from gi.repository import GLib
from typing import Dict, List, Any, Optional, Callable

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mcp_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MCP Server")

# DBus constants
DBUS_SERVICE_NAME = "com.kylin.ai.mcp.MasterAgent"
DBUS_OBJECT_PATH = "/com/kylin/ai/mcp/MasterAgent"
DBUS_INTERFACE_NAME = "com.kylin.ai.mcp.MasterAgent"


class MCPTool:
    """Represents a tool that can be called via MCP"""
    
    def __init__(self, name: str, description: str, handler: Callable, 
                 parameters: Dict[str, Any], examples: List[Dict[str, Any]]):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters
        self.examples = examples
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary format"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "examples": self.examples,
            "agent": ""  # 本地工具无 agent
        }
    
    def call(self, **kwargs) -> Dict[str, Any]:
        """Call the tool with given parameters"""
        try:
            result = self.handler(**kwargs)
            return {
                "success": True,
                "result": result,
                "error": None
            }
        except Exception as e:
            logger.error(f"Error calling tool {self.name}: {str(e)}")
            return {
                "success": False,
                "result": None,
                "error": str(e)
            }


class MCPServer(dbus.service.Object):
    """MCP Server implementation using DBus"""
    
    def __init__(self, bus_type: str = "session"):
        """Initialize MCP Server"""
        # Initialize DBus connection
        if bus_type == "session":
            self._bus = dbus.SessionBus()
        else:
            self._bus = dbus.SystemBus()
        
        self._bus_type = bus_type
        
        bus_name = dbus.service.BusName(DBUS_SERVICE_NAME, bus=self._bus)
        dbus.service.Object.__init__(self, bus_name, DBUS_OBJECT_PATH)
        
        # Dictionary to store available tools
        self.tools: Dict[str, MCPTool] = {}
        
        # Dictionary to store child agents
        self.child_agents: Dict[str, Dict[str, Any]] = {}
        
        # Heartbeat timestamp
        self.last_heartbeat = time.time()
        
        logger.info("MCP Server initialized and registered on DBus")
    
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def DBusType(self) -> str:
        """Return type of DBus (session or system)"""
        self.last_heartbeat = time.time()
        # 修复: 使用正确的 Python 三元运算符语法
        return json.dumps({
            "type": self._bus_type
        })

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def ServiceName(self) -> str:
        """Return name of DBus Service"""
        self.last_heartbeat = time.time()
        return json.dumps({
            "name": DBUS_SERVICE_NAME
        })

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def ObjectPath(self) -> str:
        """Return path of DBus object"""
        self.last_heartbeat = time.time()
        return json.dumps({
            "path": DBUS_OBJECT_PATH
        })

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def InterfaceName(self) -> str:  # 修复: 添加完整的返回类型注解
        """Return name of DBus interface"""
        self.last_heartbeat = time.time()
        return json.dumps({
            "name": DBUS_INTERFACE_NAME
        })

    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def Ping(self) -> str:
        """Ping method for health check"""
        self.last_heartbeat = time.time()
        return json.dumps({
            "status": "ok",
            "timestamp": self.last_heartbeat,
            "service": "MCP Master Agent"
        })
    
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def ToolsList(self) -> str:
        """List all available tools"""
        self.last_heartbeat = time.time()
        
        try:
            # Get tools from this agent
            tools_list = [tool.to_dict() for tool in self.tools.values()]
            
            # Get tools from child agents
            for agent_name, agent_info in self.child_agents.items():
                if "tools" in agent_info:
                    for tool in agent_info["tools"]:
                        tool_copy = tool.copy()
                        tool_copy["agent"] = agent_name
                        tools_list.append(tool_copy)
            
            return json.dumps({
                "success": True,
                "tools": tools_list,
                "total": len(tools_list)
            })
        except Exception as e:
            logger.error(f"Error in ToolsList: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='ss', out_signature='s')
    def ToolsCall(self, tool_name: str, parameters_json: str) -> str:
        """Call a specific tool with parameters"""
        self.last_heartbeat = time.time()
        
        try:
            parameters = json.loads(parameters_json)
            logger.info(f"Tool call request: {tool_name} with parameters: {parameters}")
            
            # Check if it's a child agent tool (contains agent prefix)
            if "." in tool_name:
                agent_name = tool_name.split(".")[0]
                
                # 查找匹配的子智能体
                matching_agent = None
                for registered_name, agent_info in self.child_agents.items():
                    if registered_name.lower() == agent_name.lower() or \
                       agent_name in registered_name or \
                       registered_name in agent_name:
                        matching_agent = (registered_name, agent_info)
                        break
                
                if matching_agent:
                    return self._call_child_agent_tool(matching_agent[0], tool_name, parameters)
            
            # Try local tool
            if tool_name in self.tools:
                result = self.tools[tool_name].call(**parameters)
                return json.dumps(result)
            
            # Tool not found
            return json.dumps({
                "success": False,
                "error": f"Tool '{tool_name}' not found"
            })
                
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Invalid JSON parameters: {str(e)}"
            })
        except Exception as e:
            logger.error(f"Error in ToolsCall: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='s', out_signature='s')
    def AgentRegister(self, agent_info_json: str) -> str:
        """Register a child agent"""
        self.last_heartbeat = time.time()
        
        try:
            agent_info = json.loads(agent_info_json)
            
            # 支持两种字段名：name 或 agent_name
            agent_name = agent_info.get("name") or agent_info.get("agent_name")
            if not agent_name:
                return json.dumps({
                    "success": False,
                    "error": "Missing required field: name or agent_name"
                })
            
            # 标准化字段名
            agent_info["name"] = agent_name
            
            # 支持两种字段名：service 或 bus_name
            if "bus_name" in agent_info and "service" not in agent_info:
                agent_info["service"] = agent_info["bus_name"]
            
            # 支持两种字段名：path 或 object_path
            if "object_path" in agent_info and "path" not in agent_info:
                agent_info["path"] = agent_info["object_path"]
            
            # Register the agent
            self.child_agents[agent_name] = {
                **agent_info,
                "last_seen": time.time(),
                "is_alive": True
            }
            
            logger.info(f"Child agent registered: {agent_name}")
            logger.info(f"  Tools: {[t.get('name', 'N/A') for t in agent_info.get('tools', [])]}")
            
            return json.dumps({
                "success": True,
                "message": f"Agent '{agent_name}' registered successfully"
            })
            
        except json.JSONDecodeError as e:
            return json.dumps({
                "success": False,
                "error": f"Invalid JSON agent info: {str(e)}"
            })
        except Exception as e:
            logger.error(f"Error in AgentRegister: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='s', out_signature='s')
    def AgentUnregister(self, agent_name: str) -> str:
        """Unregister a child agent"""
        self.last_heartbeat = time.time()
        
        try:
            if agent_name in self.child_agents:
                del self.child_agents[agent_name]
                logger.info(f"Child agent unregistered: {agent_name}")
                return json.dumps({
                    "success": True,
                    "message": f"Agent '{agent_name}' unregistered successfully"
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Agent '{agent_name}' not found"
                })
        except Exception as e:
            logger.error(f"Error in AgentUnregister: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def AgentsList(self) -> str:
        """List all registered child agents"""
        self.last_heartbeat = time.time()
        
        try:
            agents_list = []
            current_time = time.time()
            
            for agent_name, agent_info in self.child_agents.items():
                # Check if agent is alive (last seen within 60 seconds)
                is_alive = (current_time - agent_info.get("last_seen", 0)) < 60
                
                agents_list.append({
                    "name": agent_name,
                    "service": agent_info.get("service", agent_info.get("bus_name", "")),
                    "path": agent_info.get("path", agent_info.get("object_path", "")),
                    "interface": agent_info.get("interface", ""),
                    "tools": agent_info.get("tools", []),
                    "tools_count": len(agent_info.get("tools", [])),
                    "last_seen": agent_info.get("last_seen", 0),
                    "is_alive": is_alive
                })
            
            return json.dumps({
                "success": True,
                "agents": agents_list,
                "total": len(agents_list)
            })
        except Exception as e:
            logger.error(f"Error in AgentsList: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def _call_child_agent_tool(self, agent_name: str, tool_name: str, parameters: Dict[str, Any]) -> str:
        """Call a tool on a child agent"""
        try:
            agent_info = self.child_agents[agent_name]
            
            # Update last_seen
            agent_info["last_seen"] = time.time()
            
            # Connect to the child agent's DBus service
            proxy = self._bus.get_object(
                agent_info.get("service", agent_info.get("bus_name")), 
                agent_info.get("path", agent_info.get("object_path"))
            )
            interface = dbus.Interface(proxy, agent_info["interface"])
            
            # Call the tool on the child agent
            result = interface.ToolsCall(tool_name, json.dumps(parameters))
            return str(result)
            
        except dbus.DBusException as e:
            logger.error(f"DBus error calling child agent {agent_name}: {str(e)}")
            return json.dumps({
                "success": False,
                "error": f"DBus error: {str(e)}"
            })
        except Exception as e:
            logger.error(f"Error calling child agent {agent_name}: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    def add_tool(self, tool: MCPTool):
        """Add a tool to the server"""
        self.tools[tool.name] = tool
        logger.info(f"Tool added: {tool.name}")
    
    def remove_tool(self, tool_name: str):
        """Remove a tool from the server"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Tool removed: {tool_name}")
    
    def start_heartbeat_monitor(self):
        """Start monitoring agent heartbeats"""
        def monitor():
            while True:
                time.sleep(30)
                self._check_agent_heartbeats()
        
        heartbeat_thread = Thread(target=monitor, daemon=True)
        heartbeat_thread.start()
        logger.info("Heartbeat monitor started")
    
    def _check_agent_heartbeats(self):
        """Check and mark inactive agents"""
        current_time = time.time()
        
        for agent_name, agent_info in self.child_agents.items():
            if (current_time - agent_info.get("last_seen", 0)) > 60:
                agent_info["is_alive"] = False
                logger.warning(f"Agent marked as inactive: {agent_name}")


def main():
    """Main function to start the MCP Server"""
    try:
        # Initialize DBus main loop
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        
        # Create MCP Server instance
        server = MCPServer()
        
        # Add some example tools
        def example_echo_handler(message: str) -> Dict[str, Any]:
            return {"echo": message, "timestamp": time.time()}
        
        echo_tool = MCPTool(
            name="echo",
            description="Echo back the provided message",
            handler=example_echo_handler,
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The message to echo"
                    }
                },
                "required": ["message"]
            },
            examples=[
                {
                    "name": "Echo Example",
                    "parameters": {"message": "Hello, World!"}
                }
            ]
        )
        server.add_tool(echo_tool)
        
        # Start heartbeat monitor
        server.start_heartbeat_monitor()
        
        logger.info("=" * 60)
        logger.info("MCP Server started successfully")
        logger.info("=" * 60)
        logger.info(f"Service name: {DBUS_SERVICE_NAME}")
        logger.info(f"Object path: {DBUS_OBJECT_PATH}")
        logger.info(f"Interface name: {DBUS_INTERFACE_NAME}")
        logger.info("")
        logger.info("等待子智能体注册...")
        logger.info("=" * 60)
        
        # Run the main loop
        mainloop = GLib.MainLoop()
        mainloop.run()
        
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
    except Exception as e:
        logger.error(f"Error starting MCP Server: {str(e)}")
        raise


if __name__ == "__main__":
    main()

