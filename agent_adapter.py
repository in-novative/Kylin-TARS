#!/usr/bin/env python3
"""
子智能体适配器 - 将成员C的子智能体注册到成员A的MCP Server

问题说明：
- 成员A的MCP Server服务名: com.kylin.ai.mcp.MasterAgent
- 成员C的子智能体期望连接: com.mcp.server
- 本适配器解决服务名不一致问题

使用方式：
1. 先启动 MCP Server (mcp_server_fixed.py)
2. 运行本适配器注册子智能体
"""

import os
import sys
import json
import time

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# 尝试导入 D-Bus
try:
    import dbus
    HAS_DBUS = True
except ImportError:
    HAS_DBUS = False
    print("❌ dbus-python 未安装")

# 导入配置
from mcp_config import (
    MCP_SERVICE_NAME,
    MCP_OBJECT_PATH,
    MCP_INTERFACE_NAME,
    AGENTS_CONFIG
)


def register_agents_to_mcp():
    """
    将成员C的子智能体注册到成员A的MCP Server
    """
    if not HAS_DBUS:
        print("❌ D-Bus 不可用，无法注册子智能体")
        return False
    
    print("=" * 60)
    print("🔧 子智能体注册适配器")
    print("=" * 60)
    
    try:
        # 连接到 MCP Server
        bus = dbus.SessionBus()
        
        # 检查 MCP Server 是否运行
        if not bus.name_has_owner(MCP_SERVICE_NAME):
            print(f"❌ MCP Server ({MCP_SERVICE_NAME}) 未运行")
            print("请先启动 MCP Server:")
            print("  cd mcp_system/mcp_server && python mcp_server_fixed.py")
            return False
        
        print(f"✓ MCP Server ({MCP_SERVICE_NAME}) 已运行")
        
        # 获取 MCP 接口
        proxy = bus.get_object(MCP_SERVICE_NAME, MCP_OBJECT_PATH)
        interface = dbus.Interface(proxy, MCP_INTERFACE_NAME)
        
        # 健康检查
        ping_result = json.loads(interface.Ping())
        if ping_result.get("status") != "ok":
            print("❌ MCP Server 健康检查失败")
            return False
        
        print(f"✓ MCP Server 健康检查通过")
        
        # 注册每个子智能体
        print("\n--- 注册子智能体 ---")
        
        for agent_name, agent_config in AGENTS_CONFIG.items():
            print(f"\n正在注册 {agent_name}...")
            
            # 构造注册信息
            register_info = {
                "name": agent_config["name"],
                "service": agent_config["service"],
                "path": agent_config["path"],
                "interface": agent_config["interface"],
                "tools": agent_config["tools"]
            }
            
            # 调用注册接口
            result = json.loads(interface.AgentRegister(json.dumps(register_info)))
            
            if result.get("success"):
                print(f"  ✓ {agent_name} 注册成功")
                print(f"    服务: {agent_config['service']}")
                print(f"    工具: {[t['name'] for t in agent_config['tools']]}")
            else:
                print(f"  ✗ {agent_name} 注册失败: {result.get('error')}")
        
        # 验证注册结果
        print("\n--- 验证注册结果 ---")
        agents_result = json.loads(interface.AgentsList())
        
        if agents_result.get("success"):
            print(f"已注册子智能体: {agents_result.get('total', 0)} 个")
            for agent in agents_result.get("agents", []):
                status = "在线" if agent.get("is_alive") else "离线"
                print(f"  - {agent['name']} ({status})")
        
        # 验证工具列表
        tools_result = json.loads(interface.ToolsList())
        if tools_result.get("success"):
            print(f"\n可用工具: {tools_result.get('total', 0)} 个")
            for tool in tools_result.get("tools", []):
                agent = tool.get("agent", "本地")
                print(f"  - {tool['name']} ({agent})")
        
        print("\n" + "=" * 60)
        print("✓ 子智能体注册完成!")
        print("=" * 60)
        return True
        
    except dbus.exceptions.DBusException as e:
        print(f"❌ D-Bus 错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 注册失败: {e}")
        return False


def test_tool_call():
    """测试工具调用"""
    if not HAS_DBUS:
        print("❌ D-Bus 不可用")
        return
    
    print("\n" + "=" * 60)
    print("🧪 工具调用测试")
    print("=" * 60)
    
    try:
        bus = dbus.SessionBus()
        proxy = bus.get_object(MCP_SERVICE_NAME, MCP_OBJECT_PATH)
        interface = dbus.Interface(proxy, MCP_INTERFACE_NAME)
        
        # 测试工具调用
        test_cases = [
            {
                "tool": "file_agent.search_file",
                "params": {
                    "search_path": os.path.expanduser("~/Downloads"),
                    "keyword": ".png",
                    "recursive": True
                }
            },
            {
                "tool": "settings_agent.adjust_volume",
                "params": {
                    "volume": 50,
                    "device": "@DEFAULT_SINK@"
                }
            }
        ]
        
        for test in test_cases:
            print(f"\n测试: {test['tool']}")
            print(f"参数: {test['params']}")
            
            try:
                result = json.loads(interface.ToolsCall(
                    test["tool"],
                    json.dumps(test["params"])
                ))
                
                if result.get("success"):
                    print(f"  ✓ 成功: {result.get('result', {})}")
                else:
                    print(f"  ○ 失败: {result.get('error', '未知错误')}")
                    print("    (这可能是因为子智能体服务未运行)")
            except Exception as e:
                print(f"  ✗ 错误: {e}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="子智能体注册适配器")
    parser.add_argument("--test", action="store_true", help="测试工具调用")
    args = parser.parse_args()
    
    if register_agents_to_mcp():
        if args.test:
            test_tool_call()

