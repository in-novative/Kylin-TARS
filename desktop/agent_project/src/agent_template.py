#!/usr/bin/env python3
"""
子智能体开发模板 - Kylin-TARS GUI Agent

本模板提供标准化的子智能体开发框架，包含：
1. MCP 注册逻辑
2. 工具定义规范
3. 异常处理机制
4. 执行结果截图

使用方法：
1. 复制本模板创建新智能体
2. 修改 AGENT_CONFIG 配置
3. 实现 YourAgentLogic 类
4. 定义 AGENT_TOOLS 工具列表

作者：GUI Agent Team
"""

import os
import sys
import json
import time
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

# D-Bus 相关
try:
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False
    print("[WARNING] D-Bus 模块未安装，将使用模拟模式")


# ============================================================
# 配置模板（新智能体需修改此部分）
# ============================================================

# MCP Server 配置（统一标准，勿修改）
MCP_CONFIG = {
    "bus_name": "com.kylin.ai.mcp.MasterAgent",
    "object_path": "/com/kylin/ai/mcp/MasterAgent",
    "interface": "com.kylin.ai.mcp.MasterAgent"
}

# 智能体配置（新智能体需修改）
AGENT_CONFIG = {
    "name": "TemplateAgent",           # 智能体名称
    "bus_name": "com.mcp.agent.template",  # D-Bus 服务名
    "object_path": "/com/mcp/agent/template",
    "interface": "com.mcp.agent.template.Interface",
    "description": "模板智能体，用于演示开发流程"
}

# 权限等级定义
class PermissionLevel:
    NORMAL = "normal"      # 普通级：无需确认
    SENSITIVE = "sensitive"  # 敏感级：需用户确认


# ============================================================
# 工具定义模板
# ============================================================

def define_tool(
    name: str,
    description: str,
    parameters: Dict[str, Any],
    permission: str = PermissionLevel.NORMAL,
    examples: List[str] = None
) -> Dict:
    """
    定义工具的标准函数
    
    Args:
        name: 工具名称（格式：agent_name.tool_name）
        description: 工具描述
        parameters: 参数定义（JSON Schema 格式）
        permission: 权限等级（normal/sensitive）
        examples: 使用示例
    
    Returns:
        工具定义字典
    """
    return {
        "name": name,
        "description": description,
        "parameters": parameters,
        "permission": permission,
        "examples": examples or [],
        "agent": AGENT_CONFIG["name"]
    }


# ============================================================
# 智能体逻辑基类
# ============================================================

