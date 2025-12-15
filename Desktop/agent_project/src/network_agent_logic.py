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
    
    # ==================== 网络测速功能 ====================
    
    def speed_test(self, test_type: str = "quick") -> Dict:
        """
        网络测速（集成speedtest-cli）
        
        Args:
            test_type: 测速类型（quick/full）
                - quick: 快速测速（约10秒）
                - full: 完整测速（约30秒）
        """
        try:
            # 检查speedtest-cli是否安装
            try:
                subprocess.run(["speedtest-cli", "--version"], check=True, capture_output=True, timeout=5)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                # 如果没有安装，使用ping和wget作为备选方案
                return self._speed_test_fallback()
            
            # 使用speedtest-cli进行测速
            if test_type == "quick":
                # 快速测速：使用最近的服务器，单次测试
                cmd = ["speedtest-cli", "--simple", "--secure"]
                timeout = 30
            else:
                # 完整测速：选择最佳服务器，多次测试
                cmd = ["speedtest-cli", "--secure"]
                timeout = 60
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            elapsed_time = time.time() - start_time
            
            if result.returncode != 0:
                return self.make_response("error", f"测速失败: {result.stderr.strip()}")
            
            # 解析结果
            speed_data = self._parse_speedtest_output(result.stdout, test_type)
            speed_data["elapsed_time"] = round(elapsed_time, 2)
            speed_data["test_type"] = test_type
            
            screenshot = self.capture_screenshot("speed_test")
            
            return self.make_response(
                "success",
                f"测速完成（{test_type}模式，耗时{elapsed_time:.1f}秒）",
                speed_data,
                screenshot
            )
            
        except subprocess.TimeoutExpired:
            return self.make_response("error", f"测速超时（{test_type}模式）")
        except Exception as e:
            return self.make_response("error", f"测速失败: {e}")
    
    def _parse_speedtest_output(self, output: str, test_type: str) -> Dict:
        """解析speedtest-cli输出"""
        speed_data = {
            "ping": None,
            "download_mbps": None,
            "upload_mbps": None,
            "server": None
        }
        
        try:
            lines = output.strip().split("\n")
            for line in lines:
                line_lower = line.lower()
                if "ping:" in line_lower:
                    ping_str = line.split(":")[1].strip().replace("ms", "").strip()
                    speed_data["ping"] = float(ping_str)
                elif "download:" in line_lower:
                    download_str = line.split(":")[1].strip().replace("mbit/s", "").strip()
                    speed_data["download_mbps"] = float(download_str)
                elif "upload:" in line_lower:
                    upload_str = line.split(":")[1].strip().replace("mbit/s", "").strip()
                    speed_data["upload_mbps"] = float(upload_str)
                elif "hosted by" in line_lower or "server:" in line_lower:
                    speed_data["server"] = line.split(":")[-1].strip() if ":" in line else line.strip()
        except:
            pass
        
        return speed_data
    
    def _speed_test_fallback(self) -> Dict:
        """备选测速方案（使用ping和wget）"""
        try:
            # Ping测试延迟
            ping_result = subprocess.run(
                ["ping", "-c", "4", "8.8.8.8"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            ping_ms = None
            if ping_result.returncode == 0:
                # 解析ping结果
                for line in ping_result.stdout.split("\n"):
                    if "min/avg/max" in line:
                        parts = line.split("=")[1].strip().split("/")
                        if len(parts) >= 2:
                            ping_ms = float(parts[1])
                            break
            
            # 下载速度测试（使用wget下载小文件）
            download_mbps = None
            try:
                test_url = "http://speedtest.tele2.net/10MB.zip"
                start_time = time.time()
                wget_result = subprocess.run(
                    ["wget", "-O", "/dev/null", test_url],
                    capture_output=True,
                    timeout=30
                )
                elapsed = time.time() - start_time
                
                if wget_result.returncode == 0 and elapsed > 0:
                    # 10MB = 80Mbit
                    download_mbps = round(80 / elapsed, 2)
            except:
                pass
            
            screenshot = self.capture_screenshot("speed_test_fallback")
            
            return self.make_response(
                "success",
                "测速完成（备选方案）",
                {
                    "ping_ms": ping_ms,
                    "download_mbps": download_mbps,
                    "upload_mbps": None,
                    "test_type": "fallback",
                    "note": "speedtest-cli未安装，使用备选方案"
                },
                screenshot
            )
        except Exception as e:
            return self.make_response("error", f"备选测速方案失败: {e}")
    
    def get_network_status(self) -> Dict:
        """获取网络状态（综合信息）"""
        try:
            # WiFi状态
            wifi_status = self.get_wifi_status()
            wifi_connected = wifi_status["data"].get("connected", False)
            wifi_info = wifi_status["data"].get("wifi", {})
            
            # 代理状态
            proxy_status = self.get_proxy_status()
            proxy_data = proxy_status["data"]
            
            # IP地址
            ip_address = None
            try:
                result = subprocess.run(
                    ["hostname", "-I"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    ip_address = result.stdout.strip().split()[0]
            except:
                pass
            
            screenshot = self.capture_screenshot("network_status")
            
            return self.make_response(
                "success",
                "网络状态获取成功",
                {
                    "wifi_connected": wifi_connected,
                    "wifi_ssid": wifi_info.get("name") if wifi_connected else None,
                    "ip_address": ip_address,
                    "proxy_enabled": proxy_data.get("mode") == "manual",
                    "proxy_info": proxy_data
                },
                screenshot
            )
        except Exception as e:
            return self.make_response("error", f"获取网络状态失败: {e}")


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
