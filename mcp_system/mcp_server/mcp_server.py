#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Server - Master Control Protocol Server Implementation
This module implements the MCP Server that exposes capabilities via DBus
and handles tool listing and tool calling requests.
"""

import os
import os
import dbus
import dbus.service
import dbus.mainloop.glib
import json
import logging
import time
from threading import Thread
from gi.repository import GLib
from typing import Dict, List, Any, Optional, Callable
from mcp_client.agent_registry import InitDb, UpsertAgent, RemoveAgent, ListAgents, AgentByName
from utils.set_logger import set_logger
from utils.get_config import get_master_config

logger = set_logger("mcp_server")
MASTERAGENT = get_master_config()

# DBus constants
DBUS_SERVICE_NAME = MASTERAGENT["SERVICE_NAME"]
DBUS_OBJECT_PATH = MASTERAGENT["OBJECT_PATH"]
DBUS_INTERFACE_NAME = MASTERAGENT["INTERFACE_NAME"]

class MCPTool:
    """Represents a tool that can be called via MCP"""
    def __init__(self, name: str, description: str, handler: Callable, 
                 parameters: Dict[str, Any], examples: List[Dict[str, Any]]):
        """
        Initialize a tool
        
        Args:
            name: Name of the tool
            description: Description of what the tool does
            handler: Function to call when the tool is invoked
            parameters: Schema defining the tool's parameters
            examples: Example usage of the tool
        """
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
            "examples": self.examples
        }
    
    def call(self, **kwargs) -> Dict[str, Any]:
        """Call the tool with given parameters"""
        try:
            result = self.handler(**kwargs)
            return json.dumps({
                "success": True,
                "result": result
            })
        except Exception as e:
            logger.error(f"Error calling tool {self.name}: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })


class MCPServer(dbus.service.Object):
    """MCP Server implementation using DBus"""
    def __init__(self):
        """Initialize MCP Server"""
        # Initialize DBus connection
        bus_name = dbus.service.BusName(DBUS_SERVICE_NAME, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, DBUS_OBJECT_PATH)
        
        # Dictionary to store available tools
        self.tools: Dict[str, MCPTool] = {}
        
        # Heartbeat timestamp
        self.last_heartbeat = time.time()
        
        logger.info("MCP Server initialized and registered on DBus")
    
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='', out_signature='s')
    def DBusType(self) -> str:
        """Return type of DBus, including session and system"""
        self.last_heartbeat = time.time()
        bus = dbus.SessionBus()
        if isinstance(bus, dbus.SessionBus):
            return json.dumps({
                "type": "session"
            })
        else:
            return json.dumps({
                "type": "system"
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
    def InterfaceName(self) -> str:
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
            tools_list = []
            # Get tools from this agent
            for tool_name in self.tools.values():
                tools_list.append(f"MasterAgent.{tool_name}")
            
            # Get tools from child agents
            for agent in ListAgents():
                for tool in agent["tools"]:
                    # Add agent name prefix to tool name to avoid conflicts
                    tools_list.append(tool["name"])
            
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
            
            # Check if tool name contains agent prefix
            if "." in tool_name:
                agent_name, actual_tool_name = tool_name.split(".", 1)
                
                # Check if agent exists
                if agent_name not in ListAgents():
                    return json.dumps({
                        "success": False,
                        "error": f"Agent '{agent_name}' not found"
                    })
                
                # Call the tool on the child agent
                return self._call_child_agent_tool(agent_name, actual_tool_name, parameters)
            else:
                # Call local tool
                if tool_name not in self.tools:
                    return json.dumps({
                        "success": False,
                        "error": f"Tool '{tool_name}' not found"
                    })
                
                # Call the local tool
                return self.tools[tool_name].call(**parameters)
                
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
            
            # Validate required fields
            required_fields = ["name", "service", "path", "interface", "tools"]
            for field in required_fields:
                if field not in agent_info:
                    return json.dumps({
                        "success": False,
                        "error": f"Missing required field: {field}"
                    })
            
            # Register the agent
            agent_info["last_seen"] = time.time()
            logger.info(f"agent info : {agent_info.keys()}")
            UpsertAgent(**agent_info)
            
            logger.info(f"Child agent registered: {agent_info['name']}")
            return json.dumps({
                "success": True,
                "message": f"Agent {agent_info['name']} registered successfully"
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
            exists = (any(item.get("name") == agent_name for item in ListAgents()))
            if exists:
                RemoveAgent(agent_name)
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
            
            bus = dbus.SessionBus()
            for agent in ListAgents():
                proxy = bus.get_object(agent["service"], agent["path"])
                interface = dbus.Interface(proxy, agent["interface"])
                is_alive = json.loads(interface.Ping()).get("status") == "ok"

                if is_alive:
                    agent["last_seen"] = time.time()
                    UpsertAgent(**agent)
                else:
                    logger.warning(f"can't ping childAgent {agent['name']}, please check whether it's still alive")

                agents_list.append({
                    **agent,
                    "is_alive":is_alive
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
            agent_info = AgentByName(agent_name)
            
            # Connect to the child agent's DBus service
            bus = dbus.SessionBus()
            proxy = bus.get_object(agent_info["service"], agent_info["path"])
            interface = dbus.Interface(proxy, agent_info["interface"])
            
            # Check if agent is alive
            is_alive = json.loads(interface.Ping()).get("status") == "ok"

            if is_alive:
                # Update last_seen time of child Agent
                agent_info["last_seen"] = time.time()
                UpsertAgent(**agent_info)

                # Call the tool on the child agent
                result = interface.ToolsCall(tool_name, json.dumps(parameters))
                return json.dumps({
                    "success": True,
                    "result": result
                })
            else:
                logger.warning(f"can't ping childAgent {agent_name}, please check whether it's still alive")
                return json.dumps({
                    "success": False
                })

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
                time.sleep(30)  # Check every 30 seconds
                self._check_agent_heartbeats()
        
        heartbeat_thread = Thread(target=monitor, daemon=True)
        heartbeat_thread.start()
        logger.info("Heartbeat monitor started")
    
    def _check_agent_heartbeats(self):
        """Check and remove inactive agents"""
        try:
            bus = dbus.SessionBus()
            for agent in ListAgents():
                proxy = bus.get_object(agent["service"], agent["path"])
                interface = dbus.Interface(proxy, agent["interface"])

                # Check if agent is alive
                is_alive = json.loads(interface.Ping()).get("status") == "ok"

                if is_alive:
                    # Update last_seen time of child Agent
                    agent["last_seen"] = time.time()
                    UpsertAgent(**agent)
        except Exception as e:
            logging.warning("Agent %s offline: %s", agent["name"], e)
            

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
        
        logger.info("MCP Server started successfully")
        logger.info(f"Service name: {DBUS_SERVICE_NAME}")
        logger.info(f"Object path: {DBUS_OBJECT_PATH}")
        logger.info(f"Interface name: {DBUS_INTERFACE_NAME}")
        
        # Run the main loop
        InitDb()
        mainloop = GLib.MainLoop()
        mainloop.run()
        
    except KeyboardInterrupt:
        logger.info("MCP Server stopped by user")
    except Exception as e:
        logger.error(f"Error starting MCP Server: {str(e)}")


if __name__ == "__main__":
    main()