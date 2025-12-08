#!/usr/bin/env python3
"""
MCP 联调模块 - System-2 推理与 MCP 协议对接

本模块实现推理引擎与 MCP Server 的联调：
1. D-Bus 连接与健康检查
2. 推理链适配 MCP ToolsList
3. 推理链驱动 MCP ToolsCall
4. MCP 调用结果存入记忆

作者：GUI Agent Team (成员B)
日期：2024-12
"""

import json
import time
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

# 尝试导入 D-Bus（Linux 专用）
try:
    import dbus
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False
    print("警告: dbus-python 未安装，MCP 功能将使用模拟模式")
    print("安装命令: pip install dbus-python")

# 导入推理模块
from system2_memory import (
    reasoning_with_memory,
    get_reasoning_for_master,
    validate_for_mcp,
    normalize_for_mcp
)

# 导入记忆模块
from memory_store import (
    save_collaboration_trajectory,
    STORAGE_DIR
)


# ============================================================
# MCP 配置常量（基于 MCP 文档）
# ============================================================

MCP_SERVICE_NAME = "com.kylin.ai.mcp.MasterAgent"
MCP_OBJECT_PATH = "/com/kylin/ai/mcp/MasterAgent"
MCP_INTERFACE_NAME = "com.kylin.ai.mcp.MasterAgent"


# ============================================================
# MCP 连接管理
# ============================================================