class BaseAgentLogic(ABC):
    """
    智能体逻辑基类
    所有智能体都应继承此类并实现抽象方法
    """
    
    def __init__(self):
        self.screenshot_dir = os.path.expanduser("~/.config/kylin-gui-agent/screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def capture_screenshot(self, prefix: str = "screenshot") -> Optional[str]:
    """
    截取当前屏幕
    
    Args:
        prefix: 截图文件名前缀
        
    Returns:
        截图文件路径，失败返回 None
    """
    timestamp = int(time.time())
        screenshot_path = os.path.join(self.screenshot_dir, f"{prefix}_{timestamp}.png")
    
    try:
            # 尝试使用 scrot 截图
            subprocess.run(
                ["scrot", "-d", "1", screenshot_path],
                check=True,
                capture_output=True
            )
        return screenshot_path
    except subprocess.CalledProcessError:
    try:
                # 备选方案：使用 gnome-screenshot
                subprocess.run(
                    ["gnome-screenshot", "-f", screenshot_path],
                    check=True,
                    capture_output=True
                )
        return screenshot_path
            except Exception as e:
                print(f"[WARNING] 截图失败: {e}")
    return None

    def make_response(
        self,
        status: str,
        message: str,
        data: Any = None,
        screenshot_path: Optional[str] = None
    ) -> Dict:
    """
        生成标准响应格式
    
    Args:
            status: 状态（success/error）
            message: 消息
        data: 返回数据
            screenshot_path: 截图路径
        
    Returns:
            标准响应字典
    """
        return {
        "status": status,
            "msg": message,
            "data": data or {},
            "screenshot_path": screenshot_path,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    @abstractmethod
    def get_tools(self) -> List[Dict]:
    """
        获取工具列表（子类必须实现）
        
    Returns:
            工具定义列表
        """
        pass
    
    @abstractmethod
    def handle_tool_call(self, tool_name: str, params: Dict) -> Dict:
        """
        处理工具调用（子类必须实现）
        
        Args:
            tool_name: 工具名称
            params: 参数字典
            
        Returns:
            执行结果字典
        """
        pass


# ============================================================
# MCP 注册管理器
# ============================================================

class MCPRegistrationManager:
    """
    MCP 注册管理器
    封装与 MCP Server 的 D-Bus 通信
    """
    
    def __init__(self, agent_config: Dict):
        self.config = agent_config
        self.bus = None
        self.registered = False
    
        if HAS_DBUS:
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        
    def register_to_mcp(self, tools: List[Dict]) -> bool:
        """
        注册到 MCP Server
        
        Args:
            tools: 工具列表
            
        Returns:
            是否注册成功
        """
        if not HAS_DBUS or not self.bus:
            print("[WARNING] D-Bus 不可用，跳过 MCP 注册")
            return False
        
        try:
            # 检查 MCP Server 是否运行
            if not self.bus.name_has_owner(MCP_CONFIG["bus_name"]):
                print(f"[WARNING] MCP Server ({MCP_CONFIG['bus_name']}) 未启动，跳过注册")
                return False
            
            # 获取 MCP 接口
            mcp_proxy = self.bus.get_object(
                MCP_CONFIG["bus_name"],
                MCP_CONFIG["object_path"]
            )
            mcp_interface = dbus.Interface(mcp_proxy, MCP_CONFIG["interface"])
            
            # 构造注册数据
            register_data = json.dumps({
                "name": self.config["name"],
                "agent_name": self.config["name"],  # 兼容两种字段名
                "service": self.config["bus_name"],
                "bus_name": self.config["bus_name"],
                "path": self.config["object_path"],
                "object_path": self.config["object_path"],
                "interface": self.config["interface"],
                "tools": tools
            })
            
            # 调用注册接口
            result = json.loads(mcp_interface.AgentRegister(register_data))
            
            if result.get("success"):
                self.registered = True
                print(f"[INFO] {self.config['name']} 已成功注册到 MCP Server")
                print(f"[INFO]   工具: {[t['name'] for t in tools]}")
                return True
            else:
                print(f"[ERROR] MCP 注册失败: {result.get('error')}")
                return False
                
        except Exception as e:
            print(f"[ERROR] 注册到 MCP Server 失败: {e}")
            return False
    
    def unregister_from_mcp(self) -> bool:
        """从 MCP Server 注销"""
        if not HAS_DBUS or not self.bus or not self.registered:
            return False
        
        try:
            mcp_proxy = self.bus.get_object(
                MCP_CONFIG["bus_name"],
                MCP_CONFIG["object_path"]
            )
            mcp_interface = dbus.Interface(mcp_proxy, MCP_CONFIG["interface"])
            result = json.loads(mcp_interface.AgentUnregister(self.config["name"]))
            
            if result.get("success"):
                self.registered = False
                print(f"[INFO] {self.config['name']} 已从 MCP Server 注销")
                return True
            return False
        except Exception as e:
            print(f"[ERROR] 注销失败: {e}")
            return False
    
    def request_bus_name(self) -> bool:
        """请求 D-Bus 服务名"""
        if not HAS_DBUS or not self.bus:
            return False
        
        try:
            self.bus.request_name(self.config["bus_name"])
            return True
        except Exception as e:
            print(f"[ERROR] 请求 D-Bus 服务名失败: {e}")
            return False


# ============================================================
# D-Bus 消息处理器
# ============================================================

class DBusMessageHandler:
    """
    D-Bus 消息处理器
    处理来自 MCP Server 的工具调用请求
    """
    
    def __init__(self, agent_logic: BaseAgentLogic, agent_config: Dict):
        self.logic = agent_logic
        self.config = agent_config
    
    def handle_message(self, bus, message):
        """处理 D-Bus 消息"""
        # 检查消息类型
        if message.get_type() != dbus.lowlevel.METHOD_CALL:
            return
        
        # 检查接口
        if message.get_interface() != self.config["interface"]:
            return
        
        method_name = message.get_member()
        
        if method_name == "ToolsCall":
            self._handle_tools_call(bus, message)
        else:
            self._send_error(bus, message, f"Unknown method: {method_name}")
    
    def _handle_tools_call(self, bus, message):
        """处理工具调用"""
        try:
            tool_name, params_json = message.get_args_list()
            params = json.loads(params_json)
            
            # 调用智能体逻辑
            result = self.logic.handle_tool_call(tool_name, params)
            
            # 构造响应
            response = {
                "success": result.get("status") == "success",
                "result": result.get("data"),
                "msg": result.get("msg"),
                "screenshot_path": result.get("screenshot_path"),
                "error": result.get("msg") if result.get("status") == "error" else None
            }
            
            # 发送响应
            reply = dbus.lowlevel.MethodReturnMessage(message)
            reply.append(dbus.String(json.dumps(response)))
            bus.send(reply)
            
        except Exception as e:
            self._send_error(bus, message, str(e))
    
    def _send_error(self, bus, message, error_msg: str):
        """发送错误响应"""
        bus.send(
            dbus.lowlevel.ErrorMessage(
                message,
                "org.freedesktop.DBus.Error.Failed",
                error_msg
            )
        )


# ============================================================
# 智能体启动器
# ============================================================

def start_agent(agent_logic: BaseAgentLogic, agent_config: Dict):
    """
    启动智能体服务
    
    Args:
        agent_logic: 智能体逻辑实例
        agent_config: 智能体配置
    """
    print(f"[INFO] 启动 {agent_config['name']} MCP 服务")
    
    if not HAS_DBUS:
        print("[ERROR] D-Bus 模块不可用，无法启动服务")
        return
    
    # 创建注册管理器
    manager = MCPRegistrationManager(agent_config)
    
    # 请求 D-Bus 服务名
    if not manager.request_bus_name():
        return
    
    # 获取工具列表并注册
    tools = agent_logic.get_tools()
    manager.register_to_mcp(tools)
    
    # 设置消息处理器
    handler = DBusMessageHandler(agent_logic, agent_config)
    manager.bus.add_message_filter(handler.handle_message)
    
    # 启动主循环
    loop = GLib.MainLoop()
    try:
        print(f"[INFO] {agent_config['name']} 服务已启动，等待调用...")
        loop.run()
    except KeyboardInterrupt:
        print(f"\n[INFO] {agent_config['name']} 服务已停止")
        manager.unregister_from_mcp()
        loop.quit()


# ============================================================
# 示例：模板智能体实现
# ============================================================

class TemplateAgentLogic(BaseAgentLogic):
    """模板智能体逻辑实现（示例）"""
    
    def get_tools(self) -> List[Dict]:
        """定义工具列表"""
        return [
            define_tool(
                name="template_agent.hello",
                description="打招呼示例工具",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "姓名"}
                    },
                    "required": ["name"]
                },
                permission=PermissionLevel.NORMAL,
                examples=["template_agent.hello(name='World')"]
            ),
            define_tool(
                name="template_agent.sensitive_action",
                description="敏感操作示例（需确认）",
                parameters={
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "description": "操作内容"},
                        "user_confirm": {"type": "boolean", "description": "用户确认"}
                    },
                    "required": ["action"]
                },
                permission=PermissionLevel.SENSITIVE,
                examples=["template_agent.sensitive_action(action='重要操作', user_confirm=true)"]
            )
        ]
    
    def handle_tool_call(self, tool_name: str, params: Dict) -> Dict:
        """处理工具调用"""
        try:
            if tool_name == "template_agent.hello":
                name = params.get("name", "World")
                return self.make_response(
                    status="success",
                    message=f"Hello, {name}!",
                    data={"greeting": f"Hello, {name}!"}
                )
            
            elif tool_name == "template_agent.sensitive_action":
                # 检查敏感操作确认
                if not params.get("user_confirm", False):
                    return self.make_response(
                        status="error",
                        message="敏感操作需要用户确认（user_confirm=true）"
                    )
                
                action = params.get("action", "未知操作")
                return self.make_response(
                    status="success",
                    message=f"敏感操作已执行: {action}",
                    data={"action": action, "confirmed": True}
                )
            
            else:
                return self.make_response(
                    status="error",
                    message=f"未知工具: {tool_name}"
                )
                
        except Exception as e:
            return self.make_response(
                status="error",
                message=f"工具执行失败: {e}"
            )


# ============================================================
# 主函数（模板示例）
# ============================================================

if __name__ == "__main__":
    # 创建智能体逻辑实例
    logic = TemplateAgentLogic()

    # 启动服务
    start_agent(logic, AGENT_CONFIG)
