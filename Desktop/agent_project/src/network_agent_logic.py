#!/usr/bin/env python3
"""
NetworkAgent 核心逻辑 - 网络管理智能体

功能：
1. WiFi 连接/断开
2. 代理设置
3. 网络状态查询

作者：GUI Agent Team
"""

import os
import subprocess
import time
from typing import Dict, List, Optional
from datetime import datetime


class NetworkAgentLogic:
    """网络管理智能体核心逻辑"""
    
    def __init__(self):
        self.screenshot_dir = os.path.expanduser("~/.config/kylin-gui-agent/screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def capture_screenshot(self, prefix: str = "network") -> Optional[str]:
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
    
    # ==================== WiFi 功能 ====================
    
    def list_wifi(self) -> Dict:
        """列出可用 WiFi 网络"""
        try:
            # 使用 nmcli 列出 WiFi
            result = subprocess.run(
                ["nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return self.make_response("error", f"获取WiFi列表失败: {result.stderr}")
            
            # 解析结果
            wifi_list = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        wifi_list.append({
                            "ssid": parts[0],
                            "signal": parts[1],
                            "security": parts[2] if parts[2] else "开放"
                        })
            
            return self.make_response(
                "success",
                f"找到 {len(wifi_list)} 个WiFi网络",
                {"wifi_list": wifi_list, "count": len(wifi_list)}
            )
            
        except subprocess.TimeoutExpired:
            return self.make_response("error", "获取WiFi列表超时")
        except Exception as e:
            return self.make_response("error", f"获取WiFi列表失败: {e}")
    
    def connect_wifi(self, ssid: str, password: str = None) -> Dict:
        """
        连接 WiFi
        
        Args:
            ssid: WiFi 名称
            password: WiFi 密码（可选，开放网络不需要）
        """
        try:
            # 构建命令
            cmd = ["nmcli", "device", "wifi", "connect", ssid]
            if password:
                cmd.extend(["password", password])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                # 截图
                screenshot = self.capture_screenshot("wifi_connected")
                return self.make_response(
                    "success",
                    f"已成功连接到 WiFi: {ssid}",
                    {"ssid": ssid, "connected": True},
                    screenshot
                )
            else:
                return self.make_response(
                    "error",
                    f"连接WiFi失败: {result.stderr.strip()}"
                )
                
        except subprocess.TimeoutExpired:
            return self.make_response("error", "连接WiFi超时")
        except Exception as e:
            return self.make_response("error", f"连接WiFi失败: {e}")
    
    def disconnect_wifi(self) -> Dict:
        """断开当前 WiFi 连接"""
        try:
            # 获取当前 WiFi 设备
            result = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"],
                capture_output=True,
                text=True
            )
            
            wifi_device = None
            for line in result.stdout.strip().split("\n"):
                parts = line.split(":")
                if len(parts) >= 3 and parts[1] == "wifi" and parts[2] == "connected":
                    wifi_device = parts[0]
                    break
            
            if not wifi_device:
                return self.make_response("success", "当前没有连接的WiFi", {"disconnected": False})
            
            # 断开连接
            result = subprocess.run(
                ["nmcli", "device", "disconnect", wifi_device],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                screenshot = self.capture_screenshot("wifi_disconnected")
                return self.make_response(
                    "success",
                    f"已断开WiFi连接",
                    {"device": wifi_device, "disconnected": True},
                    screenshot
                )
            else:
                return self.make_response("error", f"断开WiFi失败: {result.stderr}")
                
        except Exception as e:
            return self.make_response("error", f"断开WiFi失败: {e}")
    
    def get_wifi_status(self) -> Dict:
        """获取当前 WiFi 连接状态"""
        try:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE,DEVICE", "connection", "show", "--active"],
                capture_output=True,
                text=True
            )
            
            wifi_connection = None
            for line in result.stdout.strip().split("\n"):
                parts = line.split(":")
                if len(parts) >= 3 and "wireless" in parts[1].lower():
                    wifi_connection = {
                        "name": parts[0],
                        "device": parts[2]
                    }
                    break
            
            if wifi_connection:
                return self.make_response(
                    "success",
                    f"当前已连接WiFi: {wifi_connection['name']}",
                    {"connected": True, "wifi": wifi_connection}
                )
            else:
                return self.make_response(
                    "success",
                    "当前未连接WiFi",
                    {"connected": False}
                )
                
        except Exception as e:
            return self.make_response("error", f"获取WiFi状态失败: {e}")
    
    # ==================== 代理功能 ====================
    
    def set_proxy(self, http_proxy: str = None, https_proxy: str = None, 
                  socks_proxy: str = None, no_proxy: str = None) -> Dict:
        """
        设置系统代理（敏感操作）
        
        Args:
            http_proxy: HTTP代理地址 (如 http://127.0.0.1:1080)
            https_proxy: HTTPS代理地址
            socks_proxy: SOCKS代理地址
            no_proxy: 不使用代理的地址列表
        """
        try:
            # 使用 gsettings 设置 GNOME 代理
            settings_changed = []
            
            if http_proxy:
                # 解析代理地址
                host, port = self._parse_proxy_address(http_proxy)
                if host and port:
                    subprocess.run(["gsettings", "set", "org.gnome.system.proxy.http", "host", host], check=True)
                    subprocess.run(["gsettings", "set", "org.gnome.system.proxy.http", "port", str(port)], check=True)
                    settings_changed.append(f"HTTP代理: {http_proxy}")
            
            if https_proxy:
                host, port = self._parse_proxy_address(https_proxy)
                if host and port:
                    subprocess.run(["gsettings", "set", "org.gnome.system.proxy.https", "host", host], check=True)
                    subprocess.run(["gsettings", "set", "org.gnome.system.proxy.https", "port", str(port)], check=True)
                    settings_changed.append(f"HTTPS代理: {https_proxy}")
            
            if socks_proxy:
                host, port = self._parse_proxy_address(socks_proxy)
                if host and port:
                    subprocess.run(["gsettings", "set", "org.gnome.system.proxy.socks", "host", host], check=True)
                    subprocess.run(["gsettings", "set", "org.gnome.system.proxy.socks", "port", str(port)], check=True)
                    settings_changed.append(f"SOCKS代理: {socks_proxy}")
            
            if no_proxy:
                subprocess.run(["gsettings", "set", "org.gnome.system.proxy", "ignore-hosts", f"['{no_proxy}']"], check=True)
                settings_changed.append(f"排除: {no_proxy}")
            
            # 启用代理模式
            subprocess.run(["gsettings", "set", "org.gnome.system.proxy", "mode", "manual"], check=True)
            
            screenshot = self.capture_screenshot("proxy_set")
            return self.make_response(
                "success",
                f"代理设置成功: {', '.join(settings_changed)}",
                {"settings": settings_changed},
                screenshot
            )
            
        except subprocess.CalledProcessError as e:
            return self.make_response("error", f"设置代理失败: {e}")
        except Exception as e:
            return self.make_response("error", f"设置代理失败: {e}")
    
    def clear_proxy(self) -> Dict:
        """清除系统代理"""
        try:
            subprocess.run(["gsettings", "set", "org.gnome.system.proxy", "mode", "none"], check=True)
            
            screenshot = self.capture_screenshot("proxy_cleared")
            return self.make_response(
                "success",
                "已清除系统代理",
                {"cleared": True},
                screenshot
            )
            
        except Exception as e:
            return self.make_response("error", f"清除代理失败: {e}")
    
    def get_proxy_status(self) -> Dict:
        """获取当前代理设置"""
        try:
            mode = subprocess.run(
                ["gsettings", "get", "org.gnome.system.proxy", "mode"],
                capture_output=True, text=True
            ).stdout.strip().strip("'")
            
            proxy_info = {"mode": mode}
            
            if mode == "manual":
                # 获取 HTTP 代理
                http_host = subprocess.run(
                    ["gsettings", "get", "org.gnome.system.proxy.http", "host"],
                    capture_output=True, text=True
                ).stdout.strip().strip("'")
                http_port = subprocess.run(
                    ["gsettings", "get", "org.gnome.system.proxy.http", "port"],
                    capture_output=True, text=True
                ).stdout.strip()
                
                if http_host:
                    proxy_info["http"] = f"{http_host}:{http_port}"
            
            return self.make_response(
                "success",
                f"代理模式: {mode}",
                proxy_info
            )
            
        except Exception as e:
            return self.make_response("error", f"获取代理状态失败: {e}")
    
    def _parse_proxy_address(self, address: str) -> tuple:
        """解析代理地址"""
        try:
            # 移除协议前缀
            addr = address.replace("http://", "").replace("https://", "").replace("socks://", "")
            
            if ":" in addr:
                host, port = addr.rsplit(":", 1)
                return host, int(port)
            return addr, 1080  # 默认端口
        except:
            return None, None


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    agent = NetworkAgentLogic()
    
    print("=== 测试 NetworkAgent ===\n")
    
    # 测试 WiFi 状态
    print("1. 获取 WiFi 状态:")
    result = agent.get_wifi_status()
    print(f"   {result}\n")
    
    # 测试 WiFi 列表
    print("2. 列出可用 WiFi:")
    result = agent.list_wifi()
    print(f"   找到 {result['data'].get('count', 0)} 个网络\n")
    
    # 测试代理状态
    print("3. 获取代理状态:")
    result = agent.get_proxy_status()
    print(f"   {result}\n")
    
    print("=== 测试完成 ===")
