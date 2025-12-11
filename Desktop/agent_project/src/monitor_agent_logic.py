#!/usr/bin/env python3
"""
MonitorAgent 核心逻辑 - 系统监控智能体

功能：
1. 获取系统状态（CPU/内存/磁盘）
2. 清理后台进程
3. 监控智能体状态

作者：GUI Agent Team
"""

import os
import subprocess
import time
import psutil
import dbus
from typing import Dict, List, Optional
from datetime import datetime


class MonitorAgentLogic:
    """系统监控智能体核心逻辑"""
    
    def __init__(self):
        self.screenshot_dir = os.path.expanduser("~/.config/kylin-gui-agent/screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def capture_screenshot(self, prefix: str = "monitor") -> Optional[str]:
        """截取屏幕"""
        timestamp = int(time.time())
        screenshot_path = os.path.join(self.screenshot_dir, f"{prefix}_{timestamp}.png")
        
        try:
            subprocess.run(["scrot", "-d", "1", screenshot_path], check=True, capture_output=True)
            return screenshot_path
        except:
            try:
                subprocess.run(["gnome-screenshot", "-f", screenshot_path], check=True, capture_output=True)
                return screenshot_path
            except:
                return None
    
    def make_response(self, status: str, msg: str, data: Dict = None, screenshot: str = None) -> Dict:
        """生成标准响应"""
        return {
            "status": status,
            "msg": msg,
            "data": data or {},
            "screenshot_path": screenshot,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # ==================== 系统状态查询 ====================
    
    def get_system_status(self) -> Dict:
        """
        获取系统状态（CPU/内存/磁盘）
        
        Returns:
            包含CPU、内存、磁盘使用率的字典
        """
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_total_gb = memory.total / (1024**3)
            memory_used_gb = memory.used / (1024**3)
            memory_available_gb = memory.available / (1024**3)
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_total_gb = disk.total / (1024**3)
            disk_used_gb = disk.used / (1024**3)
            disk_free_gb = disk.free / (1024**3)
            
            # 获取前5个CPU占用最高的进程
            top_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] is not None and proc_info['cpu_percent'] > 0:
                        top_processes.append({
                            "pid": proc_info['pid'],
                            "name": proc_info['name'],
                            "cpu_percent": round(proc_info['cpu_percent'], 2),
                            "memory_percent": round(proc_info['memory_percent'], 2)
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # 按CPU占用排序，取前5个
            top_processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            top_processes = top_processes[:5]
            
            screenshot = self.capture_screenshot("system_status")
            
            return self.make_response(
                "success",
                "系统状态获取成功",
                {
                    "cpu": {
                        "percent": round(cpu_percent, 2),
                        "count": cpu_count,
                        "status": "正常" if cpu_percent < 80 else "高负载"
                    },
                    "memory": {
                        "percent": round(memory_percent, 2),
                        "total_gb": round(memory_total_gb, 2),
                        "used_gb": round(memory_used_gb, 2),
                        "available_gb": round(memory_available_gb, 2),
                        "status": "正常" if memory_percent < 80 else "高占用"
                    },
                    "disk": {
                        "percent": round(disk_percent, 2),
                        "total_gb": round(disk_total_gb, 2),
                        "used_gb": round(disk_used_gb, 2),
                        "free_gb": round(disk_free_gb, 2),
                        "status": "正常" if disk_percent < 90 else "空间不足"
                    },
                    "top_processes": top_processes
                },
                screenshot
            )
            
        except Exception as e:
            return self.make_response("error", f"获取系统状态失败: {e}")
    
    # ==================== 清理后台进程 ====================
    
    def clean_background_process(self, process_name: Optional[str] = None) -> Dict:
        """
        清理后台进程
        
        Args:
            process_name: 进程名称（可选，不指定则清理闲置进程）
        """
        try:
            cleaned_processes = []
            
            if process_name:
                # 清理指定进程
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if process_name.lower() in proc.info['name'].lower():
                            proc.terminate()
                            cleaned_processes.append({
                                "pid": proc.info['pid'],
                                "name": proc.info['name']
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            else:
                # 清理闲置进程（CPU占用<1%且内存占用<100MB）
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                    try:
                        proc_info = proc.info
                        cpu_percent = proc_info.get('cpu_percent', 0)
                        memory_mb = proc_info.get('memory_info', {}).rss / (1024**2) if proc_info.get('memory_info') else 0
                        
                        # 排除系统关键进程
                        critical_processes = ['systemd', 'dbus', 'gdm', 'gnome-shell', 'python']
                        proc_name = proc_info.get('name', '').lower()
                        
                        if (cpu_percent < 1.0 and memory_mb < 100 and 
                            not any(cp in proc_name for cp in critical_processes)):
                            proc.terminate()
                            cleaned_processes.append({
                                "pid": proc_info['pid'],
                                "name": proc_info['name'],
                                "cpu_percent": round(cpu_percent, 2),
                                "memory_mb": round(memory_mb, 2)
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
            
            if cleaned_processes:
                time.sleep(1)  # 等待进程退出
                screenshot = self.capture_screenshot("process_cleaned")
                return self.make_response(
                    "success",
                    f"已清理 {len(cleaned_processes)} 个进程",
                    {
                        "cleaned_count": len(cleaned_processes),
                        "cleaned_processes": cleaned_processes
                    },
                    screenshot
                )
            else:
                return self.make_response(
                    "success",
                    "未找到需要清理的进程",
                    {"cleaned_count": 0, "cleaned_processes": []}
                )
                
        except Exception as e:
            return self.make_response("error", f"清理进程失败: {e}")
    
    # ==================== 监控智能体状态 ====================
    
    def monitor_agent_status(self) -> Dict:
        """
        查询所有MCP子智能体在线状态
        
        Returns:
            包含各智能体状态的字典
        """
        try:
            agent_statuses = {}
            
            # MCP Server 服务名
            mcp_service = "com.kylin.ai.mcp.MasterAgent"
            
            try:
                bus = dbus.SessionBus()
                
                # 检查MCP Server是否在线
                if bus.name_has_owner(mcp_service):
                    # 尝试获取工具列表
                    try:
                        mcp_proxy = bus.get_object(mcp_service, "/com/kylin/ai/mcp/MasterAgent")
                        mcp_interface = dbus.Interface(mcp_proxy, "com.kylin.ai.mcp.MasterAgent")
                        
                        # 调用ToolsList获取已注册的智能体
                        tools_json = mcp_interface.ToolsList()
                        import json
                        tools_data = json.loads(tools_json)
                        
                        # 解析工具列表，提取智能体名称
                        agents = set()
                        if isinstance(tools_data, dict) and "tools" in tools_data:
                            for tool in tools_data["tools"]:
                                tool_name = tool.get("name", "")
                                if "." in tool_name:
                                    agent_name = tool_name.split(".")[0]
                                    agents.add(agent_name)
                        
                        # 检查每个智能体的服务状态
                        agent_services = {
                            "file_agent": "com.mcp.agent.file",
                            "settings_agent": "com.mcp.agent.settings",
                            "network_agent": "com.mcp.agent.network",
                            "app_agent": "com.mcp.agent.app",
                            "monitor_agent": "com.mcp.agent.monitor",
                            "media_agent": "com.mcp.agent.media",
                        }
                        
                        for agent_name, service_name in agent_services.items():
                            is_online = bus.name_has_owner(service_name)
                            agent_statuses[agent_name] = {
                                "online": is_online,
                                "status": "在线" if is_online else "离线",
                                "service": service_name
                            }
                        
                        # MCP Server状态
                        agent_statuses["mcp_server"] = {
                            "online": True,
                            "status": "在线",
                            "service": mcp_service,
                            "registered_agents": list(agents)
                        }
                        
                    except Exception as e:
                        agent_statuses["mcp_server"] = {
                            "online": True,
                            "status": "在线但无法获取工具列表",
                            "error": str(e)
                        }
                else:
                    agent_statuses["mcp_server"] = {
                        "online": False,
                        "status": "离线"
                    }
                    
            except Exception as e:
                return self.make_response("error", f"查询智能体状态失败: {e}")
            
            screenshot = self.capture_screenshot("agent_status")
            
            return self.make_response(
                "success",
                "智能体状态查询成功",
                {
                    "agents": agent_statuses,
                    "online_count": sum(1 for a in agent_statuses.values() if a.get("online", False)),
                    "total_count": len(agent_statuses)
                },
                screenshot
            )
            
        except Exception as e:
            return self.make_response("error", f"监控智能体状态失败: {e}")


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    agent = MonitorAgentLogic()
    
    print("=== 测试 MonitorAgent ===\n")
    
    # 测试系统状态
    print("1. 获取系统状态:")
    result = agent.get_system_status()
    print(f"   {result['msg']}")
    if result["status"] == "success":
        data = result["data"]
        print(f"   CPU: {data['cpu']['percent']}% ({data['cpu']['status']})")
        print(f"   内存: {data['memory']['percent']}% ({data['memory']['status']})")
        print(f"   磁盘: {data['disk']['percent']}% ({data['disk']['status']})\n")
    
    # 测试清理进程
    print("2. 清理后台进程:")
    result = agent.clean_background_process()
    print(f"   {result['msg']}\n")
    
    # 测试智能体状态
    print("3. 监控智能体状态:")
    result = agent.monitor_agent_status()
    print(f"   {result['msg']}")
    if result["status"] == "success":
        agents = result["data"]["agents"]
        for agent_name, status in agents.items():
            print(f"   {agent_name}: {status.get('status', 'N/A')}")
    
    print("\n=== 测试完成 ===")

