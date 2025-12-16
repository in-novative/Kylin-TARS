#!/usr/bin/env python3
"""
AppAgent 核心逻辑 - 应用管理智能体

功能：
1. 启动应用
2. 关闭应用
3. 列出运行中的应用
4. 查找应用路径

作者：GUI Agent Team
"""

import os
import subprocess
import time
import psutil
from typing import Dict, List, Optional
from datetime import datetime


class AppAgentLogic:
    """应用管理智能体核心逻辑"""
    
    def __init__(self):
        self.screenshot_dir = os.path.expanduser("~/.config/kylin-gui-agent/screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    def capture_screenshot(self, prefix: str = "app") -> Optional[str]:
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
    
    # ==================== 应用查找 ====================
    
    def find_app(self, app_name: str) -> Dict:
        """
        查找应用路径
        
        Args:
            app_name: 应用名称（如 firefox, chrome, gedit）
        """
        try:
            # 方法1: 使用 which 查找可执行文件
            result = subprocess.run(
                ["which", app_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                app_path = result.stdout.strip()
                return self.make_response(
                    "success",
                    f"找到应用: {app_name}",
                    {"app_name": app_name, "app_path": app_path, "found": True}
                )
            
            # 方法2: 使用 gio launch 查找桌面文件
            desktop_files = [
                f"/usr/share/applications/{app_name}.desktop",
                f"/usr/local/share/applications/{app_name}.desktop",
                os.path.expanduser(f"~/.local/share/applications/{app_name}.desktop")
            ]
            
            for desktop_file in desktop_files:
                if os.path.exists(desktop_file):
                    return self.make_response(
                        "success",
                        f"找到应用桌面文件: {app_name}",
                        {"app_name": app_name, "desktop_file": desktop_file, "found": True}
                    )
            
            # 方法3: 搜索所有 .desktop 文件
            result = subprocess.run(
                ["find", "/usr/share/applications", "-name", f"*{app_name}*.desktop"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.stdout.strip():
                desktop_file = result.stdout.strip().split("\n")[0]
                return self.make_response(
                    "success",
                    f"找到应用: {app_name}",
                    {"app_name": app_name, "desktop_file": desktop_file, "found": True}
                )
            
            return self.make_response(
                "error",
                f"未找到应用: {app_name}",
                {"app_name": app_name, "found": False}
            )
            
        except subprocess.TimeoutExpired:
            return self.make_response("error", "查找应用超时")
        except Exception as e:
            return self.make_response("error", f"查找应用失败: {e}")
        
    # ==================== 应用启动 ====================
    
    def launch_app(self, app_name: str, args: List[str] = None) -> Dict:
        """
        启动应用
        
        Args:
            app_name: 应用名称或路径
            args: 启动参数（可选）
        """
        try:
            # 先查找应用
            find_result = self.find_app(app_name)
            if find_result["status"] == "error":
                return find_result
            
            app_path = find_result["data"].get("app_path")
            desktop_file = find_result["data"].get("desktop_file")
            
            # 构建启动命令
            if app_path:
                cmd = [app_path]
            elif desktop_file:
                # 使用 gio launch 启动桌面文件
                cmd = ["gio", "launch", desktop_file]
            else:
                # 直接使用应用名
                cmd = [app_name]
            
            if args:
                cmd.extend(args)
            
            # 启动应用（后台运行）
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # 等待一下确保启动
            time.sleep(1)
            
            # 检查进程是否还在运行
            if process.poll() is None:
                screenshot = self.capture_screenshot("app_launched")
                return self.make_response(
                    "success",
                    f"应用已启动: {app_name}",
                    {
                        "app_name": app_name,
                        "pid": process.pid,
                        "launched": True
                    },
                    screenshot
                )
            else:
                return self.make_response(
                    "error",
                    f"应用启动失败: {app_name}（进程立即退出）"
                )
                
        except FileNotFoundError:
            return self.make_response("error", f"应用不存在: {app_name}")
        except Exception as e:
            return self.make_response("error", f"启动应用失败: {e}")
    
    # ==================== 应用关闭 ====================
    
    def close_app(self, app_name: str, force: bool = False) -> Dict:
        """
        关闭应用
        
        Args:
            app_name: 应用名称
            force: 是否强制关闭（kill -9）
        """
        try:
            # 查找运行中的应用进程
            running_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '').lower()
                    cmdline = ' '.join(proc_info.get('cmdline', [])).lower()
                    
                    # 匹配应用名
                    if app_name.lower() in proc_name or app_name.lower() in cmdline:
                        running_processes.append({
                            "pid": proc_info['pid'],
                            "name": proc_info['name']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not running_processes:
                return self.make_response(
                    "success",
                    f"应用未运行: {app_name}",
                    {"app_name": app_name, "closed": False, "processes": []}
                )
            
            # 关闭进程
            closed_pids = []
            for proc_info in running_processes:
                try:
                    proc = psutil.Process(proc_info["pid"])
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    closed_pids.append(proc_info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    continue
            
            if closed_pids:
                # 等待进程退出
                time.sleep(1)
                screenshot = self.capture_screenshot("app_closed")
                return self.make_response(
                "success",
                f"已关闭应用: {app_name}",
                    {
                        "app_name": app_name,
                        "closed": True,
                        "closed_pids": closed_pids,
                        "force": force
                    },
                    screenshot
                )
            else:
                return self.make_response(
                    "error",
                    f"关闭应用失败: {app_name}（无权限或进程不存在）"
            )
            
        except Exception as e:
            return self.make_response("error", f"关闭应用失败: {e}")
    
    # ==================== 应用列表 ====================
    
    def list_running_apps(self) -> Dict:
        """列出当前运行的应用"""
        try:
            running_apps = []
            seen_apps = set()
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '')
                    
                    # 过滤系统进程和重复应用
                    if proc_name and proc_name not in seen_apps:
                        # 检查是否是用户应用（排除系统进程）
                        cmdline = ' '.join(proc_info.get('cmdline', []))
                        
                        # 简单过滤：排除系统进程
                        system_keywords = ['kernel', 'systemd', 'dbus', 'gdm', 'gnome-shell']
                        if not any(keyword in cmdline.lower() for keyword in system_keywords):
                            running_apps.append({
                                "name": proc_name,
                                "pid": proc_info['pid'],
                                "cmdline": cmdline[:100]  # 截断过长的命令行
                            })
                            seen_apps.add(proc_name)
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return self.make_response(
                "success",
                f"找到 {len(running_apps)} 个运行中的应用",
                {
                    "apps": running_apps,
                    "count": len(running_apps)
                }
            )
            
        except Exception as e:
            return self.make_response("error", f"列出应用失败: {e}")
    
    def is_app_running(self, app_name: str) -> Dict:
        """检查应用是否在运行"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info.get('name', '').lower()
                    cmdline = ' '.join(proc_info.get('cmdline', [])).lower()
                    
                    if app_name.lower() in proc_name or app_name.lower() in cmdline:
                        return self.make_response(
                            "success",
                            f"应用正在运行: {app_name}",
                            {
                                "app_name": app_name,
                                "running": True,
                                "pid": proc_info['pid']
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return self.make_response(
                "success",
                f"应用未运行: {app_name}",
                {"app_name": app_name, "running": False}
            )
            
        except Exception as e:
            return self.make_response("error", f"检查应用状态失败: {e}")
    
    # ==================== 应用快捷操作 ====================
    
    def app_quick_operation(self, app_name: str, url: Optional[str] = None, args: List[str] = None) -> Dict:
        """
        应用快捷操作（定义主流应用参数映射）
        
        Args:
            app_name: 应用名称（如firefox, chrome, 微信）
            url: URL地址（可选，用于浏览器）
            args: 启动参数（可选）
            
        Returns:
            操作结果
        """
        try:
            # 主流应用参数映射
            app_mappings = {
                "firefox": {
                    "cmd": "firefox",
                    "url_prefix": True,
                    "description": "Firefox浏览器"
                },
                "chrome": {
                    "cmd": "google-chrome",
                    "url_prefix": True,
                    "description": "Chrome浏览器"
                },
                "微信": {
                    "cmd": "wechat",
                    "url_prefix": False,
                    "description": "微信"
                },
                "wine": {
                    "cmd": "wine",
                    "url_prefix": False,
                    "description": "Wine运行Windows应用"
                },
                "终端": {
                    "cmd": "gnome-terminal",
                    "url_prefix": False,
                    "description": "GNOME终端"
                },
                "文件": {
                    "cmd": "nautilus",
                    "url_prefix": False,
                    "description": "文件管理器"
                },
                "gedit": {
                    "cmd": "gedit",
                    "url_prefix": False,
                    "description": "文本编辑器"
                }
            }
            
            # 查找应用映射
            app_info = app_mappings.get(app_name.lower())
            if not app_info:
                # 未找到映射，使用默认启动
                cmd = [app_name]
            else:
                cmd = [app_info["cmd"]]
            
            # 处理URL参数（浏览器应用）
            if url and app_info and app_info.get("url_prefix", False):
                # 确保URL格式正确
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                cmd.append(url)
            
            # 添加额外参数
            if args:
                cmd.extend(args)
            
            # 启动应用
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            time.sleep(1)
            
            if process.poll() is None:
                screenshot = self.capture_screenshot("app_quick_launched")
                return self.make_response(
                    "success",
                    f"应用快捷操作成功: {app_name}" + (f" ({url})" if url else ""),
                    {
                        "app_name": app_name,
                        "url": url,
                        "pid": process.pid,
                        "cmd": " ".join(cmd),
                        "launched": True
                    },
                    screenshot
                )
            else:
                return self.make_response(
                    "error",
                    f"应用启动失败: {app_name}（进程立即退出）"
                )
                
        except FileNotFoundError:
            return self.make_response("error", f"应用不存在: {app_name}")
        except Exception as e:
            return self.make_response("error", f"应用快捷操作失败: {e}")


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    agent = AppAgentLogic()
    
    print("=== 测试 AppAgent ===\n")
    
    # 测试查找应用
    print("1. 查找应用:")
    result = agent.find_app("firefox")
    print(f"   {result}\n")
    
    # 测试列出运行的应用
    print("2. 列出运行中的应用:")
    result = agent.list_running_apps()
    print(f"   找到 {result['data'].get('count', 0)} 个应用\n")
    
    # 测试检查应用状态
    print("3. 检查应用状态:")
    result = agent.is_app_running("firefox")
    print(f"   {result}\n")
    
    print("=== 测试完成 ===")
