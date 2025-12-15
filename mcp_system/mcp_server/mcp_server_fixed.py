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
import psutil
import sys
import os
from threading import Thread
from gi.repository import GLib
from typing import Dict, List, Any, Optional, Callable, Tuple

# 导入协作日志模块
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from collaboration_logger import log_schedule, log_execution, log_broadcast
    HAS_COLLABORATION_LOGGER = True
except ImportError:
    HAS_COLLABORATION_LOGGER = False
    logger.warning("协作日志模块未找到，日志记录功能不可用")

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
        
        # 支持多实例智能体（同一智能体的多个实例）
        self.agent_instances: Dict[str, List[str]] = {}  # agent_name -> [instance_ids]
        
        # 智能体状态缓存（用于广播）
        self.agent_status_cache: Dict[str, str] = {}  # instance_id -> status
        
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
            
            # 提取任务信息（用于日志）
            task = parameters.get("task", "unknown_task")
            step = parameters.get("step", 1)
            related_log_id = parameters.get("related_log_id")
            
            # Check if it's a child agent tool (contains agent prefix)
            if "." in tool_name:
                agent_name = tool_name.split(".")[0]
                
                # 负载均衡：选择最佳实例
                best_instance = self._load_balance(agent_name, tool_name)
                
                if best_instance:
                    # 记录调度日志
                    if HAS_COLLABORATION_LOGGER:
                        schedule_log_id = log_schedule(
                            task=task,
                            step=step,
                            agent=agent_name,
                            tool=tool_name,
                            parameters=parameters,
                            related_log_id=related_log_id
                        )
                        parameters["schedule_log_id"] = schedule_log_id
                    
                    # 故障转移：如果调用失败，尝试备选实例
                    result = self._fault_tolerance(best_instance, tool_name, parameters, agent_name)
                    
                    # 记录执行日志
                    if HAS_COLLABORATION_LOGGER:
                        try:
                            result_dict = json.loads(result)
                            log_execution(
                                task=task,
                                step=step,
                                agent=agent_name,
                                tool=tool_name,
                                status="success" if result_dict.get("success") else "error",
                                result=result_dict.get("result"),
                                related_log_id=schedule_log_id if 'schedule_log_id' in locals() else None,
                                error=result_dict.get("error")
                            )
                        except:
                            pass
                    
                    return result
                else:
                    # 回退到原有逻辑
                    matching_agent = None
                    for registered_name, agent_info in self.child_agents.items():
                        agent_base_name = agent_info.get("agent_name", registered_name)
                        if agent_base_name.lower() == agent_name.lower() or \
                           agent_name in agent_base_name or \
                           agent_base_name in agent_name:
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
            
            # 生成实例ID（支持多实例）
            instance_id = f"{agent_name}_{int(time.time())}"
            if agent_name not in self.agent_instances:
                self.agent_instances[agent_name] = []
            self.agent_instances[agent_name].append(instance_id)
            
            # Register the agent
            self.child_agents[instance_id] = {
                **agent_info,
                "agent_name": agent_name,  # 保留原始名称
                "instance_id": instance_id,
                "last_seen": time.time(),
                "is_alive": True,
                "status": "online",  # 状态：online/busy/offline/error
                "cpu_usage": 0.0  # CPU占用（用于负载均衡）
            }
            
            # 初始化状态缓存
            self.agent_status_cache[instance_id] = "online"
            
            # 广播新智能体注册
            self._broadcast_agent_status(instance_id, "online", agent_name)
            
            logger.info(f"Child agent registered: {agent_name} (instance: {instance_id})")
            logger.info(f"  Tools: {[t.get('name', 'N/A') for t in agent_info.get('tools', [])]}")
            
            return json.dumps({
                "success": True,
                "message": f"Agent '{agent_name}' registered successfully",
                "instance_id": instance_id
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
    
    def _load_balance(self, agent_name: str, tool_name: str) -> Optional[str]:
        """
        负载均衡：选择CPU占用最低的智能体实例
        
        Args:
            agent_name: 智能体名称
            tool_name: 工具名称
        
        Returns:
            最佳实例ID，无多实例则返回None
        """
        # 查找该智能体的所有实例
        instances = self.agent_instances.get(agent_name, [])
        
        if len(instances) <= 1:
            # 无多实例，返回第一个（如果有）
            return instances[0] if instances else None
        
        # 更新CPU占用信息
        current_time = time.time()
        available_instances = []
        
        for instance_id in instances:
            if instance_id not in self.child_agents:
                continue
            
            agent_info = self.child_agents[instance_id]
            
            # 检查是否在线（最近60秒内有活动）
            if (current_time - agent_info.get("last_seen", 0)) > 60:
                agent_info["is_alive"] = False
                continue
            
            if not agent_info.get("is_alive", True):
                continue
            
            # 查询进程CPU占用
            try:
                service_name = agent_info.get("service", agent_info.get("bus_name", ""))
                # 通过服务名查找进程（简化实现）
                cpu_usage = self._get_agent_cpu_usage(service_name)
                agent_info["cpu_usage"] = cpu_usage
                available_instances.append((instance_id, cpu_usage))
            except:
                # 无法获取CPU信息，使用默认值
                agent_info["cpu_usage"] = 50.0
                available_instances.append((instance_id, 50.0))
        
        if not available_instances:
            return None
        
        # 选择CPU占用最低的实例
        best_instance = min(available_instances, key=lambda x: x[1])
        logger.info(f"负载均衡选择: {agent_name} -> {best_instance[0]} (CPU: {best_instance[1]:.1f}%)")
        
        return best_instance[0]
    
    def _get_agent_cpu_usage(self, service_name: str) -> float:
        """
        获取智能体进程的CPU占用
        
        Args:
            service_name: DBus服务名
        
        Returns:
            CPU占用百分比
        """
        try:
            # 通过服务名查找进程（简化实现，实际可能需要更复杂的匹配）
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info.get('cmdline', []))
                    if service_name.lower() in cmdline.lower():
                        proc_obj = psutil.Process(proc.info['pid'])
                        return proc_obj.cpu_percent(interval=0.1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except:
            pass
        
        return 0.0  # 默认值
    
    def _fault_tolerance(
        self, 
        instance_id: str, 
        tool_name: str, 
        parameters: Dict[str, Any],
        agent_name: str
    ) -> str:
        """
        故障转移：调用失败时自动切换到备选实例
        
        Args:
            instance_id: 首选实例ID
            tool_name: 工具名称
            parameters: 工具参数
            agent_name: 智能体名称
        
        Returns:
            调用结果JSON字符串
        """
        # 尝试调用首选实例
        result = self._call_child_agent_tool(instance_id, tool_name, parameters)
        
        try:
            result_dict = json.loads(result)
            
            # 检查是否失败且错误类型为"智能体离线"
            if not result_dict.get("success", False):
                error_msg = result_dict.get("error", "").lower()
                
                if "offline" in error_msg or "not found" in error_msg or "dbus error" in error_msg:
                    # 标记实例为离线
                    if instance_id in self.child_agents:
                        self.child_agents[instance_id]["is_alive"] = False
                    
                    logger.warning(f"实例 {instance_id} 调用失败，尝试故障转移")
                    
                    # 查找备选实例
                    instances = self.agent_instances.get(agent_name, [])
                    for alt_instance_id in instances:
                        if alt_instance_id == instance_id:
                            continue
                        
                        if alt_instance_id not in self.child_agents:
                            continue
                        
                        alt_agent_info = self.child_agents[alt_instance_id]
                        current_time = time.time()
                        
                        # 检查备选实例是否在线
                        if (current_time - alt_agent_info.get("last_seen", 0)) < 60 and \
                           alt_agent_info.get("is_alive", True):
                            logger.info(f"故障转移: {instance_id} -> {alt_instance_id}")
                            return self._call_child_agent_tool(alt_instance_id, tool_name, parameters)
                    
                    # 无备选实例
                    return json.dumps({
                        "success": False,
                        "error": f"智能体 {agent_name} 所有实例均离线，请重启智能体",
                        "fault_tolerance": True
                    })
        except:
            pass
        
        return result
    
    def _call_child_agent_tool(self, instance_id: str, tool_name: str, parameters: Dict[str, Any]) -> str:
        """
        Call a tool on a child agent (支持实例ID)
        
        Args:
            instance_id: 智能体实例ID
            tool_name: 工具名称
            parameters: 工具参数
        """
        try:
            if instance_id not in self.child_agents:
                return json.dumps({
                    "success": False,
                    "error": f"Instance '{instance_id}' not found"
                })
            
            agent_info = self.child_agents[instance_id]
            
            # Update last_seen
            agent_info["last_seen"] = time.time()
            agent_info["is_alive"] = True
            
            # Connect to the child agent's DBus service
            proxy = self._bus.get_object(
                agent_info.get("service", agent_info.get("bus_name")), 
                agent_info.get("path", agent_info.get("object_path"))
            )
            interface = dbus.Interface(proxy, agent_info["interface"])
            
            # Call the tool on the child agent
            result = interface.ToolsCall(tool_name, json.dumps(parameters))
            return str(result)
            
        except dbus.exceptions.DBusException as e:
            error_msg = str(e).lower()
            logger.error(f"DBus error calling instance {instance_id}: {error_msg}")
            
            # 判断是否为离线错误
            if "name has no owner" in error_msg or "no such interface" in error_msg:
                if instance_id in self.child_agents:
                    self.child_agents[instance_id]["is_alive"] = False
                return json.dumps({
                    "success": False,
                    "error": f"智能体离线: {instance_id}",
                    "offline": True
                })
            
            return json.dumps({
                "success": False,
                "error": f"DBus error: {str(e)}"
            })
        except Exception as e:
            logger.error(f"Error calling instance {instance_id}: {str(e)}")
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
        """Start monitoring agent heartbeats and broadcasting status"""
        def monitor():
            while True:
                time.sleep(3)  # 每3秒检查一次
                self._check_agent_heartbeats()
                self._broadcast_status_updates()
        
        heartbeat_thread = Thread(target=monitor, daemon=True)
        heartbeat_thread.start()
        logger.info("Heartbeat monitor started (3s interval)")
    
    def _check_agent_heartbeats(self):
        """Check and mark inactive agents"""
        current_time = time.time()
        
        for instance_id, agent_info in self.child_agents.items():
            last_seen = agent_info.get("last_seen", 0)
            time_since_seen = current_time - last_seen
            
            if time_since_seen > 60:
                # 标记为离线
                old_status = agent_info.get("status", "online")
                agent_info["is_alive"] = False
                agent_info["status"] = "offline"
                agent_name = agent_info.get("agent_name", instance_id)
                
                # 如果状态改变，广播更新
                if old_status != "offline":
                    self._broadcast_agent_status(instance_id, "offline", agent_name)
                    
                    # 记录广播日志
                    if HAS_COLLABORATION_LOGGER:
                        log_broadcast(
                            agent_name=agent_name,
                            instance_id=instance_id,
                            old_status=old_status,
                            new_status="offline"
                        )
                
                logger.warning(f"Agent marked as inactive: {agent_name} (instance: {instance_id})")
            elif time_since_seen > 10 and agent_info.get("status") == "online":
                # 超过10秒未活动，标记为busy（可能正在处理任务）
                agent_info["status"] = "busy"
    
    def _broadcast_agent_status(self, instance_id: str, status: str, agent_name: str):
        """
        广播智能体状态变更
        
        Args:
            instance_id: 实例ID
            status: 状态（online/busy/offline/error）
            agent_name: 智能体名称
        """
        try:
            # 更新状态缓存
            old_status = self.agent_status_cache.get(instance_id)
            self.agent_status_cache[instance_id] = status
            
            # 如果状态改变，通过DBus信号广播
            if old_status != status:
                # 构建广播消息
                broadcast_msg = {
                    "instance_id": instance_id,
                    "agent_name": agent_name,
                    "status": status,
                    "timestamp": time.time()
                }
                
                # 向所有其他智能体广播（通过DBus信号）
                # 注意：这里简化实现，实际可能需要更复杂的信号机制
                logger.info(f"📡 广播状态: {agent_name} ({instance_id}) -> {status}")
                
                # 更新所有智能体的状态缓存（供查询使用）
                for other_instance_id, other_info in self.child_agents.items():
                    if other_instance_id != instance_id:
                        # 其他智能体可以查询状态缓存
                        pass
                        
        except Exception as e:
            logger.error(f"广播状态失败: {e}")
    
    def _broadcast_status_updates(self):
        """定期广播状态更新"""
        current_time = time.time()
        
        for instance_id, agent_info in self.child_agents.items():
            # 检查状态是否需要更新
            last_seen = agent_info.get("last_seen", 0)
            time_since_seen = current_time - last_seen
            current_status = agent_info.get("status", "online")
            
            # 根据时间判断状态
            if time_since_seen > 60:
                new_status = "offline"
            elif time_since_seen > 10:
                new_status = "busy"
            else:
                new_status = "online"
            
            # 如果状态改变，广播
            if new_status != current_status:
                agent_info["status"] = new_status
                agent_name = agent_info.get("agent_name", instance_id)
                self._broadcast_agent_status(instance_id, new_status, agent_name)
                
                # 记录广播日志
                if HAS_COLLABORATION_LOGGER:
                    log_broadcast(
                        agent_name=agent_name,
                        instance_id=instance_id,
                        old_status=current_status,
                        new_status=new_status
                    )
    
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='s', out_signature='s')
    def GetAgentStatus(self, instance_id: str) -> str:
        """获取智能体状态"""
        self.last_heartbeat = time.time()
        
        try:
            if instance_id in self.child_agents:
                agent_info = self.child_agents[instance_id]
                return json.dumps({
                    "success": True,
                    "instance_id": instance_id,
                    "agent_name": agent_info.get("agent_name", instance_id),
                    "status": agent_info.get("status", "unknown"),
                    "is_alive": agent_info.get("is_alive", False),
                    "last_seen": agent_info.get("last_seen", 0),
                    "cpu_usage": agent_info.get("cpu_usage", 0.0)
                })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Instance '{instance_id}' not found"
                })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })
    
    @dbus.service.method(DBUS_INTERFACE_NAME, in_signature='ss', out_signature='s')
    def UpdateAgentStatus(self, instance_id: str, status: str) -> str:
        """更新智能体状态（由智能体主动调用）"""
        self.last_heartbeat = time.time()
        
        try:
            if instance_id not in self.child_agents:
                return json.dumps({
                    "success": False,
                    "error": f"Instance '{instance_id}' not found"
                })
            
            agent_info = self.child_agents[instance_id]
            old_status = agent_info.get("status", "online")
            agent_info["status"] = status
            agent_info["last_seen"] = time.time()
            
            # 如果状态改变，广播
            if old_status != status:
                agent_name = agent_info.get("agent_name", instance_id)
                self._broadcast_agent_status(instance_id, status, agent_name)
                
                # 记录广播日志
                if HAS_COLLABORATION_LOGGER:
                    log_broadcast(
                        agent_name=agent_name,
                        instance_id=instance_id,
                        old_status=old_status,
                        new_status=status
                    )
            
            return json.dumps({
                "success": True,
                "message": f"Status updated to '{status}'"
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            })


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

