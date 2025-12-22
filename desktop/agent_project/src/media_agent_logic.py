#!/usr/bin/env python3
"""
MediaAgent 核心逻辑 - 媒体控制智能体

功能：
1. 播放音频/视频文件
2. 媒体控制（播放/暂停/停止/全屏）
3. 截图当前播放帧

作者：GUI Agent Team
"""

import os
import subprocess
import time
import dbus
from typing import Dict, Optional
from datetime import datetime
import shutil


class MediaAgentLogic:
    """媒体控制智能体核心逻辑"""
    
    def __init__(self):
        self.screenshot_dir = os.path.expanduser("~/.config/kylin-gui-agent/screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        # 检测可用的媒体播放器
        self.media_player = self._detect_media_player()
        self.current_player_process = None  # 当前播放器进程
        self.current_player_service = None  # 当前播放器D-Bus服务名
    
    def _detect_media_player(self) -> str:
        """检测可用的媒体播放器"""
        # 按优先级检测播放器
        players = ["totem", "vlc", "mpv", "smplayer", "mplayer"]
        for player in players:
            if shutil.which(player):
                return player
        return "totem"  # 默认
    
    def _detect_running_player(self) -> Optional[str]:
        """检测当前运行的媒体播放器"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_name = proc.info['name'].lower()
                    if any(player in proc_name for player in ['totem', 'vlc', 'mpv', 'smplayer', 'mplayer']):
                        return proc_name
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except:
            pass
        return None
    
    def capture_screenshot(self, prefix: str = "media") -> Optional[str]:
        """截取屏幕（优先截取播放器窗口）"""
        timestamp = int(time.time())
        screenshot_path = os.path.join(self.screenshot_dir, f"{prefix}_{timestamp}.png")
        
        env = os.environ.copy()
        if not env.get("DISPLAY"):
            if os.path.exists("/tmp/.X11-unix/X0"):
                env["DISPLAY"] = ":0"
            elif os.path.exists("/tmp/.X11-unix/X1"):
                env["DISPLAY"] = ":1"

        # 尝试找到播放器窗口并截图
        player_window_id = None
        try:
            if shutil.which("wmctrl"):
                result = subprocess.run(
                    ["wmctrl", "-l"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                    env=env
                )
                if result.returncode == 0:
                    # 查找播放器窗口
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 4:
                                window_title = ' '.join(parts[3:]).lower()
                                # 检查是否是播放器窗口
                                player_keywords = ['totem', 'vlc', 'mpv', 'smplayer', 'mplayer', 'media', 'video']
                                if any(keyword in window_title for keyword in player_keywords):
                                    player_window_id = parts[0]
                                    break
        except:
            pass
        
        try:
            # 方法1: 如果找到播放器窗口，优先截取播放器窗口
            if player_window_id and shutil.which("scrot"):
                # 使用scrot截取特定窗口
                subprocess.run(
                    ["scrot", "-z", "-d", "1", screenshot_path],
                    check=True,
                    capture_output=True,
                    timeout=10,
                    env=env
                )
                if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    return screenshot_path
        except:
            pass
        
        try:
            # 方法2: 使用 scrot 截取整个屏幕
            if shutil.which("scrot"):
                subprocess.run(
                    ["scrot", "-z", "-d", "1", screenshot_path],
                    check=True,
                    capture_output=True,
                    timeout=10,
                    env=env
                )
                if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    return screenshot_path
        except:
            pass
        
        try:
            # 方法3: 使用 gnome-screenshot
            if shutil.which("gnome-screenshot"):
                subprocess.run(
                    ["gnome-screenshot", "-f", screenshot_path, "--delay=1"],
                    check=True,
                    capture_output=True,
                    timeout=10,
                    env=env
                )
                if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    return screenshot_path
        except:
            pass
        
        try:
            # 方法4: 使用 import (ImageMagick)
            if shutil.which("import"):
                subprocess.run(
                    ["import", "-display", env.get("DISPLAY", ":0"), "-window", "root", screenshot_path],
                    check=True,
                    capture_output=True,
                    timeout=10,
                    env=env
                )
                if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                    return screenshot_path
        except:
            pass
        
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
    
    # ==================== 播放媒体 ====================
    
    def play_media(self, media_path: str) -> Dict:
        """
        播放媒体文件（音频/视频）
        
        Args:
            media_path: 媒体文件路径（支持本地文件）
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(media_path):
                return self.make_response("error", f"媒体文件不存在: {media_path}")
            
            # 检查文件权限
            if not os.access(media_path, os.R_OK):
                return self.make_response("error", f"无权限读取文件: {media_path}")
            
            # 播放媒体文件
            # 方法1: 优先使用检测到的播放器（确保窗口可见）
            player_process = None
            actual_player = None
            
            # 确保DISPLAY环境变量设置
            env = os.environ.copy()
            if not env.get("DISPLAY"):
                if os.path.exists("/tmp/.X11-unix/X0"):
                    env["DISPLAY"] = ":0"
                elif os.path.exists("/tmp/.X11-unix/X1"):
                    env["DISPLAY"] = ":1"
            
            try:
                # 优先使用检测到的播放器（确保窗口可见）
                if shutil.which(self.media_player):
                    # 根据播放器类型选择启动参数
                    if self.media_player == "totem":
                        cmd = ["totem", media_path]
                    elif self.media_player == "vlc":
                        cmd = ["vlc", "--play-and-exit", media_path]
                    elif self.media_player == "mpv":
                        cmd = ["mpv", media_path]
                    else:
                        cmd = [self.media_player, media_path]
                    
                    player_process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                        env=env
                    )
                    self.current_player_process = player_process
                    actual_player = self.media_player
                    time.sleep(3)  # 等待播放器启动
                else:
                    # 如果检测到的播放器不可用，使用gio open
                    player_process = subprocess.Popen(
                        ["gio", "open", media_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                        env=env
                    )
                    self.current_player_process = player_process
                    time.sleep(3)  # 等待播放器启动
                    
                    # 检测实际启动的播放器
                    actual_player = self._detect_running_player() or "默认播放器"
                
            except FileNotFoundError:
                # 如果gio不可用，尝试使用gio open作为备选
                try:
                    player_process = subprocess.Popen(
                        ["gio", "open", media_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                        env=env
                    )
                    self.current_player_process = player_process
                    time.sleep(3)
                    actual_player = self._detect_running_player() or "默认播放器"
                except:
                    return self.make_response("error", f"未找到可用的媒体播放器")
            
            # 等待播放器窗口出现
            time.sleep(2)
            
            # 截图（确保截取播放器窗口）
            screenshot = self.capture_screenshot("media_playing")
            
            return self.make_response(
                "success",
                f"媒体文件已开始播放: {os.path.basename(media_path)}（播放器: {actual_player}）",
                {
                    "media_path": media_path,
                    "media_name": os.path.basename(media_path),
                    "player": actual_player,
                    "player_pid": player_process.pid if player_process else None,
                    "playing": True
                },
                screenshot
            )
                
        except Exception as e:
            return self.make_response("error", f"播放媒体失败: {e}")
    
    # ==================== 媒体控制 ====================
    
    def media_control(self, action: str) -> Dict:
        """
        控制媒体播放状态
        
        Args:
            action: 操作类型（play/pause/stop/fullscreen/next/previous）
        """
        try:
            # 检测当前运行的播放器
            running_player = self._detect_running_player()
            if not running_player:
                # 检查进程是否还在运行
                if self.current_player_process:
                    try:
                        if self.current_player_process.poll() is None:
                            # 进程还在运行，但检测不到播放器名称，使用快捷键方式
                            return self._control_via_hotkey(action)
                    except:
                        pass
                return self.make_response("error", "媒体播放器未运行，请先播放媒体文件")
            
            # 根据播放器选择控制方式
            bus = dbus.SessionBus()
            
            # 尝试不同的D-Bus服务
            dbus_services = [
                ("org.gnome.Totem", "/org/gnome/Totem", "org.gnome.Totem"),
                ("org.mpris.MediaPlayer2.totem", "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player"),
                ("org.mpris.MediaPlayer2.vlc", "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player"),
                ("org.mpris.MediaPlayer2.mpv", "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player"),
            ]
            
            dbus_success = False
            for service, path, interface in dbus_services:
                try:
                    if bus.name_has_owner(service):
                        dbus_success = True
                        totem_proxy = bus.get_object(service, path)
                        totem_interface_obj = dbus.Interface(totem_proxy, interface)
                        
                        action_map = {
                            "play": "Play",
                            "pause": "Pause",
                            "stop": "Stop",
                            "next": "Next",
                            "previous": "Previous",
                        }
                        
                        if action == "fullscreen":
                            # 全屏操作
                            if hasattr(totem_interface_obj, "set_fullscreen"):
                                totem_interface_obj.set_fullscreen(True)
                            else:
                                # MPRIS接口使用Fullscreen属性
                                props = dbus.Interface(totem_proxy, "org.freedesktop.DBus.Properties")
                                props.Set(interface, "Fullscreen", dbus.Boolean(True))
                            control_action = "fullscreen"
                        elif action in action_map:
                            # 其他控制操作
                            method_name = action_map[action]
                            if hasattr(totem_interface_obj, method_name):
                                getattr(totem_interface_obj, method_name)()
                            else:
                                # MPRIS接口使用PlayPause等方法
                                if action == "play":
                                    totem_interface_obj.Play()
                                elif action == "pause":
                                    totem_interface_obj.Pause()
                                elif action == "stop":
                                    totem_interface_obj.Stop()
                            control_action = action
                        else:
                            return self.make_response("error", f"不支持的操作: {action}")
                        
                        time.sleep(0.5)
                        screenshot = self.capture_screenshot(f"media_{control_action}")
                        
                        return self.make_response(
                            "success",
                            f"媒体控制成功: {action}",
                            {
                                "action": control_action,
                                "player": running_player,
                                "status": "success"
                            },
                            screenshot
                        )
                except dbus.exceptions.DBusException:
                    continue
            
            # 如果D-Bus都失败，使用键盘快捷键
            if not dbus_success:
                return self._control_via_hotkey(action)
            
            try:
                totem_proxy = bus.get_object(totem_service, totem_path)
                totem_interface_obj = dbus.Interface(totem_proxy, totem_interface)
                
                action_map = {
                    "play": "Play",
                    "pause": "Pause",
                    "stop": "Stop",
                    "next": "Next",
                    "previous": "Previous",
                }
                
                if action == "fullscreen":
                    # 全屏操作
                    totem_interface_obj.set_fullscreen(True)
                    control_action = "fullscreen"
                elif action in action_map:
                    # 其他控制操作
                    method_name = action_map[action]
                    getattr(totem_interface_obj, method_name)()
                    control_action = action
                else:
                    return self.make_response("error", f"不支持的操作: {action}")
                
                time.sleep(0.5)
                screenshot = self.capture_screenshot(f"media_{control_action}")
                
                return self.make_response(
                    "success",
                    f"媒体控制成功: {action}",
                    {
                        "action": control_action,
                        "status": "success"
                    },
                    screenshot
                )
                
            except dbus.exceptions.DBusException as e:
                # DBus调用失败，尝试使用键盘快捷键
                return self._control_via_hotkey(action)
                
        except Exception as e:
            return self.make_response("error", f"媒体控制失败: {e}")
    
    def _control_via_hotkey(self, action: str) -> Dict:
        """使用键盘快捷键控制媒体（备用方案）"""
        try:
            hotkey_map = {
                "play": "space",
                "pause": "space",
                "stop": "Escape",
                "fullscreen": "f",
            }
            
            if action not in hotkey_map:
                return self.make_response("error", f"不支持的操作: {action}")
            
            # 使用xdotool发送按键
            subprocess.run(
                ["xdotool", "key", hotkey_map[action]],
                check=True,
                capture_output=True,
                timeout=2
            )
            
            time.sleep(0.5)
            screenshot = self.capture_screenshot(f"media_{action}")
            
            return self.make_response(
                "success",
                f"媒体控制成功（快捷键）: {action}",
                {
                    "action": action,
                    "method": "hotkey"
                },
                screenshot
            )
            
        except Exception as e:
            return self.make_response("error", f"快捷键控制失败: {e}")
    
    # ==================== 截图播放帧 ====================
    
    def capture_media_frame(self) -> Dict:
        """
        截图当前播放帧
        
        Returns:
            截图路径
        """
        try:
            screenshot = self.capture_screenshot("media_frame")
            
            if screenshot:
                return self.make_response(
                    "success",
                    "播放帧截图成功",
                    {
                        "screenshot_path": screenshot,
                        "timestamp": datetime.now().isoformat()
                    },
                    screenshot
                )
            else:
                return self.make_response("error", "截图失败，请确保媒体播放器正在运行")
                
        except Exception as e:
            return self.make_response("error", f"截图播放帧失败: {e}")


# ============================================================
# 测试
# ============================================================

if __name__ == "__main__":
    agent = MediaAgentLogic()
    
    print("=== 测试 MediaAgent ===\n")
    
    # 测试播放媒体（需要提供实际文件路径）
    print("1. 播放媒体:")
    print("   提示: 需要提供实际的媒体文件路径进行测试")
    
    # 测试媒体控制
    print("\n2. 媒体控制:")
    result = agent.media_control("pause")
    print(f"   {result['msg']}")
    
    # 测试截图
    print("\n3. 截图播放帧:")
    result = agent.capture_media_frame()
    print(f"   {result['msg']}")
    
    print("\n=== 测试完成 ===")