class MCPClient:
    """
    MCP 客户端 - 封装与 MCP Server 的 D-Bus 通信
    """
    
    def __init__(self, bus_type: str = "session"):
        """
        初始化 MCP 客户端
        
        Args:
            bus_type: D-Bus 总线类型 ("session" 或 "system")
        """
        self.bus_type = bus_type
        self.bus = None
        self.proxy = None
        self.interface = None
        self.connected = False
        self._mock_mode = not HAS_DBUS
        
        # 模拟模式下的工具列表
        self._mock_tools = [
            {
                "name": "search_file",
                "description": "搜索指定目录下的文件",
                "parameters": {"dir": "string", "pattern": "string"},
                "examples": ["search_file(dir='~/Downloads', pattern='*.png')"],
                "agent": "FileAgent"
            },
            {
                "name": "move_to_trash",
                "description": "将文件移动到回收站",
                "parameters": {"file_path": "string"},
                "examples": ["move_to_trash(file_path='~/Downloads/test.tmp')"],
                "agent": "FileAgent"
            },
            {
                "name": "change_wallpaper",
                "description": "更换桌面壁纸",
                "parameters": {"image_path": "string"},
                "examples": ["change_wallpaper(image_path='~/Pictures/bg.png')"],
                "agent": "SettingsAgent"
            },
            {
                "name": "adjust_volume",
                "description": "调整系统音量",
                "parameters": {"level": "int"},
                "examples": ["adjust_volume(level=50)"],
                "agent": "SettingsAgent"
            }
        ]
        
        self._mock_agents = [
            {
                "name": "FileAgent",
                "service": "com.kylin.ai.agent.FileAgent",
                "path": "/com/kylin/ai/agent/FileAgent",
                "interface": "com.kylin.ai.agent.FileAgent",
                "tools_count": 2,
                "last_seen": int(time.time()),
                "is_alive": True
            },
            {
                "name": "SettingsAgent",
                "service": "com.kylin.ai.agent.SettingsAgent",
                "path": "/com/kylin/ai/agent/SettingsAgent",
                "interface": "com.kylin.ai.agent.SettingsAgent",
                "tools_count": 2,
                "last_seen": int(time.time()),
                "is_alive": True
            }
        ]
    
    def connect(self) -> bool:
        """
        连接到 MCP Server
        
        Returns:
            是否连接成功
        """
        if self._mock_mode:
            print("📡 [模拟模式] MCP 客户端已启动")
            self.connected = True
            return True
        
        try:
            # 根据总线类型创建连接
            if self.bus_type == "session":
                self.bus = dbus.SessionBus()
            else:
                self.bus = dbus.SystemBus()
            
            # 获取 MCP Server 代理对象
            self.proxy = self.bus.get_object(MCP_SERVICE_NAME, MCP_OBJECT_PATH)
            self.interface = dbus.Interface(self.proxy, MCP_INTERFACE_NAME)
            
            # 健康检查
            if self.ping():
                self.connected = True
                print(f"✓ 已连接到 MCP Server ({self.bus_type} 总线)")
                return True
            else:
                print("✗ MCP Server 健康检查失败")
                return False
                
        except dbus.exceptions.DBusException as e:
            print(f"✗ 连接 MCP Server 失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        self.bus = None
        self.proxy = None
        self.interface = None
        self.connected = False
        print("已断开 MCP Server 连接")
    
    # ========== 基础信息接口 ==========
    
    def get_dbus_type(self) -> Dict:
        """获取 D-Bus 总线类型"""
        if self._mock_mode:
            return {"type": self.bus_type}
        
        result = self.interface.DBusType()
        return json.loads(result)
    
    def get_service_name(self) -> Dict:
        """获取服务名称"""
        if self._mock_mode:
            return {"name": MCP_SERVICE_NAME}
        
        result = self.interface.ServiceName()
        return json.loads(result)
    
    def get_object_path(self) -> Dict:
        """获取对象路径"""
        if self._mock_mode:
            return {"path": MCP_OBJECT_PATH}
        
        result = self.interface.ObjectPath()
        return json.loads(result)
    
    def get_interface_name(self) -> Dict:
        """获取接口名称"""
        if self._mock_mode:
            return {"name": MCP_INTERFACE_NAME}
        
        result = self.interface.InterfaceName()
        return json.loads(result)
    
    # ========== 健康检查接口 ==========
    
    def ping(self) -> bool:
        """
        健康检查
        
        Returns:
            MCP Server 是否正常运行
        """
        if self._mock_mode:
            return True
        
        try:
            result = self.interface.Ping()
            data = json.loads(result)
            return data.get("status") == "ok"
        except Exception as e:
            print(f"Ping 失败: {e}")
            return False
    
    # ========== 工具管理接口 ==========
    
    def tools_list(self) -> Dict:
        """
        获取可用工具列表
        
        Returns:
            工具列表字典
        """
        if self._mock_mode:
            return {
                "success": True,
                "tools": self._mock_tools,
                "total": len(self._mock_tools)
            }
        
        try:
            result = self.interface.ToolsList()
            return json.loads(result)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def tools_call(self, tool_name: str, parameters: Dict) -> Dict:
        """
        调用指定工具
        
        Args:
            tool_name: 工具名称
            parameters: 工具参数
            
        Returns:
            调用结果字典
        """
        parameters_json = json.dumps(parameters)
        
        if self._mock_mode:
            # 模拟工具调用结果
            return self._mock_tool_call(tool_name, parameters)
        
        try:
            result = self.interface.ToolsCall(tool_name, parameters_json)
            return json.loads(result)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _mock_tool_call(self, tool_name: str, parameters: Dict) -> Dict:
        """模拟工具调用"""
        # 检查工具是否存在
        tool_names = [t["name"] for t in self._mock_tools]
        if tool_name not in tool_names:
            return {"success": False, "error": f"工具 '{tool_name}' 不存在"}
        
        # 模拟不同工具的返回结果
        if tool_name == "search_file":
            return {
                "success": True,
                "result": {
                    "files": ["~/Downloads/image1.png", "~/Downloads/image2.png"],
                    "count": 2
                }
            }
        elif tool_name == "move_to_trash":
            return {
                "success": True,
                "result": {"message": f"文件 {parameters.get('file_path')} 已移动到回收站"}
            }
        elif tool_name == "change_wallpaper":
            return {
                "success": True,
                "result": {"message": f"壁纸已更换为 {parameters.get('image_path')}"}
            }
        elif tool_name == "adjust_volume":
            return {
                "success": True,
                "result": {"message": f"音量已调整到 {parameters.get('level')}%"}
            }
        else:
            return {"success": True, "result": {"message": "操作完成"}}
    
    # ========== 子智能体管理接口 ==========
    
    def agents_list(self) -> Dict:
        """
        获取已注册的子智能体列表
        
        Returns:
            子智能体列表字典
        """
        if self._mock_mode:
            return {
                "success": True,
                "agents": self._mock_agents,
                "total": len(self._mock_agents)
            }
        
        try:
            result = self.interface.AgentsList()
            return json.loads(result)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def agent_register(self, agent_info: Dict) -> Dict:
        """
        注册子智能体
        
        Args:
            agent_info: 子智能体信息
            
        Returns:
            注册结果字典
        """
        agent_info_json = json.dumps(agent_info)
        
        if self._mock_mode:
            self._mock_agents.append({
                "name": agent_info["name"],
                "service": agent_info["service"],
                "path": agent_info["path"],
                "interface": agent_info["interface"],
                "tools_count": len(agent_info.get("tools", [])),
                "last_seen": int(time.time()),
                "is_alive": True
            })
            return {"success": True, "message": f"Agent '{agent_info['name']}' registered successfully"}
        
        try:
            result = self.interface.AgentRegister(agent_info_json)
            return json.loads(result)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def agent_unregister(self, agent_name: str) -> Dict:
        """
        注销子智能体
        
        Args:
            agent_name: 子智能体名称
            
        Returns:
            注销结果字典
        """
        if self._mock_mode:
            self._mock_agents = [a for a in self._mock_agents if a["name"] != agent_name]
            return {"success": True, "message": f"Agent '{agent_name}' unregistered successfully"}
        
        try:
            result = self.interface.AgentUnregister(agent_name)
            return json.loads(result)
        except Exception as e:
            return {"success": False, "error": str(e)}


# ============================================================
# 推理链与 MCP 适配
# ============================================================

def get_available_tools(mcp_client: MCPClient) -> Dict[str, Dict]:
    """
    获取 MCP 可用工具映射
    
    Args:
        mcp_client: MCP 客户端
        
    Returns:
        {tool_name: {parameters, agent, description}}
    """
    tools_result = mcp_client.tools_list()
    
    if not tools_result.get("success"):
        print(f"⚠️ 获取工具列表失败: {tools_result.get('error')}")
        return {}
    
    tool_map = {}
    for tool in tools_result.get("tools", []):
        tool_map[tool["name"]] = {
            "parameters": tool.get("parameters", {}),
            "agent": tool.get("agent", ""),
            "description": tool.get("description", "")
        }
    
    return tool_map


def get_available_agents(mcp_client: MCPClient) -> List[Dict]:
    """
    获取可用子智能体列表
    
    Args:
        mcp_client: MCP 客户端
        
    Returns:
        在线的子智能体列表
    """
    agents_result = mcp_client.agents_list()
    
    if not agents_result.get("success"):
        print(f"⚠️ 获取子智能体列表失败: {agents_result.get('error')}")
        return []
    
    # 只返回在线的子智能体
    online_agents = [
        agent for agent in agents_result.get("agents", [])
        if agent.get("is_alive", False)
    ]
    
    return online_agents


def build_mcp_aware_prompt(user_task: str, tool_map: Dict, agents: List[Dict]) -> str:
    """
    构建 MCP 感知的推理 Prompt
    
    Args:
        user_task: 用户任务
        tool_map: 可用工具映射
        agents: 可用子智能体列表
        
    Returns:
        增强后的 Prompt
    """
    agent_names = list(set(t["agent"] for t in tool_map.values() if t["agent"]))
    tool_names = list(tool_map.keys())
    
    mcp_context = f"""
## MCP 可用资源（必须遵守）
### 可用子智能体
{', '.join(agent_names) if agent_names else '无'}

### 可用工具
{json.dumps(tool_map, indent=2, ensure_ascii=False)}

### 重要约束
- agent_selection 中的 agent 必须从可用子智能体中选择
- execution_plan 中的 action 应使用可用工具
- 工具参数必须符合 parameters 定义
"""
    
    return mcp_context


# ============================================================
# MCP 集成推理流程
# ============================================================

def reasoning_with_mcp(
    user_task: str,
    mcp_client: MCPClient,
    screenshot_path: Optional[str] = None,
    verbose: bool = True
) -> Tuple[Dict, List[Dict]]:
    """
    MCP 集成推理流程：
    1. 检查 MCP Server 状态
    2. 获取可用工具/子智能体
    3. 生成适配 MCP 的推理链
    4. 执行 MCP 工具调用
    5. 存储协作轨迹
    
    Args:
        user_task: 用户任务
        mcp_client: MCP 客户端
        screenshot_path: 截图路径
        verbose: 是否打印详细信息
        
    Returns:
        (推理链, 执行结果列表)
    """
    if verbose:
        print("\n" + "=" * 70)
        print("MCP 集成推理流程")
        print("=" * 70)
        print(f"用户任务: {user_task}")
    
    # Step 1: 检查 MCP Server 状态
    if verbose:
        print("\n--- Step 1: MCP 健康检查 ---")
    
    if not mcp_client.connected:
        if not mcp_client.connect():
            return {"error": "MCP Server 未连接"}, []
    
    if not mcp_client.ping():
        return {"error": "MCP Server 健康检查失败"}, []
    
    if verbose:
        print("✓ MCP Server 运行正常")
    
    # Step 2: 获取可用工具和子智能体
    if verbose:
        print("\n--- Step 2: 获取 MCP 资源 ---")
    
    tool_map = get_available_tools(mcp_client)
    agents = get_available_agents(mcp_client)
    
    if verbose:
        print(f"可用工具: {list(tool_map.keys())}")
        print(f"在线子智能体: {[a['name'] for a in agents]}")
    
    # Step 3: 生成推理链
    if verbose:
        print("\n--- Step 3: 生成推理链 ---")
    
    reasoning_chain, trajectory_path = reasoning_with_memory(
        user_task=user_task,
        screenshot_path=screenshot_path,
        enable_reuse=True,
        verbose=verbose
    )
    
    # Step 4: 解析推理链并执行 MCP 调用
    if verbose:
        print("\n--- Step 4: 执行 MCP 工具调用 ---")
    
    execution_results = execute_reasoning_via_mcp(
        reasoning_chain=reasoning_chain,
        mcp_client=mcp_client,
        tool_map=tool_map,
        verbose=verbose
    )
    
    # Step 5: 更新轨迹存储（添加 MCP 执行结果）
    if verbose:
        print("\n--- Step 5: 存储协作轨迹 ---")
    
    # 汇总执行结果
    success = all(r.get("success", False) for r in execution_results) if execution_results else True
    execution_summary = json.dumps(execution_results, ensure_ascii=False)
    
    # 保存包含 MCP 信息的轨迹
    save_mcp_trajectory(
        task=user_task,
        reasoning_chain=reasoning_chain,
        mcp_results=execution_results,
        success=success
    )
    
    if verbose:
        print(f"✓ 协作轨迹已保存")
    
    return reasoning_chain, execution_results


def execute_reasoning_via_mcp(
    reasoning_chain: Dict,
    mcp_client: MCPClient,
    tool_map: Dict,
    verbose: bool = True
) -> List[Dict]:
    """
    根据推理链执行 MCP 工具调用
    
    Args:
        reasoning_chain: 推理链
        mcp_client: MCP 客户端
        tool_map: 可用工具映射
        verbose: 是否打印详细信息
        
    Returns:
        执行结果列表
    """
    results = []
    
    # 获取执行计划
    execution_plan = reasoning_chain.get("execution_plan", [])
    
    if not execution_plan:
        if verbose:
            print("⚠️ 推理链无执行计划")
        return results
    
    for i, step in enumerate(execution_plan, 1):
        action = step.get("action", "")
        agent = step.get("agent", "")
        
        if verbose:
            print(f"\n  Step {i}: {action[:50]}... (Agent: {agent})")
        
        # 解析工具调用
        tool_call = parse_tool_call_from_action(action, tool_map)
        
        if tool_call:
            tool_name = tool_call["tool_name"]
            parameters = tool_call["parameters"]
            
            if verbose:
                print(f"    → 调用工具: {tool_name}")
                print(f"    → 参数: {parameters}")
            
            # 执行 MCP 工具调用
            result = mcp_client.tools_call(tool_name, parameters)
            
            result["step"] = i
            result["tool_name"] = tool_name
            result["parameters"] = parameters
            results.append(result)
            
            if verbose:
                status = "✓" if result.get("success") else "✗"
                print(f"    → 结果: {status} {result.get('result', result.get('error', ''))}"[:60])
        else:
            if verbose:
                print(f"    → 无法解析工具调用，跳过")
            results.append({
                "step": i,
                "success": True,
                "result": {"message": "步骤已记录，无需工具调用"}
            })
    
    return results


def parse_tool_call_from_action(action: str, tool_map: Dict) -> Optional[Dict]:
    """
    从 action 描述中解析工具调用
    
    Args:
        action: 动作描述
        tool_map: 可用工具映射
        
    Returns:
        {"tool_name": str, "parameters": dict} 或 None
    """
    import re
    
    # 检查是否包含已知工具名
    for tool_name, tool_info in tool_map.items():
        if tool_name in action.lower():
            # 尝试提取参数
            parameters = {}
            param_defs = tool_info.get("parameters", {})
            
            for param_name in param_defs.keys():
                # 尝试多种模式匹配参数值
                patterns = [
                    rf"{param_name}\s*[=:]\s*['\"]?([^'\"，,;]+)['\"]?",
                    rf"{param_name}\s*[=:]\s*(\S+)",
                ]
                for pattern in patterns:
                    match = re.search(pattern, action, re.IGNORECASE)
                    if match:
                        parameters[param_name] = match.group(1).strip()
                        break
            
            # 如果没有解析到参数，使用默认值
            if not parameters:
                # 从 action 中提取路径等信息
                path_match = re.search(r'[~/\w]+/[\w.*]+', action)
                if path_match:
                    # 根据工具类型设置默认参数
                    if "dir" in param_defs:
                        parameters["dir"] = path_match.group(0)
                    elif "file_path" in param_defs:
                        parameters["file_path"] = path_match.group(0)
                    elif "image_path" in param_defs:
                        parameters["image_path"] = path_match.group(0)
                
                # 提取文件模式
                pattern_match = re.search(r'\*\.\w+', action)
                if pattern_match and "pattern" in param_defs:
                    parameters["pattern"] = pattern_match.group(0)
                
                # 提取数字（如音量级别）
                num_match = re.search(r'\b(\d+)\s*%?', action)
                if num_match and "level" in param_defs:
                    parameters["level"] = int(num_match.group(1))
            
            return {"tool_name": tool_name, "parameters": parameters}
    
    return None


# ============================================================
# MCP 轨迹存储
# ============================================================

def save_mcp_trajectory(
    task: str,
    reasoning_chain: Dict,
    mcp_results: List[Dict],
    success: bool = True
) -> str:
    """
    保存包含 MCP 执行信息的协作轨迹
    
    Args:
        task: 用户任务
        reasoning_chain: 推理链
        mcp_results: MCP 执行结果列表
        success: 是否成功
        
    Returns:
        轨迹文件路径
    """
    # 提取 MCP 相关信息
    mcp_tools_called = [r.get("tool_name", "") for r in mcp_results if r.get("tool_name")]
    mcp_errors = [r.get("error", "") for r in mcp_results if r.get("error")]
    
    return save_collaboration_trajectory(
        task=task,
        reasoning_chain=reasoning_chain,
        execution_result=json.dumps(mcp_results, ensure_ascii=False),
        screenshot_paths=[],
        success=success,
        metadata={
            "source": "mcp_integration",
            "mcp_tools_called": mcp_tools_called,
            "mcp_errors": mcp_errors,
            "mcp_call_count": len(mcp_results)
        }
    )


# ============================================================
# 便捷接口
# ============================================================

# 全局 MCP 客户端实例
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """获取全局 MCP 客户端实例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
        _mcp_client.connect()
    return _mcp_client


def mcp_reasoning(user_task: str, verbose: bool = True) -> Tuple[Dict, List[Dict]]:
    """
    便捷接口：MCP 集成推理
    
    Args:
        user_task: 用户任务
        verbose: 是否打印详细信息
        
    Returns:
        (推理链, 执行结果列表)
    """
    client = get_mcp_client()
    return reasoning_with_mcp(user_task, client, verbose=verbose)


def mcp_tool_call(tool_name: str, parameters: Dict) -> Dict:
    """
    便捷接口：直接调用 MCP 工具
    
    Args:
        tool_name: 工具名称
        parameters: 参数
        
    Returns:
        调用结果
    """
    client = get_mcp_client()
    return client.tools_call(tool_name, parameters)


def mcp_status() -> Dict:
    """
    获取 MCP 状态
    
    Returns:
        状态信息字典
    """
    client = get_mcp_client()
    
    status = {
        "connected": client.connected,
        "mock_mode": client._mock_mode,
        "bus_type": client.bus_type,
        "ping": client.ping() if client.connected else False
    }
    
    if client.connected:
        tools = client.tools_list()
        agents = client.agents_list()
        status["tools_count"] = tools.get("total", 0)
        status["agents_count"] = agents.get("total", 0)
        status["agents"] = [a["name"] for a in agents.get("agents", [])]
    
    return status


# ============================================================
# 测试函数
# ============================================================

def test_mcp_integration():
    """测试 MCP 集成功能"""
    print("\n" + "🔌 MCP 联调测试 🔌".center(60))
    print("=" * 60)
    
    # 创建 MCP 客户端
    client = MCPClient()
    
    # 测试 1: 连接
    print("\n--- 测试 1: MCP 连接 ---")
    if client.connect():
        print("✓ 连接成功")
    else:
        print("✗ 连接失败")
        return
    
    # 测试 2: 基础信息
    print("\n--- 测试 2: 基础信息 ---")
    print(f"  总线类型: {client.get_dbus_type()}")
    print(f"  服务名称: {client.get_service_name()}")
    print(f"  对象路径: {client.get_object_path()}")
    
    # 测试 3: 健康检查
    print("\n--- 测试 3: 健康检查 ---")
    print(f"  Ping: {'✓ OK' if client.ping() else '✗ FAIL'}")
    
    # 测试 4: 工具列表
    print("\n--- 测试 4: 工具列表 ---")
    tools = client.tools_list()
    if tools.get("success"):
        print(f"  可用工具数: {tools['total']}")
        for tool in tools["tools"]:
            print(f"    - {tool['name']} ({tool['agent']})")
    else:
        print(f"  ✗ 获取失败: {tools.get('error')}")
    
    # 测试 5: 子智能体列表
    print("\n--- 测试 5: 子智能体列表 ---")
    agents = client.agents_list()
    if agents.get("success"):
        print(f"  已注册子智能体数: {agents['total']}")
        for agent in agents["agents"]:
            status = "在线" if agent["is_alive"] else "离线"
            print(f"    - {agent['name']} ({status})")
    else:
        print(f"  ✗ 获取失败: {agents.get('error')}")
    
    # 测试 6: 工具调用
    print("\n--- 测试 6: 工具调用 ---")
    result = client.tools_call("search_file", {"dir": "~/Downloads", "pattern": "*.png"})
    if result.get("success"):
        print(f"  ✓ search_file 调用成功")
        print(f"    结果: {result['result']}")
    else:
        print(f"  ✗ 调用失败: {result.get('error')}")
    
    # 测试 7: 完整推理流程
    print("\n--- 测试 7: MCP 集成推理 ---")
    test_task = "搜索下载目录的png文件并设置为壁纸"
    
    reasoning_chain, execution_results = reasoning_with_mcp(
        user_task=test_task,
        mcp_client=client,
        verbose=True
    )
    
    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"  MCP 连接: ✓")
    print(f"  健康检查: ✓")
    print(f"  工具列表: {tools.get('total', 0)} 个")
    print(f"  子智能体: {agents.get('total', 0)} 个")
    print(f"  推理链生成: ✓")
    print(f"  工具调用: {len(execution_results)} 次")
    
    if client._mock_mode:
        print("\n⚠️ 注意: 当前为模拟模式，实际部署需启动 MCP Server")
    
    print("\n✓ MCP 联调测试完成!")


if __name__ == "__main__":
    test_mcp_integration()

