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
import dbus
import shlex
import subprocess
import time
import shutil
import psutil
from pathlib import Path
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
    
    def _get_app_name_mapping(self, app_name: str) -> list:
        """
        获取应用名称映射列表（根据桌面环境）
        
        Args:
            app_name: 应用名称（如 nautilus, gnome-terminal）
        
        Returns:
            应用名称列表（按优先级排序）
        """
        # 检测桌面环境
        desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
        is_ukui = "UKUI" in desktop_env
        
        # 应用名称映射表
        app_mappings = {
            "nautilus": {
                "ukui": ["peony", "peony-qt", "nautilus", "thunar", "pcmanfm"],
                "default": ["nautilus", "peony", "peony-qt", "thunar", "pcmanfm"]
            },
            "gnome-terminal": {
                "ukui": ["ukui-terminal", "peony-terminal", "gnome-terminal", "xterm", "x-terminal-emulator"],
                "default": ["gnome-terminal", "ukui-terminal", "peony-terminal", "xterm", "x-terminal-emulator"]
            },
            "文件": {
                "ukui": ["peony", "peony-qt", "nautilus", "thunar", "pcmanfm"],
                "default": ["nautilus", "peony", "peony-qt", "thunar", "pcmanfm"]
            },
            "终端": {
                "ukui": ["ukui-terminal", "peony-terminal", "gnome-terminal", "xterm", "x-terminal-emulator"],
                "default": ["gnome-terminal", "ukui-terminal", "peony-terminal", "xterm", "x-terminal-emulator"]
            }
        }
        
        app_name_lower = app_name.lower()
        if app_name_lower in app_mappings:
            return app_mappings[app_name_lower]["ukui" if is_ukui else "default"]
        
        # 如果没有映射，返回原名称
        return [app_name]
    
    def find_app(self, app_name: str) -> Dict:
        """
        查找应用路径（支持应用名称映射）
        
        Args:
            app_name: 应用名称（如 firefox, chrome, gedit, nautilus, gnome-terminal）
        """
        # 获取应用名称映射列表
        app_names_to_try = self._get_app_name_mapping(app_name)
        
        for try_name in app_names_to_try:
            try:
                # 方法1: 使用 which 查找可执行文件
                result = subprocess.run(
                    ["which", try_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    app_path = result.stdout.strip()
                    return self.make_response(
                        "success",
                        f"找到应用: {try_name}（原始名称: {app_name}）",
                        {"app_name": app_name, "actual_app_name": try_name, "app_path": app_path, "found": True}
                    )
                
                # 方法2: 使用 gio launch 查找桌面文件
                desktop_files = [
                    f"/usr/share/applications/{try_name}.desktop",
                    f"/usr/local/share/applications/{try_name}.desktop",
                    os.path.expanduser(f"~/.local/share/applications/{try_name}.desktop")
                ]
                
                for desktop_file in desktop_files:
                    if os.path.exists(desktop_file):
                        return self.make_response(
                            "success",
                            f"找到应用桌面文件: {try_name}（原始名称: {app_name}）",
                            {"app_name": app_name, "actual_app_name": try_name, "desktop_file": desktop_file, "found": True}
                        )
                
                # 方法3: 搜索所有 .desktop 文件
                result = subprocess.run(
                    ["find", "/usr/share/applications", "-name", f"*{try_name}*.desktop"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.stdout.strip():
                    desktop_file = result.stdout.strip().split("\n")[0]
                    return self.make_response(
                        "success",
                        f"找到应用: {try_name}（原始名称: {app_name}）",
                        {"app_name": app_name, "actual_app_name": try_name, "desktop_file": desktop_file, "found": True}
                    )
            except Exception as e:
                # 继续尝试下一个名称
                continue
        
        # 所有尝试都失败
        return self.make_response(
            "error",
            f"未找到应用: {app_name}（已尝试: {', '.join(app_names_to_try)}）",
            {"app_name": app_name, "tried_names": app_names_to_try, "found": False}
        )
        
    # ==================== 应用启动 ====================
    
    def launch_app(self, app_name: str, args: List[str] = []) -> Dict:
        """
        启动应用（Wayland 安全版，支持应用名称映射）
        """
        try:
            find_result = self.find_app(app_name)
            if find_result["status"] == "error":
                return find_result

            # 获取实际的应用名称（可能是映射后的）
            actual_app_name = find_result["data"].get("actual_app_name", app_name)
            app_path = find_result["data"].get("app_path")
            desktop_file = find_result["data"].get("desktop_file")

            # ---- 构建 cmd ----
            if app_path:
                cmd = [shlex.quote(app_path)]
            elif desktop_file:
                desktop_file = str(Path(desktop_file).expanduser().resolve())
                cmd = ["gio", "launch", desktop_file]
            else:
                # 使用映射后的应用名称
                full_path = shutil.which(actual_app_name)
                if not full_path:
                    return self.make_response("error", f"{app_name} (映射为 {actual_app_name}) not found in $PATH")
                cmd = [actual_app_name]
            cmd.extend(args)

            # ---- 启动 ----
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            # ---- Wayland 等待窗口 ----
            def wait_gnome_wayland_window(pid, timeout=10):
                """GNOME Wayland 专用：等 pid 出现在 Shell 窗口列表"""
                try:
                    bus = dbus.SessionBus()
                    shell = bus.get_object('org.gnome.Shell',
                                             '/org/gnome/Shell/Introspect')
                    intro = dbus.Interface(shell, 'org.gnome.Shell.Introspect')
                    for _ in range(timeout * 4):
                        if str(pid) in intro.GetWindows():
                            return True
                        time.sleep(0.25)
                except Exception:
                    pass
                return False

            # 1. 进程级兜底
            if process.poll() is None:
                # 2. 窗口级检测（Wayland 专用）
                screenshot = self.capture_screenshot("app_launched")
                return self.make_response(
                    "success",
                    f"应用已启动: {app_name}",
                    {"app_name": app_name, "pid": process.pid, "launched": True},
                    screenshot
                )
                """if wait_gnome_wayland_window(process.pid):
                    screenshot = self.capture_screenshot("app_launched")
                    return self.make_response(
                        "success",
                        f"应用已启动: {app_name}",
                        {"app_name": app_name, "pid": process.pid, "launched": True},
                        screenshot
                    )
                else:
                    return self.make_response(
                        "error",
                        f"应用启动超时: {app_name}（进程存在，但 Wayland 窗口未出现）"
                    )"""
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
                                "cmdline": cmdline
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
    
    def _find_app_by_desktop(self, keywords: List[str]) -> Optional[str]:
        """通过desktop文件查找应用"""
        desktop_dirs = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            os.path.expanduser("~/.local/share/applications")
        ]
        
        for desktop_dir in desktop_dirs:
            if not os.path.exists(desktop_dir):
                continue
            
            try:
                for filename in os.listdir(desktop_dir):
                    if not filename.endswith(".desktop"):
                        continue
                    
                    filepath = os.path.join(desktop_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read().lower()
                            # 检查是否包含关键词
                            for keyword in keywords:
                                if keyword.lower() in content or keyword.lower() in filename.lower():
                                    # 解析Exec字段
                                    for line in content.split('\n'):
                                        if line.startswith('exec='):
                                            exec_cmd = line.split('=', 1)[1].strip()
                                            # 提取命令（去除%参数）
                                            cmd = exec_cmd.split()[0] if exec_cmd.split() else exec_cmd
                                            # 检查命令是否存在
                                            if shutil.which(cmd):
                                                return cmd
                                            # 如果是完整路径，直接返回
                                            if os.path.exists(cmd):
                                                return cmd
                                    break
                    except:
                        continue
            except:
                continue
        
        return None
    
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
            # 检测桌面环境并选择对应的应用
            desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").upper()
            is_ukui = "UKUI" in desktop_env
            
            # 检测可用的终端和文件管理器（按优先级）
            terminal_cmd = None
            file_manager_cmd = None
            
            # 终端应用优先级列表（UKUI优先）
            terminal_priority = []
            if is_ukui:
                terminal_priority = ["ukui-terminal", "peony-terminal", "gnome-terminal", "xterm", "x-terminal-emulator"]
            else:
                terminal_priority = ["gnome-terminal", "xterm", "x-terminal-emulator", "ukui-terminal", "peony-terminal"]
            
            for cmd in terminal_priority:
                if shutil.which(cmd):
                    terminal_cmd = cmd
                    break
            
            # 文件管理器优先级列表（UKUI优先）
            file_manager_priority = []
            if is_ukui:
                file_manager_priority = ["peony", "nautilus", "thunar", "pcmanfm", "dolphin"]
            else:
                file_manager_priority = ["nautilus", "peony", "thunar", "pcmanfm", "dolphin"]
            
            for cmd in file_manager_priority:
                if shutil.which(cmd):
                    file_manager_cmd = cmd
                    break
            
            # 如果还是没找到，尝试通过desktop文件查找
            if not terminal_cmd:
                terminal_cmd = self._find_app_by_desktop(["terminal", "Terminal", "TerminalEmulator"])
            if not file_manager_cmd:
                file_manager_cmd = self._find_app_by_desktop(["file-manager", "FileManager", "Files", "Nautilus", "Peony"])
            
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
                    "cmd": terminal_cmd or "xterm",
                    "url_prefix": False,
                    "description": f"终端（{terminal_cmd or 'xterm'}）"
                },
                "文件": {
                    "cmd": file_manager_cmd or "nautilus",
                    "url_prefix": False,
                    "description": f"文件管理器（{file_manager_cmd or 'nautilus'}）"
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
                # 未找到映射，尝试查找应用
                find_result = self.find_app(app_name)
                if find_result["status"] == "success":
                    app_path = find_result["data"].get("app_path")
                    desktop_file = find_result["data"].get("desktop_file")
                    if app_path:
                        cmd = [app_path]
                    elif desktop_file:
                        cmd = ["gio", "launch", desktop_file]
                    else:
                        cmd = [app_name]
                else:
                    # 查找失败，使用默认启动
                    cmd = [app_name]
            else:
                # 检查映射的命令是否存在
                if app_info["cmd"] and shutil.which(app_info["cmd"]):
                    cmd = [app_info["cmd"]]
                else:
                    # 命令不存在，尝试查找应用
                    find_result = self.find_app(app_info["cmd"] or app_name)
                    if find_result["status"] == "success":
                        app_path = find_result["data"].get("app_path")
                        desktop_file = find_result["data"].get("desktop_file")
                        if app_path:
                            cmd = [app_path]
                        elif desktop_file:
                            cmd = ["gio", "launch", desktop_file]
                        else:
                            cmd = [app_info["cmd"]]
                    else:
                        return self.make_response("error", f"未找到应用: {app_name}（映射命令: {app_info['cmd']}）")
            
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
